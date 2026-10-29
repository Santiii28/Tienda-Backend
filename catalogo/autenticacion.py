from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as ErrorDeValidacion
from django.db import IntegrityError
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import seguridad


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
    nombre = serializers.CharField(allow_null=True)
    correo = serializers.CharField(allow_null=True)
    es_admin = serializers.BooleanField()


class RegistroSerializer(serializers.Serializer):
    """Datos para crear una cuenta de cliente. El correo es también el usuario."""

    nombre = serializers.CharField(max_length=100)
    correo = serializers.EmailField(max_length=150)
    password = serializers.CharField(write_only=True, max_length=128)


def datos_de_usuario(usuario):
    """Lo que el frontend necesita saber de quien tiene la sesión abierta."""
    if usuario is None or not usuario.is_authenticated:
        return {
            "autenticado": False,
            "username": None,
            "nombre": None,
            "correo": None,
            "es_admin": False,
        }
    return {
        "autenticado": True,
        "username": usuario.username,
        "nombre": usuario.first_name or usuario.username,
        "correo": usuario.email or None,
        "es_admin": usuario.is_staff,
    }


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
        responses={200: UsuarioSerializer, 401: DetalleSerializer, 429: DetalleSerializer},
        description="Inicia la sesión. Tras varios intentos fallidos seguidos con el "
        "mismo usuario, la cuenta se bloquea unos minutos (429).",
        auth=[],
    )
    def post(self, request):
        datos = LoginSerializer(data=request.data)
        datos.is_valid(raise_exception=True)

        nombre_de_usuario = datos.validated_data["username"].strip()
        if "@" in nombre_de_usuario:
            # Las cuentas de clientes usan el correo en minúsculas como usuario.
            nombre_de_usuario = nombre_de_usuario.lower()

        if seguridad.bloqueado(nombre_de_usuario):
            seguridad.registro.warning(
                "Inicio de sesión bloqueado por demasiados intentos: %s",
                seguridad.enmascarar(nombre_de_usuario),
            )
            minutos = settings.LOGIN_VENTANA_SEGUNDOS // 60
            respuesta = Response(
                {"detail": f"Demasiados intentos. Espere {minutos} minutos antes de volver a intentar."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
            respuesta["Retry-After"] = str(settings.LOGIN_VENTANA_SEGUNDOS)
            return respuesta

        usuario = authenticate(
            request,
            username=nombre_de_usuario,
            password=datos.validated_data["password"],
        )
        if usuario is None:
            intentos = seguridad.registrar_fallo(nombre_de_usuario)
            seguridad.registro.warning(
                "Inicio de sesión fallido: %s (intento %d de %d)",
                seguridad.enmascarar(nombre_de_usuario),
                intentos,
                settings.LOGIN_MAX_INTENTOS,
            )
            # El mismo mensaje para «no existe» y «clave incorrecta»: no revela qué correos tienen cuenta.
            return Response(
                {"detail": "Usuario o contraseña incorrectos."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        seguridad.limpiar_fallos(nombre_de_usuario)
        login(request, usuario)
        seguridad.registro.info(
            "Inicio de sesión correcto (usuario %s, %s)",
            usuario.pk,
            "administrador" if usuario.is_staff else "cliente",
        )
        return Response(datos_de_usuario(usuario))


class RegistroView(APIView):
    authentication_classes = [SesionConCSRF]
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Crear una cuenta de cliente",
        description="Crea la cuenta (sin permisos de administrador) e inicia la "
        "sesión. El correo se usa como nombre de usuario y la contraseña debe "
        "cumplir las reglas de Django. Exige el token CSRF.",
        request=RegistroSerializer,
        responses={201: UsuarioSerializer},
        auth=[],
    )
    def post(self, request):
        datos = RegistroSerializer(data=request.data)
        datos.is_valid(raise_exception=True)

        nombre = datos.validated_data["nombre"].strip()
        correo = datos.validated_data["correo"].strip().lower()
        clave = datos.validated_data["password"]
        if not nombre:
            return Response(
                {"nombre": ["Este campo no puede estar vacío."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        Usuario = get_user_model()
        if Usuario.objects.filter(username__iexact=correo).exists():
            return self.correo_repetido()

        nuevo = Usuario(username=correo, email=correo, first_name=nombre)
        try:
            # Con el usuario armado, también se compara la clave con su nombre y correo.
            validate_password(clave, user=nuevo)
        except ErrorDeValidacion as error:
            return Response(
                {"password": list(error.messages)}, status=status.HTTP_400_BAD_REQUEST
            )

        nuevo.set_password(clave)
        try:
            nuevo.save()
        except IntegrityError:
            return self.correo_repetido()

        login(request, nuevo, backend="django.contrib.auth.backends.ModelBackend")
        return Response(datos_de_usuario(nuevo), status=status.HTTP_201_CREATED)

    @staticmethod
    def correo_repetido():
        return Response(
            {"correo": ["Ya existe una cuenta con este correo."]},
            status=status.HTTP_400_BAD_REQUEST,
        )


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
        return Response(datos_de_usuario(request.user))
