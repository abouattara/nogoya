"""Le parcours d'une demande, côté client et côté équipe.

Une règle gouverne tout ce fichier : **le client ne décide de rien**. Il
soumet une demande, il lit son avancement, il annule s'il change d'avis.
Vérifier la disponibilité et transmettre les coordonnées sont des gestes
d'équipe, et ils sont refusés à quiconque d'autre — y compris à un client
qui appellerait l'API directement.
"""
import logging

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.catalog.models import Product
from apps.catalog.permissions import IsStaff
from apps.messaging.services import get_or_create_support_thread

from .notices import announce_request

from .models import RentalRequest
from .serializers import (
    RentalRequestCreateSerializer,
    RentalRequestSerializer,
    StaffRentalRequestSerializer,
)

logger = logging.getLogger("nogoya.rentals")


class RentalRequestViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action == "create":
            # Exiger une inscription avant la première question fait fuir
            # une part des clients, et le schéma ne l'impose pas : c'est
            # NOGOYA qui rappelle, et un numéro suffit. Le serializer exige
            # ce numéro pour un visiteur sans compte.
            return [permissions.AllowAny()]
        return super().get_permissions()

    def get_throttles(self):
        # Une demande ouverte aux visiteurs est une porte ouverte au bruit :
        # elle passe par le quota serré, compté par navigateur.
        if self.action == "create":
            self.throttle_scope = "auth"
        return super().get_throttles()

    def get_queryset(self):
        base = RentalRequest.objects.select_related(
            "product", "product__supplier__user", "client", "handled_by"
        ).prefetch_related("product__images")
        if self.request.user.is_staff:
            queryset = base
            state = self.request.query_params.get("status")
            if state in dict(RentalRequest.Status.choices):
                queryset = queryset.filter(status=state)
            return queryset
        return base.filter(client=self.request.user)

    def get_serializer_class(self):
        if self.action == "create":
            return RentalRequestCreateSerializer
        if self.request.user.is_staff:
            return StaffRentalRequestSerializer
        return RentalRequestSerializer

    def perform_create(self, serializer):
        product = serializer.validated_data["product"]
        user = self.request.user

        if not user.is_authenticated:
            # Pas de compte, donc pas de fil : nous rappellerons au numéro
            # laissé. La demande reste visible de l'équipe dans sa file.
            demande = serializer.save()
            announce_request(demande)
            return

        # La demande ouvre — ou retrouve — le fil avec NOGOYA sur ce bien :
        # le client n'a pas à chercher où suivre son dossier.
        thread, _created = get_or_create_support_thread(user, product=product)
        demande = serializer.save(client=user, thread=thread)
        announce_request(demande)

    @action(
        detail=False, methods=["get"], url_path="pending-summary",
        permission_classes=[permissions.IsAuthenticated, IsStaff],
    )
    def pending_summary(self, request):
        """Combien de demandes attendent, et combien sans compte.

        Une demande d'un visiteur sans compte n'a pas de fil : elle
        n'apparaît dans aucune conversation, et personne ne relancera si
        l'équipe l'oublie. Ce compteur sert à l'afficher là où l'équipe
        regarde déjà — la messagerie et la modération — plutôt que de
        compter sur elle pour penser à ouvrir un troisième écran.
        """
        en_attente = RentalRequest.objects.filter(
            status__in=[RentalRequest.Status.SUBMITTED, RentalRequest.Status.CHECKING]
        )
        return Response({
            "pending": en_attente.count(),
            "without_account": en_attente.filter(client__isnull=True).count(),
        })

    # --- gestes d'équipe ------------------------------------------------

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated, IsStaff])
    def checking(self, request, pk=None):
        """L'équipe prend la demande en main."""
        return self._advance(request, pk, RentalRequest.Status.CHECKING)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated, IsStaff])
    def available(self, request, pk=None):
        """Le fournisseur a confirmé la disponibilité.

        Horodate la vérification : sans cette trace, « disponible » n'est
        qu'une supposition qui engage NOGOYA.
        """
        return self._advance(
            request, pk, RentalRequest.Status.AVAILABLE, checked=True
        )

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated, IsStaff])
    def unavailable(self, request, pk=None):
        return self._advance(
            request, pk, RentalRequest.Status.UNAVAILABLE, checked=True
        )

    @action(
        detail=True, methods=["post"], url_path="release-contact",
        permission_classes=[permissions.IsAuthenticated, IsStaff],
    )
    def release_contact(self, request, pk=None):
        """Transmet les coordonnées du fournisseur au client.

        Refusé tant que la disponibilité n'a pas été vérifiée : mettre en
        relation sur un bien indisponible est la seule faute que ce schéma
        existe pour éviter.
        """
        demande = get_object_or_404(RentalRequest, pk=pk)
        if demande.supplier_checked_at is None:
            return Response(
                {"detail": "Vérifiez d'abord la disponibilité auprès du fournisseur."},
                status=status.HTTP_409_CONFLICT,
            )
        if demande.status == RentalRequest.Status.UNAVAILABLE:
            return Response(
                {"detail": "Ce bien a été déclaré indisponible pour ces dates."},
                status=status.HTTP_409_CONFLICT,
            )

        demande.contact_released_at = demande.contact_released_at or timezone.now()
        demande.released_by = demande.released_by or request.user
        demande.status = RentalRequest.Status.CONNECTED
        demande.handled_by = demande.handled_by or request.user
        demande.save(
            update_fields=[
                "contact_released_at", "released_by", "status", "handled_by", "updated_at",
            ]
        )
        logger.info(
            "Coordonnées transmises : demande %s, bien %s, client %s, par %s",
            demande.pk, demande.product.slug, demande.client_id, request.user.phone,
        )
        return Response(StaffRentalRequestSerializer(demande, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Le client renonce. C'est la seule décision qui lui appartienne."""
        demande = get_object_or_404(self.get_queryset(), pk=pk)
        if not request.user.is_staff and demande.client_id != request.user.pk:
            return Response(status=status.HTTP_404_NOT_FOUND)
        demande.status = RentalRequest.Status.CANCELLED
        demande.save(update_fields=["status", "updated_at"])
        serializer = self.get_serializer(demande)
        return Response(serializer.data)

    def _advance(self, request, pk, new_status, *, checked=False):
        demande = get_object_or_404(RentalRequest, pk=pk)
        demande.status = new_status
        demande.handled_by = demande.handled_by or request.user
        fields = ["status", "handled_by", "updated_at"]
        if checked:
            demande.supplier_checked_at = timezone.now()
            fields.append("supplier_checked_at")
        note = request.data.get("staff_note")
        if note is not None:
            demande.staff_note = str(note)[:2000]
            fields.append("staff_note")
        demande.save(update_fields=fields)
        return Response(StaffRentalRequestSerializer(demande, context={"request": request}).data)


def contact_is_released(user, product):
    """Ce client a-t-il le droit de voir les coordonnées de ce fournisseur ?

    Utilisé par `/products/{slug}/contact/`. L'équipe passe toujours ; un
    client ne passe que si une demande le concernant a été explicitement
    libérée.
    """
    if not user.is_authenticated:
        return False
    if user.is_staff:
        return True
    return RentalRequest.objects.filter(
        client=user, product=product, contact_released_at__isnull=False
    ).exists()


def supplier_owns(user, product):
    """Un fournisseur voit évidemment ses propres coordonnées."""
    profile = getattr(user, "supplier_profile", None)
    return profile is not None and product.supplier_id == profile.pk


__all__ = ["RentalRequestViewSet", "contact_is_released", "supplier_owns", "Product"]
