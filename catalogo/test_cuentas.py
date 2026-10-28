"""Pruebas del registro y el inicio de sesión de clientes."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Categoria, Producto
from .test_autenticacion import HASH_RAPIDO, cliente_con_csrf, iniciar_sesion, token

DATOS = {"nombre": "Ana Pérez", "correo": "Ana@Example.com", "password": "Tienda-segura-2026"}


def registrar(cliente, **cambios):
    return cliente.post(
        "/api/auth/registro/",
        {**DATOS, **cambios},
        format="json",
        HTTP_X_CSRFTOKEN=token(cliente),
    )


@HASH_RAPIDO
class RegistroTests(TestCase):
    def test_registro_correcto_crea_la_cuenta_y_abre_la_sesion(self):
        cliente = cliente_con_csrf()
        r = registrar(cliente)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(
            r.json(),
            {
                "autenticado": True,
                "username": "ana@example.com",
                "nombre": "Ana Pérez",
                "correo": "ana@example.com",
                "es_admin": False,
            },
        )
        yo = cliente.get("/api/auth/yo/").json()
        self.assertTrue(yo["autenticado"])
        self.assertFalse(yo["es_admin"])

    def test_la_cuenta_no_es_de_administrador_y_la_clave_no_se_guarda_en_claro(self):
        registrar(cliente_con_csrf())
        usuario = get_user_model().objects.get(username="ana@example.com")
        self.assertFalse(usuario.is_staff)
        self.assertFalse(usuario.is_superuser)
        self.assertNotEqual(usuario.password, DATOS["password"])
        self.assertTrue(usuario.check_password(DATOS["password"]))

    def test_la_respuesta_no_incluye_la_clave(self):
        r = registrar(cliente_con_csrf())
        self.assertNotIn("password", r.json())
        self.assertNotIn(DATOS["password"], r.content.decode())

    def test_registro_sin_token_csrf_se_rechaza(self):
        cliente = APIClient(enforce_csrf_checks=True)
        r = cliente.post("/api/auth/registro/", DATOS, format="json")
        self.assertEqual(r.status_code, 403)
        self.assertFalse(get_user_model().objects.filter(username="ana@example.com").exists())

    def test_correo_repetido_se_rechaza_sin_importar_mayusculas(self):
        registrar(cliente_con_csrf())
        r = registrar(cliente_con_csrf(), correo="ANA@example.COM")
        self.assertEqual(r.status_code, 400)
        self.assertIn("correo", r.json())
        self.assertEqual(get_user_model().objects.filter(email="ana@example.com").count(), 1)

    def test_datos_obligatorios(self):
        for campo in DATOS:
            datos = {k: v for k, v in DATOS.items() if k != campo}
            r = cliente_con_csrf()
            r = r.post("/api/auth/registro/", datos, format="json", HTTP_X_CSRFTOKEN=token(r))
            self.assertEqual(r.status_code, 400, campo)
            self.assertIn(campo, r.json())

    def test_correo_invalido(self):
        r = registrar(cliente_con_csrf(), correo="no-es-correo")
        self.assertEqual(r.status_code, 400)
        self.assertIn("correo", r.json())

    def test_nombre_en_blanco(self):
        r = registrar(cliente_con_csrf(), nombre="   ")
        self.assertEqual(r.status_code, 400)
        self.assertIn("nombre", r.json())

    def test_claves_debiles_se_rechazan(self):
        for clave in ("corta1", "12345678", "password", "qwerty123"):
            r = registrar(cliente_con_csrf(), password=clave)
            self.assertEqual(r.status_code, 400, clave)
            self.assertIn("password", r.json(), clave)
        self.assertFalse(get_user_model().objects.exists())

    def test_clave_parecida_al_correo_se_rechaza(self):
        r = registrar(cliente_con_csrf(), password="ana@example.com")
        self.assertEqual(r.status_code, 400)
        self.assertIn("password", r.json())

    def test_el_nombre_con_html_se_devuelve_como_texto(self):
        r = registrar(cliente_con_csrf(), nombre="<img src=x onerror=alert(1)>")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["nombre"], "<img src=x onerror=alert(1)>")
        self.assertEqual(r["Content-Type"], "application/json")


@HASH_RAPIDO
class CuentaDeClienteTests(TestCase):
    def setUp(self):
        registrar(cliente_con_csrf())  # crea la cuenta
        categoria = Categoria.objects.create(nombre="Mueble")
        self.mesa = Producto.objects.create(
            nombre="Mesa", precio=Decimal("199000"), existencias=4, categoria=categoria
        )

    def entrar(self, usuario="ana@example.com", clave=DATOS["password"]):
        cliente = cliente_con_csrf()
        return cliente, iniciar_sesion(cliente, username=usuario, password=clave)

    def test_el_cliente_inicia_sesion_con_su_correo(self):
        cliente, r = self.entrar()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["nombre"], "Ana Pérez")
        self.assertFalse(r.json()["es_admin"])

    def test_el_correo_no_distingue_mayusculas_al_entrar(self):
        _, r = self.entrar(usuario="  ANA@EXAMPLE.COM ")
        self.assertEqual(r.status_code, 200)

    def test_clave_incorrecta(self):
        _, r = self.entrar(clave="otra-clave-123")
        self.assertEqual(r.status_code, 401)

    def test_cerrar_sesion(self):
        cliente, _ = self.entrar()
        r = cliente.post("/api/auth/logout/", HTTP_X_CSRFTOKEN=token(cliente))
        self.assertEqual(r.status_code, 204)
        self.assertFalse(cliente.get("/api/auth/yo/").json()["autenticado"])

    def test_un_cliente_no_puede_modificar_el_catalogo(self):
        cliente, _ = self.entrar()
        t = token(cliente)
        self.assertEqual(
            cliente.post("/api/categorias/", {"nombre": "X"}, format="json", HTTP_X_CSRFTOKEN=t).status_code, 403
        )
        self.assertEqual(
            cliente.patch(f"/api/productos/{self.mesa.pk}/", {"precio": "1"}, format="json", HTTP_X_CSRFTOKEN=t).status_code,
            403,
        )
        self.assertEqual(cliente.delete(f"/api/productos/{self.mesa.pk}/", HTTP_X_CSRFTOKEN=t).status_code, 403)
        self.mesa.refresh_from_db()
        self.assertEqual(self.mesa.precio, Decimal("199000"))

    def test_el_cliente_con_sesion_puede_usar_el_carrito_y_comprar(self):
        cliente, _ = self.entrar()
        carrito = cliente.post("/api/carritos/").json()
        base = f"/api/carritos/{carrito['token']}"
        r = cliente.post(f"{base}/items/", {"producto": self.mesa.pk, "cantidad": 1}, format="json")
        self.assertEqual(r.status_code, 200)
        r = cliente.post(
            f"{base}/comprar/",
            {"nombre": "Ana", "correo": "ana@example.com", "telefono": "3001234567", "direccion": "Calle 1", "ciudad": "Medellín"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)

    def test_el_administrador_sigue_entrando_con_su_usuario(self):
        get_user_model().objects.create_user("admin", password="clave-de-prueba-1", is_staff=True)
        cliente, r = self.entrar(usuario="admin", clave="clave-de-prueba-1")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["es_admin"])
