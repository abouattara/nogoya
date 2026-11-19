"""Analytics services: view de-duplication and search logging.

Business logic lives here (not in views/serializers) so both the REST API
and any future internal callers (Celery tasks, admin actions) share it.
"""
import re
from datetime import timedelta

from django.core.cache import cache
from django.db.models import F
from django.utils import timezone

from .models import ContactEvent, ProductView, SearchEvent

VIEW_DEDUPE_TTL = 60 * 60 * 12  # a visitor re-viewing within 12h doesn't recount


def _actor_key(request):
    if request.user.is_authenticated:
        return f"user:{request.user.pk}"
    return f"anon:{getattr(request, 'visitor_id', 'unknown')}"


def record_product_view(request, product):
    """Increment Product.views_count at most once per actor per TTL window.

    Returns True if this call counted as a new view.
    """
    actor = _actor_key(request)
    cache_key = f"pv:{product.pk}:{actor}"
    if cache.get(cache_key):
        return False
    cache.set(cache_key, 1, timeout=VIEW_DEDUPE_TTL)

    type(product).objects.filter(pk=product.pk).update(views_count=F("views_count") + 1)
    ProductView.objects.create(
        product=product,
        user=request.user if request.user.is_authenticated else None,
        visitor_id="" if request.user.is_authenticated else getattr(request, "visitor_id", ""),
    )
    return True


def record_contact_event(request, product, channel="phone"):
    return ContactEvent.objects.create(product=product, user=request.user, channel=channel)


_WHITESPACE_RE = re.compile(r"\s+")


def normalize_query(query):
    return _WHITESPACE_RE.sub(" ", query or "").strip().lower()


#: Les canaux qu'un client peut annoncer. Tout le reste est ignore.
SEARCH_CHANNELS = {"web", "android", "ios"}

#: Une recherche tapee au fil des lettres reste une seule recherche si elle
#: se precise dans ce delai.
REFINE_WINDOW = timedelta(seconds=60)


def record_search_event(request, *, query, filters, results_count, page=1):
    """Enregistre une recherche, une seule fois par intention.

    Deux choses gonflaient les chiffres sans rien dire de plus :

    * **la pagination.** Faire defiler une liste charge les pages 2, 3,
      4... de la meme recherche ; chacune comptait comme une recherche
      nouvelle. Seule la premiere page est enregistree.
    * **la frappe.** L'application cherche pendant qu'on tape : « ten »
      puis « tente » faisaient deux recherches, dont une que personne
      n'avait voulue. Une recherche qui en precise une autre du meme
      visiteur, avec les memes filtres et dans la minute, remplace la
      precedente au lieu de s'y ajouter.
    """
    try:
        if int(page or 1) > 1:
            return None
    except (TypeError, ValueError):
        return None

    normalized = normalize_query(query)
    filters = filters or {}
    if not normalized and not filters:
        return None  # rien a retenir : la page d'accueil, une liste vide de criteres

    authenticated = request.user.is_authenticated
    user = request.user if authenticated else None
    visitor_id = "" if authenticated else getattr(request, "visitor_id", "")
    channel = (request.headers.get("X-Client") or "").strip().lower()
    if channel not in SEARCH_CHANNELS:
        channel = ""

    actor = {"user": user} if authenticated else {"user__isnull": True, "visitor_id": visitor_id}
    if authenticated or visitor_id:
        previous = (
            SearchEvent.objects.filter(
                created_at__gte=timezone.now() - REFINE_WINDOW, **actor
            )
            .order_by("-created_at")
            .first()
        )
        # Meme intention : l'une prolonge l'autre, dans un sens ou dans
        # l'autre (on tape, on efface une lettre). Mais un champ vide ne
        # remplace jamais une recherche ecrite : « tente » puis rien, c'est
        # deux choses, et la premiere doit rester.
        same_intent = previous is not None and previous.filters == filters and (
            normalized.startswith(previous.normalized_query)
            or (normalized and previous.normalized_query.startswith(normalized))
        )
        if same_intent:
            previous.query = query or ""
            previous.normalized_query = normalized
            previous.results_count = results_count
            previous.channel = previous.channel or channel
            previous.save(
                update_fields=["query", "normalized_query", "results_count", "channel"]
            )
            return previous

    return SearchEvent.objects.create(
        user=user,
        visitor_id=visitor_id,
        query=query or "",
        normalized_query=normalized,
        filters=filters,
        results_count=results_count,
        channel=channel,
    )
