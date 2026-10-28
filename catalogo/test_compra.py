"""Pruebas del envío, el total a pagar y la compra simulada."""

from decimal import Decimal

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import Categoria, Producto

DATOS = {
    "nombre": "Ana Pérez",
    "correo": "ana@example.com",
    "telefono": "300 123 4567",
    "direccion": "Calle 10 # 20-30",
    "ciudad": "Medellín",
}


class CompraTests(TestCase):
    def setUp(self):
        categoria = Categoria.objects.create(nombre="Mueble")
        self.mesa = Producto.objects.create(
            nombre="Mesa", precio=Decimal("199000"), existencias=4, categoria=categoria
        )
        self.silla = Producto.objects.create(
            nombre="Silla", precio=Decimal("230000.50"), existencias=2, categoria=categoria
        )
        self.api = APIClient()
        self.carrito = self.api.post("/api/carritos/").json()
        self.base = f"/api/carritos/{self.carrito['token']}"

    def agregar(self, producto, cantidad=1):
        return self.api.post(
            f"{self.base}/items/", {"producto": producto.pk, "cantidad": cantidad}, format="json"
        )

    def comprar(self, datos=None):
        return self.api.post(
            f"{self.base}/comprar/", DATOS if datos is None else datos, format="json"
        )

    # --- envío y total a pagar
    def test_un_carrito_vacio_no_cobra_envio(self):
        self.assertEqual(Decimal(self.carrito["envio"]), 0)
        self.assertEqual(Decimal(self.carrito["total_a_pagar"]), 0)

    def test_el_envio_es_10000_y_se_suma_al_total(self):
        r = self.agregar(self.mesa, 2).json()
        self.assertEqual(Decimal(r["total"]), Decimal("398000"))
        self.assertEqual(Decimal(r["envio"]), Decimal("10000"))
        self.assertEqual(Decimal(r["total_a_pagar"]), Decimal("408000"))

    def test_el_envio_no_cambia_con_la_cantidad(self):
        self.agregar(self.mesa, 1)
        r = self.agregar(self.silla, 2).json()
        self.assertEqual(Decimal(r["envio"]), Decimal("10000"))
        self.assertEqual(Decimal(r["total_a_pagar"]), Decimal("669001.00"))

    def test_al_vaciar_el_carrito_el_envio_vuelve_a_cero(self):
        r = self.agregar(self.mesa).json()
        item_id = r["items"][0]["id"]
        r = self.api.delete(f"{self.base}/items/{item_id}/").json()
        self.assertEqual(Decimal(r["total_a_pagar"]), 0)

    @override_settings(COSTO_ENVIO=Decimal("0"))
    def test_el_costo_de_envio_es_configurable(self):
        r = self.agregar(self.mesa).json()
        self.assertEqual(Decimal(r["total_a_pagar"]), Decimal("199000"))

    # --- compra
    def test_comprar_devuelve_el_resumen_y_vacia_el_carrito(self):
        self.agregar(self.mesa, 2)
        self.agregar(self.silla, 1)
        r = self.comprar()
        self.assertEqual(r.status_code, 200)
        datos = r.json()
        self.assertEqual(datos["mensaje"], "¡Compra exitosa!")
        self.assertEqual(datos["nombre"], "Ana Pérez")
        self.assertEqual(datos["ciudad"], "Medellín")
        self.assertEqual(len(datos["items"]), 2)
        self.assertEqual(Decimal(datos["total"]), Decimal("628000.50"))
        self.assertEqual(Decimal(datos["envio"]), Decimal("10000"))
        self.assertEqual(Decimal(datos["total_a_pagar"]), Decimal("638000.50"))

        despues = self.api.get(f"{self.base}/").json()
        self.assertEqual(despues["items"], [])
        self.assertEqual(Decimal(despues["total_a_pagar"]), 0)

    def test_comprar_no_descuenta_las_existencias(self):
        self.agregar(self.mesa, 2)
        self.comprar()
        self.mesa.refresh_from_db()
        self.assertEqual(self.mesa.existencias, 4)

    def test_comprar_un_carrito_vacio_da_400(self):
        r = self.comprar()
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["detail"], "El carrito está vacío.")

    def test_comprar_con_existencias_que_ya_no_alcanzan_da_409_y_no_vacia(self):
        self.agregar(self.silla, 2)
        Producto.objects.filter(pk=self.silla.pk).update(existencias=1)
        r = self.comprar()
        self.assertEqual(r.status_code, 409)
        self.assertIn("Silla", r.json()["detail"])
        self.assertEqual(len(self.api.get(f"{self.base}/").json()["items"]), 1)

    def test_comprar_exige_todos_los_datos(self):
        self.agregar(self.mesa)
        for campo in DATOS:
            datos = {k: v for k, v in DATOS.items() if k != campo}
            r = self.comprar(datos)
            self.assertEqual(r.status_code, 400, campo)
            self.assertIn(campo, r.json())
        self.assertEqual(len(self.api.get(f"{self.base}/").json()["items"]), 1)

    def test_comprar_valida_correo_y_telefono(self):
        self.agregar(self.mesa)
        self.assertIn("correo", self.comprar({**DATOS, "correo": "no-es-correo"}).json())
        self.assertIn("telefono", self.comprar({**DATOS, "telefono": "abc"}).json())
        self.assertEqual(len(self.api.get(f"{self.base}/").json()["items"]), 1)

    def test_comprar_con_token_desconocido_da_404(self):
        r = self.api.post(
            "/api/carritos/00000000-0000-4000-8000-000000000000/comprar/", DATOS, format="json"
        )
        self.assertEqual(r.status_code, 404)

    def test_comprar_no_exige_csrf_ni_sesion(self):
        api = APIClient(enforce_csrf_checks=True)
        self.agregar(self.mesa)
        r = api.post(f"{self.base}/comprar/", DATOS, format="json")
        self.assertEqual(r.status_code, 200)

    def test_una_compra_con_texto_html_se_devuelve_como_texto(self):
        self.agregar(self.mesa)
        r = self.comprar({**DATOS, "nombre": "<img src=x onerror=alert(1)>"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["nombre"], "<img src=x onerror=alert(1)>")
        self.assertEqual(r["Content-Type"], "application/json")

    def test_la_compra_no_se_puede_repetir_con_el_mismo_carrito(self):
        self.agregar(self.mesa)
        self.assertEqual(self.comprar().status_code, 200)
        self.assertEqual(self.comprar().status_code, 400)
