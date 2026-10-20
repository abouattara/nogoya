"""Transformer ce qu'une source raconte en quelque chose que NOGOYA sait lire.

Règle qui gouverne tout ce fichier : **ne jamais inventer**. Un prix absent
reste absent, une ville absente reste absente, une catégorie qu'on ne sait
pas rattacher reste nulle. L'annonce partira en « données insuffisantes » et
un humain tranchera. Un catalogue rempli de valeurs plausibles mais fausses
est pire qu'un catalogue vide : il se trompe sans prévenir.
"""
import re
import unicodedata
from decimal import Decimal, InvalidOperation

from apps.catalog.models import Category, Product

# Les périodes telles qu'elles s'écrivent dans une annonce francophone.
_PERIOD_WORDS = {
    Product.RentalPeriod.HOUR: ("heure", "/h", "par heure", "hour"),
    Product.RentalPeriod.DAY: ("jour", "/j", "par jour", "jours", "day", "nuit", "nuitée"),
    Product.RentalPeriod.WEEK: ("semaine", "/sem", "par semaine", "week"),
    Product.RentalPeriod.MONTH: ("mois", "/m", "par mois", "mensuel", "month"),
}

# Rattachement par mots-clés, utilisé seulement quand la source ne donne pas
# de catégorie exploitable. Volontairement étroit : mieux vaut ne pas
# conclure que mal ranger.
_CATEGORY_HINTS = (
    ("appartement", ("appartement", "appart", "f2", "f3", "f4", "studio meublé")),
    ("maison", ("maison", "villa", "duplex")),
    ("chambre", ("chambre", "studio", "célibatérium", "celibaterium")),
    ("voiture", ("voiture", "berline", "4x4", "suv", "automobile", "véhicule", "vehicule")),
    ("utilitaire", ("utilitaire", "camionnette", "pick-up", "pickup", "fourgon", "minibus", "bus")),
    ("moto", ("moto", "scooter", "motocyclette", "tricycle")),
    ("terrain", ("terrain", "parcelle", "lot ")),
    ("salle", ("salle", "salle de fête", "salle de conférence")),
    ("bureau", ("bureau", "local commercial", "boutique", "magasin", "entrepôt", "entrepot")),
)

_CURRENCIES = {
    "xof": "XOF", "fcfa": "XOF", "cfa": "XOF", "f cfa": "XOF", "franc cfa": "XOF",
    "eur": "EUR", "€": "EUR", "usd": "USD", "$": "USD",
}


def strip_accents(text):
    return "".join(
        c for c in unicodedata.normalize("NFD", text or "") if unicodedata.category(c) != "Mn"
    )


def normalize_text(text):
    """Minuscules, sans accent, espaces réduits — la forme qui sert à comparer."""
    flat = strip_accents(str(text or "")).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", flat)).strip()


def parse_price(raw):
    """« 150 000 FCFA / mois » -> (Decimal('150000'), 'XOF', 'month').

    Renvoie `(None, None, None)` plutôt qu'un zéro : une annonce sans prix
    doit être signalée, pas affichée comme gratuite.
    """
    if raw is None:
        return None, None, None
    text = str(raw).strip()
    if not text:
        return None, None, None

    lowered = strip_accents(text).lower()

    currency = None
    for token, code in _CURRENCIES.items():
        if token in lowered:
            currency = code
            break

    period = None
    for value, words in _PERIOD_WORDS.items():
        if any(word in lowered for word in words):
            period = value
            break

    # Les chiffres, séparateurs de milliers retirés. On refuse les décimales
    # pour coller au modèle (decimal_places=0) plutôt que d'arrondir en
    # douce une valeur qu'on aurait mal lue.
    digits = re.sub(r"[^\d]", "", lowered.split(",")[0].split(".")[0])
    if not digits:
        return None, currency, period
    try:
        amount = Decimal(digits)
    except InvalidOperation:
        return None, currency, period
    if amount <= 0:
        return None, currency, period
    return amount, currency, period


def match_category(hint, title="", description=""):
    """Trouve la catégorie NOGOYA, ou renvoie None sans forcer.

    On essaie d'abord le slug ou le nom donné par la source, puis seulement
    des mots-clés dans le titre. La description n'est consultée qu'en dernier
    recours : elle contient souvent des mots qui parlent d'autre chose
    (« à deux pas de la mairie, près du marché aux motos »).
    """
    if hint:
        flat = normalize_text(hint)
        for category in Category.objects.all():
            if normalize_text(category.slug) == flat or normalize_text(category.name) == flat:
                return category

    haystacks = [normalize_text(title), normalize_text(description)]
    for haystack in haystacks:
        if not haystack:
            continue
        for keyword, variants in _CATEGORY_HINTS:
            if any(normalize_text(v) in haystack for v in variants):
                match = _category_by_keyword(keyword)
                if match:
                    return match
    return None


def _category_by_keyword(keyword):
    flat = normalize_text(keyword)
    for category in Category.objects.all():
        name = normalize_text(category.name)
        # « Voitures » doit répondre à « voiture », au singulier.
        if flat in name or name.rstrip("s") == flat.rstrip("s"):
            return category
    return None


def normalize_url(url):
    """Forme comparable d'une URL : sans schéma, sans www, sans traceurs.

    Deux liens vers la même annonce ne diffèrent souvent que par un
    `?utm_source=` ou un `www.` — ils ne doivent pas produire deux annonces.
    """
    if not url:
        return ""
    from urllib.parse import parse_qsl, urlencode, urlparse

    parsed = urlparse(str(url).strip())
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    query = [
        (k, v)
        for k, v in parse_qsl(parsed.query)
        if not k.lower().startswith(("utm_", "fbclid", "gclid", "ref"))
    ]
    path = parsed.path.rstrip("/")
    tail = f"?{urlencode(sorted(query))}" if query else ""
    return f"{host}{path}{tail}"
