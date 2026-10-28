"""Pruebas de HTTPS, cookies y XSS (Criterio 8).

Los ajustes de producción se activan con override_settings, de modo que estas
pruebas verifican el comportamiento que tendrá la aplicación desplegada.
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from rest_framework.test import APIClient

from .models import Categoria, Producto

PRODUCCION = dict(
    SECURE_SSL_REDIRECT=True,
    SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"),
    SECURE_REDIRECT_EXEMPT=[r"^api/salud/$"],
    SESSION_COOKIE_SECURE=True,
    CSRF_COOKIE_SECURE=True,
    SECURE_HSTS_SECONDS=31536000,
)
HTTPS = {"HTTP_X_FORWARDED_PROTO": "https"}


def respuesta_de_login(**extra):
    """Hace un login real (con CSRF) y devuelve la respuesta, con sus cookies."""
    get_user_model().objects.create_user("admin", password="x", is_staff=True)
    cliente = APIClient(enforce_csrf_checks=True)
    cliente.get("/api/auth/csrf/", **extra)
    # Por HTTPS los navegadores envían la cabecera Origin; Django la exige.
    origen = {"HTTP_ORIGIN": "https://testserver", "SERVER_PORT": "443"} if extra else {}
    return cliente.post(
        "/api/auth/login/",
        {"username": "admin", "password": "x"},
        format="json",
        HTTP_X_CSRFTOKEN=cliente.cookies["csrftoken"].value,
        **extra,
        **origen,
    )


@override_settings(**PRODUCCION)
class HttpsTests(TestCase):
    def test_http_se_redirige_a_https(self):
        respuesta = Client().get("/api/productos/")
        self.assertEqual(respuesta.status_code, 301)
        self.assertTrue(respuesta["Location"].startswith("https://"))

    def test_https_responde_normal(self):
        respuesta = Client().get("/api/productos/", **HTTPS)
        self.assertEqual(respuesta.status_code, 200)

    def test_hsts_le_dice_al_navegador_que_use_siempre_https(self):
        respuesta = Client().get("/api/productos/", **HTTPS)
        self.assertEqual(respuesta["Strict-Transport-Security"], "max-age=31536000")

    def test_el_chequeo_de_salud_no_se_redirige(self):
        respuesta = Client().get("/api/salud/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json(), {"estado": "ok"})

    def test_la_cookie_csrf_viaja_solo_por_https(self):
        respuesta = Client().get("/api/auth/csrf/", **HTTPS)
        self.assertTrue(respuesta.cookies["csrftoken"]["secure"])

    def test_la_cookie_de_sesion_viaja_solo_por_https(self):
        respuesta = respuesta_de_login(**HTTPS)
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.cookies["sessionid"]["secure"])
        self.assertTrue(respuesta.cookies["csrftoken"]["secure"])


class CookiesTests(TestCase):
    def test_la_cookie_csrf_debe_ser_legible_por_javascript(self):
        # El frontend la lee para enviarla en X-CSRFToken.
        respuesta = APIClient().get("/api/auth/csrf/")
        self.assertEqual(respuesta.cookies["csrftoken"]["httponly"], "")

    def test_la_cookie_de_sesion_no_es_legible_por_javascript(self):
        respuesta = respuesta_de_login()
        self.assertTrue(respuesta.cookies["sessionid"]["httponly"])

    def test_samesite_lax_en_ambas_cookies(self):
        respuesta = respuesta_de_login()
        self.assertEqual(respuesta.cookies["sessionid"]["samesite"], "Lax")
        self.assertEqual(respuesta.cookies["csrftoken"]["samesite"], "Lax")


class XssTests(TestCase):
    """La defensa principal contra XSS está en el frontend (textContent, nunca
    innerHTML). Aquí se comprueba la parte que le corresponde a la API."""

    CARGA = '<img src=x onerror="alert(1)">'

    def setUp(self):
        self.admin = APIClient()
        self.admin.force_login(
            get_user_model().objects.create_user("admin", password="x", is_staff=True)
        )
        self.categoria = Categoria.objects.create(nombre="Mueble")

    def test_la_api_responde_json_y_no_html(self):
        self.admin.post(
            "/api/productos/",
            {"nombre": self.CARGA, "precio": "1", "existencias": 1, "categoria": self.categoria.pk},
            format="json",
        )
        respuesta = APIClient().get("/api/productos/")
        self.assertTrue(respuesta["Content-Type"].startswith("application/json"))
        self.assertEqual(respuesta["X-Content-Type-Options"], "nosniff")
        self.assertEqual(respuesta.json()[0]["nombre"], self.CARGA)  # se guarda como texto

    def test_la_url_de_imagen_no_acepta_javascript(self):
        for url in ("javascript:alert(1)", "data:text/html,<script>alert(1)</script>"):
            respuesta = self.admin.post(
                "/api/productos/",
                {"nombre": "Mesa", "precio": "1", "existencias": 1,
                 "imagen": url, "categoria": self.categoria.pk},
                format="json",
            )
            self.assertEqual(respuesta.status_code, 400, url)
            self.assertIn("imagen", respuesta.json())
        self.assertEqual(Producto.objects.count(), 0)

    def test_la_api_no_puede_ser_embebida_en_un_iframe(self):
        self.assertEqual(APIClient().get("/api/productos/")["X-Frame-Options"], "DENY")
