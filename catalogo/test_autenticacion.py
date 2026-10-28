"""Pruebas de login, sesión y CSRF (Criterio 8 y RF-13)."""

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import Categoria

CLAVE = "clave-de-prueba-1"

# Hash rápido solo para las pruebas (el real, PBKDF2, tarda ~0,3 s por usuario).
HASH_RAPIDO = override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"]
)


def cliente_con_csrf():
    """Cliente que, como el navegador, SÍ aplica la verificación CSRF."""
    cliente = APIClient(enforce_csrf_checks=True)
    cliente.get("/api/auth/csrf/")
    return cliente


def token(cliente):
    return cliente.cookies["csrftoken"].value


def iniciar_sesion(cliente, username="admin", password=CLAVE):
    return cliente.post(
        "/api/auth/login/",
        {"username": username, "password": password},
        format="json",
        HTTP_X_CSRFTOKEN=token(cliente),
    )


@HASH_RAPIDO
class LoginTests(TestCase):
    def setUp(self):
        User = get_user_model()
        User.objects.create_user("admin", password=CLAVE, is_staff=True)
        User.objects.create_user("cliente", password=CLAVE, is_staff=False)

    def test_la_cookie_csrf_se_entrega(self):
        cliente = APIClient()
        respuesta = cliente.get("/api/auth/csrf/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("csrftoken", respuesta.cookies)

    def test_login_sin_token_csrf_se_rechaza(self):
        cliente = APIClient(enforce_csrf_checks=True)
        respuesta = cliente.post(
            "/api/auth/login/", {"username": "admin", "password": CLAVE}, format="json"
        )
        self.assertEqual(respuesta.status_code, 403)
        self.assertIn("CSRF", respuesta.json()["detail"])

    def test_login_correcto_abre_sesion(self):
        cliente = cliente_con_csrf()
        respuesta = iniciar_sesion(cliente)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta.json(),
            {"autenticado": True, "username": "admin", "nombre": "admin", "correo": None, "es_admin": True},
        )
        self.assertEqual(cliente.get("/api/auth/yo/").json(), respuesta.json())

    def test_el_token_csrf_cambia_al_iniciar_sesion(self):
        cliente = cliente_con_csrf()
        antes = token(cliente)
        iniciar_sesion(cliente)
        self.assertNotEqual(antes, token(cliente))

    def test_clave_incorrecta(self):
        respuesta = iniciar_sesion(cliente_con_csrf(), password="otra")
        self.assertEqual(respuesta.status_code, 401)
        self.assertEqual(respuesta.json()["detail"], "Usuario o contraseña incorrectos.")

    def test_usuario_inexistente(self):
        self.assertEqual(iniciar_sesion(cliente_con_csrf(), username="nadie").status_code, 401)

    def test_un_cliente_entra_pero_no_es_administrador(self):
        cliente = cliente_con_csrf()
        respuesta = iniciar_sesion(cliente, username="cliente")
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.json()["autenticado"])
        self.assertFalse(respuesta.json()["es_admin"])
        self.assertFalse(cliente.get("/api/auth/yo/").json()["es_admin"])

    def test_datos_incompletos(self):
        cliente = cliente_con_csrf()
        respuesta = cliente.post(
            "/api/auth/login/", {"username": "admin"}, format="json",
            HTTP_X_CSRFTOKEN=token(cliente),
        )
        self.assertEqual(respuesta.status_code, 400)

    def test_yo_sin_sesion(self):
        self.assertEqual(
            APIClient().get("/api/auth/yo/").json(),
            {"autenticado": False, "username": None, "nombre": None, "correo": None, "es_admin": False},
        )

    def test_cerrar_sesion(self):
        cliente = cliente_con_csrf()
        iniciar_sesion(cliente)
        respuesta = cliente.post("/api/auth/logout/", HTTP_X_CSRFTOKEN=token(cliente))
        self.assertEqual(respuesta.status_code, 204)
        self.assertFalse(cliente.get("/api/auth/yo/").json()["autenticado"])

    def test_cerrar_sesion_sin_haber_entrado(self):
        cliente = cliente_con_csrf()
        respuesta = cliente.post("/api/auth/logout/", HTTP_X_CSRFTOKEN=token(cliente))
        self.assertEqual(respuesta.status_code, 403)

    def test_las_respuestas_de_sesion_no_se_guardan_en_cache(self):
        self.assertEqual(APIClient().get("/api/auth/yo/")["Cache-Control"], "no-store")


@HASH_RAPIDO
class PermisosTests(TestCase):
    """Lectura pública; escritura solo para administradores."""

    def setUp(self):
        get_user_model().objects.create_user("admin", password=CLAVE, is_staff=True)
        get_user_model().objects.create_user("cliente", password=CLAVE, is_staff=False)
        self.categoria = Categoria.objects.create(nombre="Mueble")

    def test_visitante_puede_leer(self):
        for ruta in ("/api/categorias/", "/api/productos/"):
            self.assertEqual(APIClient().get(ruta).status_code, 200, ruta)

    def test_visitante_no_puede_escribir(self):
        cliente = APIClient()
        id_ = self.categoria.pk
        self.assertEqual(cliente.post("/api/categorias/", {"nombre": "X"}).status_code, 403)
        self.assertEqual(cliente.patch(f"/api/categorias/{id_}/", {"nombre": "X"}).status_code, 403)
        self.assertEqual(cliente.delete(f"/api/categorias/{id_}/").status_code, 403)
        self.assertEqual(cliente.post("/api/productos/", {"nombre": "X"}).status_code, 403)
        self.assertTrue(Categoria.objects.filter(pk=id_).exists())

    def test_usuario_sin_permiso_de_staff_no_puede_escribir(self):
        cliente = APIClient()
        cliente.force_login(get_user_model().objects.get(username="cliente"))
        self.assertEqual(cliente.post("/api/categorias/", {"nombre": "X"}).status_code, 403)


@HASH_RAPIDO
class CsrfTests(TestCase):
    """Criterio 8: la protección CSRF debe poder demostrarse con un caso concreto."""

    def setUp(self):
        get_user_model().objects.create_user("admin", password=CLAVE, is_staff=True)
        self.cliente = cliente_con_csrf()
        iniciar_sesion(self.cliente)

    def test_con_sesion_pero_sin_token_la_escritura_se_rechaza(self):
        respuesta = self.cliente.post("/api/categorias/", {"nombre": "Atacante"}, format="json")
        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(respuesta.json()["detail"], "CSRF Failed: CSRF token missing.")
        self.assertFalse(Categoria.objects.filter(nombre="Atacante").exists())

    def test_con_un_token_falso_se_rechaza(self):
        respuesta = self.cliente.post(
            "/api/categorias/", {"nombre": "Atacante"}, format="json",
            HTTP_X_CSRFTOKEN="token-inventado",
        )
        self.assertEqual(respuesta.status_code, 403)
        self.assertFalse(Categoria.objects.filter(nombre="Atacante").exists())

    def test_con_el_token_correcto_la_escritura_funciona(self):
        respuesta = self.cliente.post(
            "/api/categorias/", {"nombre": "Legitima"}, format="json",
            HTTP_X_CSRFTOKEN=token(self.cliente),
        )
        self.assertEqual(respuesta.status_code, 201)

    def test_editar_y_borrar_tambien_exigen_token(self):
        categoria = Categoria.objects.create(nombre="Mueble")
        ruta = f"/api/categorias/{categoria.pk}/"
        self.assertEqual(self.cliente.patch(ruta, {"nombre": "Otro"}, format="json").status_code, 403)
        self.assertEqual(self.cliente.delete(ruta).status_code, 403)
        categoria.refresh_from_db()
        self.assertEqual(categoria.nombre, "Mueble")

    def test_origen_no_confiable_se_rechaza_aunque_lleve_token(self):
        respuesta = self.cliente.post(
            "/api/categorias/", {"nombre": "Atacante"}, format="json",
            HTTP_X_CSRFTOKEN=token(self.cliente),
            HTTP_ORIGIN="https://sitio-malicioso.example",
        )
        self.assertEqual(respuesta.status_code, 403)
        self.assertIn("Origin checking failed", respuesta.json()["detail"])

    def test_origen_del_frontend_se_acepta(self):
        respuesta = self.cliente.post(
            "/api/categorias/", {"nombre": "Desde el frontend"}, format="json",
            HTTP_X_CSRFTOKEN=token(self.cliente),
            HTTP_ORIGIN="http://localhost:5173",
        )
        self.assertEqual(respuesta.status_code, 201)

    @override_settings(CSRF_TRUSTED_ORIGINS=["https://tienda.vercel.app"])
    def test_el_dominio_de_produccion_debe_estar_declarado(self):
        cliente = cliente_con_csrf()
        iniciar_sesion(cliente)
        ruta, datos = "/api/categorias/", {"nombre": "Produccion"}
        permitido = cliente.post(
            ruta, datos, format="json", HTTP_X_CSRFTOKEN=token(cliente),
            HTTP_ORIGIN="https://tienda.vercel.app",
        )
        self.assertEqual(permitido.status_code, 201)
        otro = cliente.post(
            ruta, {"nombre": "Otro"}, format="json", HTTP_X_CSRFTOKEN=token(cliente),
            HTTP_ORIGIN="http://localhost:5173",
        )
        self.assertEqual(otro.status_code, 403)
