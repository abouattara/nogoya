from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import MeSerializer, RegisterSerializer


class RegisterView(generics.CreateAPIView):
    """Public sign-up. Rate-limited to slow down enumeration/spam."""

    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth"


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Adds a few non-sensitive user fields so the frontend avoids a round trip."""

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = {
            "id": self.user.id,
            "role": self.user.role,
            "full_name": self.user.get_full_name() or self.user.phone,
        }
        return data


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth"


class LogoutView(APIView):
    """Blacklists the refresh token so it can no longer mint access tokens."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        refresh = request.data.get("refresh")
        if not refresh:
            return Response(status=status.HTTP_204_NO_CONTENT)
        try:
            RefreshToken(refresh).blacklist()
        except TokenError:
            pass  # already invalid/expired — logout still succeeds
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = MeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
