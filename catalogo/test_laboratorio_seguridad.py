"""Pruebas del laboratorio de seguridad: límite de intentos, registros,
errores genéricos y diseño seguro (no confiar en lo que manda el cliente)."""

import logging
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.http import Http404
from django.test import RequestFactory, TestCase, override_settings
from rest_framework.test import APIClient

from config.urls import error_404, error_500

from . import seguridad
from .models import Categoria, Producto
from .test_autenticacion import CLAVE, HASH_RAPIDO, cliente_con_csrf, iniciar_sesion
from .test_cuentas import registrar


@HASH_RAPIDO
class LimiteDeIntentosTests(TestCase):
    """Parte 2.5: el sexto intento fallido seguido responde 429."""

    def setUp(self):
        cache.clear()
        get_user_model().objects.create_user("ana@example.com", password=CLAVE)
        get_user_model().objects.create_user("luis@example.com", password=CLAVE)
        self.cliente = cliente_con_csrf()

    def fallar(self, veces, usuario="ana@example.com"):
        return [
            iniciar_sesion(self.cliente, usuario, "incorrecta").status_code
            for _ in range(veces)
        ]

    def test_cinco_fallos_dan_401_y_el_sexto_intento_da_429(self):
        self.assertEqual(self.fallar(5), [401] * 5)
        respuesta = iniciar_sesion(self.cliente, "ana@example.com", "incorrecta")
        self.assertEqual(respuesta.status_code, 429)
        self.assertIn("Demasiados intentos", respuesta.json()["detail"])
        self.assertEqual(respuesta["Retry-After"], "900")

    def test_con_la_cuenta_bloqueada_ni_la_clave_correcta_entra(self):
        self.fallar(5)
        respuesta = iniciar_sesion(self.cliente, "ana@example.com", CLAVE)
        self.assertEqual(respuesta.status_code, 429)
        self.assertFalse(self.cliente.get("/api/auth/yo/").json()["autenticado"])

    def test_el_bloqueo_es_por_usuario_y_no_afecta_a_los_demas(self):
        self.fallar(5)
        respuesta = iniciar_sesion(self.cliente, "luis@example.com", CLAVE)
        self.assertEqual(respuesta.status_code, 200)

    def test_no_distingue_mayusculas_en_el_correo(self):
        self.fallar(5)
        respuesta = iniciar_sesion(self.cliente, "ANA@Example.com", CLAVE)
        self.assertEqual(respuesta.status_code, 429)

    def test_entrar_bien_borra_el_contador(self):
        self.fallar(4)
        self.assertEqual(iniciar_sesion(self.cliente, "ana@example.com", CLAVE).status_code, 200)
        self.assertEqual(self.fallar(4), [401] * 4)  # el contador empezó de cero

    def test_un_usuario_que_no_existe_tambien_se_limita_y_da_el_mismo_mensaje(self):
        existe = iniciar_sesion(self.cliente, "ana@example.com", "incorrecta").json()
        no_existe = iniciar_sesion(self.cliente, "nadie@example.com", "incorrecta").json()
        self.assertEqual(existe, no_existe)
        self.fallar(4, "nadie@example.com")
        self.assertEqual(iniciar_sesion(self.cliente, "nadie@example.com", "x").status_code, 429)

    @override_settings(LOGIN_MAX_INTENTOS=2)
    def test_el_maximo_se_puede_configurar(self):
        self.assertEqual(self.fallar(2), [401, 401])
        self.assertEqual(iniciar_sesion(self.cliente, "ana@example.com", "x").status_code, 429)


@HASH_RAPIDO
class RegistrosDeSeguridadTests(TestCase):
    """Parte 6.4 / A09: los intentos de login quedan registrados, sin datos sensibles."""

    def setUp(self):
        cache.clear()
        get_user_model().objects.create_user("ana@example.com", password=CLAVE)
        self.cliente = cliente_con_csrf()

    def test_un_login_fallido_se_registra_con_el_correo_enmascarado(self):
        with self.assertLogs("tienda.seguridad", level=logging.WARNING) as capturado:
            iniciar_sesion(self.cliente, "ana@example.com", "clave-secreta-mala")
        texto = "\n".join(capturado.output)
        self.assertIn("Inicio de sesión fallido", texto)
        self.assertIn("an***@example.com", texto)
        self.assertNotIn("ana@example.com", texto)
        self.assertNotIn("clave-secreta-mala", texto)

    def test_el_bloqueo_se_registra(self):
        for _ in range(5):
            iniciar_sesion(self.cliente, "ana@example.com", "mala")
        with self.assertLogs("tienda.seguridad", level=logging.WARNING) as capturado:
            iniciar_sesion(self.cliente, "ana@example.com", "mala")
        self.assertIn("bloqueado", "\n".join(capturado.output))

    def test_un_login_correcto_no_guarda_el_correo_ni_la_clave(self):
        with self.assertLogs("tienda.seguridad", level=logging.INFO) as capturado:
            iniciar_sesion(self.cliente, "ana@example.com", CLAVE)
        texto = "\n".join(capturado.output)
        self.assertIn("Inicio de sesión correcto", texto)
        self.assertNotIn("ana@example.com", texto)
        self.assertNotIn(CLAVE, texto)

    def test_enmascarar(self):
        self.assertEqual(seguridad.enmascarar("ana.perez@correo.com"), "an***@correo.com")
        self.assertEqual(seguridad.enmascarar("admin"), "ad***")


class ErroresGenericosTests(TestCase):
    """Parte 6.4: hacia afuera solo mensajes genéricos, sin rutas ni trazas."""

    def test_una_ruta_inexistente_responde_json_generico(self):
        respuesta = self.client.get("/api/esto-no-existe/")
        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(respuesta.json(), {"detail": "No encontrado."})

    def test_el_manejador_404_no_revela_la_ruta(self):
        respuesta = error_404(RequestFactory().get("/secreto/ruta"), Http404("detalle interno"))
        self.assertNotIn(b"secreto", respuesta.content)
        self.assertNotIn(b"interno", respuesta.content)

    def test_el_manejador_500_responde_json_generico(self):
        respuesta = error_500(RequestFactory().get("/"))
        self.assertEqual(respuesta.status_code, 500)
        self.assertEqual(respuesta.content, b'{"detail": "Error interno del servidor."}')

    def test_un_id_mal_formado_responde_404_generico(self):
        respuesta = self.client.get("/api/productos/abc/")
        self.assertEqual(respuesta.status_code, 404)
        self.assertNotIn("Traceback", respuesta.content.decode())

    def test_el_token_de_carrito_mal_formado_responde_404(self):
        self.assertEqual(self.client.get("/api/carritos/no-es-un-uuid/").status_code, 404)


@HASH_RAPIDO
class DisenoInseguroTests(TestCase):
    """Parte 7.1 (A06): el servidor no confía en lo que manda el cliente."""

    def setUp(self):
        cache.clear()
        categoria = Categoria.objects.create(nombre="Mueble")
        self.mesa = Producto.objects.create(
            nombre="Mesa", precio=Decimal("199000"), existencias=4, categoria=categoria
        )
        self.api = APIClient()
        self.carrito = self.api.post("/api/carritos/").json()
        self.base = f"/api/carritos/{self.carrito['token']}"

    def test_cantidad_negativa_o_cero_al_agregar_se_rechaza(self):
        for cantidad in (-5, 0):
            r = self.api.post(
                f"{self.base}/items/", {"producto": self.mesa.pk, "cantidad": cantidad}, format="json"
            )
            self.assertEqual(r.status_code, 400, cantidad)
        self.assertEqual(self.api.get(f"{self.base}/").json()["items"], [])

    def test_cantidad_negativa_al_cambiar_se_rechaza_y_el_total_no_se_altera(self):
        r = self.api.post(
            f"{self.base}/items/", {"producto": self.mesa.pk, "cantidad": 2}, format="json"
        ).json()
        item = r["items"][0]["id"]
        cambio = self.api.patch(f"{self.base}/items/{item}/", {"cantidad": -5}, format="json")
        self.assertEqual(cambio.status_code, 400)
        total = Decimal(self.api.get(f"{self.base}/").json()["total"])
        self.assertEqual(total, Decimal("398000"))

    def test_el_precio_manipulado_en_el_cuerpo_se_ignora(self):
        r = self.api.post(
            f"{self.base}/items/",
            {"producto": self.mesa.pk, "cantidad": 1, "precio": 1, "precio_unitario": 1, "total": 1},
            format="json",
        ).json()
        self.assertEqual(Decimal(r["total"]), Decimal("199000"))

    def test_el_total_de_la_compra_sale_de_la_base_de_datos(self):
        self.api.post(
            f"{self.base}/items/", {"producto": self.mesa.pk, "cantidad": 1}, format="json"
        )
        datos = {
            "nombre": "Ana Pérez", "correo": "ana@example.com", "telefono": "300 123 4567",
            "direccion": "Calle 10 # 20-30", "ciudad": "Medellín", "total": 1, "total_a_pagar": 1,
        }
        r = self.api.post(f"{self.base}/comprar/", datos, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Decimal(r.json()["total_a_pagar"]), Decimal("209000"))

    def test_el_rol_que_manda_el_cliente_al_registrarse_se_ignora(self):
        cliente = cliente_con_csrf()
        r = registrar(cliente, rol="admin", is_staff=True, is_superuser=True, es_admin=True)
        self.assertEqual(r.status_code, 201)
        usuario = get_user_model().objects.get(username="ana@example.com")
        self.assertFalse(usuario.is_staff)
        self.assertFalse(usuario.is_superuser)
        self.assertFalse(r.json()["es_admin"])
