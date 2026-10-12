from django.contrib.auth import authenticate, login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class SesionConCSRF(SessionAuthentication):
    """Como SessionAuthentication, pero exige el token CSRF aunque todavía
    no haya sesión. Se usa en el login, que es cuando aún no la hay."""

    def authenticate(self, request):
        self.enforce_csrf(request)
        return None


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class UsuarioSerializer(serializers.Serializer):
    autenticado = serializers.BooleanField()
    username = serializers.CharField(allow_null=True)


class DetalleSerializer(serializers.Serializer):
    detail = serializers.CharField()


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    """Entrega la cookie csrftoken para que el frontend pueda enviarla."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(responses={200: DetalleSerializer})
    def get(self, request):
        return Response({"detail": "Cookie CSRF establecida."})


class LoginView(APIView):
    authentication_classes = [SesionConCSRF]
    permission_classes = [AllowAny]

    @extend_schema(
        request=LoginSerializer,
        responses={200: UsuarioSerializer},
        auth=[],
    )
    def post(self, request):
        datos = LoginSerializer(data=request.data)
        datos.is_valid(raise_exception=True)

        usuario = authenticate(
            request,
            username=datos.validated_data["username"],
            password=datos.validated_data["password"],
        )
        if usuario is None or not usuario.is_staff:
            return Response(
                {"detail": "Usuario o contraseña incorrectos."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        login(request, usuario)
        return Response({"autenticado": True, "username": usuario.username})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={204: None})
    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class YoView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]

    @extend_schema(responses={200: UsuarioSerializer})
    def get(self, request):
        if request.user.is_authenticated and request.user.is_staff:
            return Response({"autenticado": True, "username": request.user.username})
        return Response({"autenticado": False, "username": None})
