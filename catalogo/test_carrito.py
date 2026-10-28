"""Pruebas del carrito (Criterio 5: el total se recalcula ante cualquier cambio)."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Carrito, Categoria, ItemCarrito, Producto


class CarritoTests(TestCase):
    def setUp(self):
        categoria = Categoria.objects.create(nombre="Mueble")
        self.mesa = Producto.objects.create(
            nombre="Mesa", precio=Decimal("199000"), existencias=4, categoria=categoria
        )
        self.silla = Producto.objects.create(
            nombre="Silla", precio=Decimal("230000.50"), existencias=2, categoria=categoria
        )
        self.agotado = Producto.objects.create(
            nombre="Biblioteca", precio=Decimal("640000"), existencias=0, categoria=categoria
        )
        self.api = APIClient()
        self.carrito = self.api.post("/api/carritos/").json()
        self.base = f"/api/carritos/{self.carrito['token']}"

    def agregar(self, producto, cantidad=1):
        return self.api.post(
            f"{self.base}/items/", {"producto": producto.pk, "cantidad": cantidad}, format="json"
        )

    # --- creación y lectura
    def test_un_carrito_nuevo_esta_vacio_y_tiene_token(self):
        self.assertEqual(self.carrito["items"], [])
        self.assertEqual(Decimal(self.carrito["total"]), 0)
        self.assertEqual(len(self.carrito["token"]), 36)

    def test_leer_el_carrito_por_su_token(self):
        self.agregar(self.mesa)
        respuesta = self.api.get(f"{self.base}/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.json()["items"]), 1)

    def test_token_desconocido(self):
        respuesta = self.api.get("/api/carritos/00000000-0000-4000-8000-000000000000/")
        self.assertEqual(respuesta.status_code, 404)

    def test_cada_carrito_tiene_un_token_distinto(self):
        otro = self.api.post("/api/carritos/").json()
        self.assertNotEqual(otro["token"], self.carrito["token"])

    # --- el total (criterio 5)
    def test_el_total_se_recalcula_al_agregar_cambiar_y_quitar(self):
        r = self.agregar(self.mesa, 2).json()
        self.assertEqual(Decimal(r["total"]), Decimal("398000"))

        r = self.agregar(self.silla, 1).json()
        self.assertEqual(Decimal(r["total"]), Decimal("628000.50"))

        item_mesa = next(i for i in r["items"] if i["producto"] == self.mesa.pk)
        r = self.api.patch(
            f"{self.base}/items/{item_mesa['id']}/", {"cantidad": 3}, format="json"
        ).json()
        self.assertEqual(Decimal(r["total"]), Decimal("827000.50"))

        r = self.api.delete(f"{self.base}/items/{item_mesa['id']}/").json()
        self.assertEqual(Decimal(r["total"]), Decimal("230000.50"))
        self.assertEqual(len(r["items"]), 1)

    def test_el_subtotal_de_cada_linea(self):
        r = self.agregar(self.silla, 2).json()
        self.assertEqual(Decimal(r["items"][0]["subtotal"]), Decimal("460001.00"))

    def test_quitar_el_ultimo_producto_deja_el_total_en_cero(self):
        r = self.agregar(self.mesa).json()
        r = self.api.delete(f"{self.base}/items/{r['items'][0]['id']}/").json()
        self.assertEqual(Decimal(r["total"]), 0)
        self.assertEqual(r["items"], [])

    # --- agregar
    def test_agregar_el_mismo_producto_suma_la_cantidad(self):
        self.agregar(self.mesa, 1)
        r = self.agregar(self.mesa, 2).json()
        self.assertEqual(len(r["items"]), 1)
        self.assertEqual(r["items"][0]["cantidad"], 3)

    def test_la_cantidad_por_defecto_es_uno(self):
        r = self.api.post(f"{self.base}/items/", {"producto": self.mesa.pk}, format="json")
        self.assertEqual(r.json()["items"][0]["cantidad"], 1)

    def test_no_se_puede_superar_las_existencias(self):
        r = self.agregar(self.silla, 3)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["cantidad"], ["Solo hay 2 disponibles."])
        self.assertEqual(ItemCarrito.objects.count(), 0)

    def test_sumar_a_lo_que_ya_hay_tambien_respeta_las_existencias(self):
        self.agregar(self.silla, 2)
        r = self.agregar(self.silla, 1)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(ItemCarrito.objects.get().cantidad, 2)

    def test_un_producto_agotado_no_se_agrega(self):
        r = self.agregar(self.agotado)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["cantidad"], ["Este producto está agotado."])

    def test_producto_inexistente(self):
        r = self.api.post(f"{self.base}/items/", {"producto": 9999}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("producto", r.json())

    def test_cantidad_invalida(self):
        for cantidad in (0, -1, "abc"):
            r = self.agregar(self.mesa, cantidad)
            self.assertEqual(r.status_code, 400, cantidad)

    # --- modificar y quitar
    def test_cambiar_la_cantidad_respeta_las_existencias(self):
        item = self.agregar(self.silla).json()["items"][0]
        r = self.api.patch(f"{self.base}/items/{item['id']}/", {"cantidad": 5}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(ItemCarrito.objects.get().cantidad, 1)

    def test_cantidad_cero_al_modificar_se_rechaza(self):
        item = self.agregar(self.mesa).json()["items"][0]
        r = self.api.patch(f"{self.base}/items/{item['id']}/", {"cantidad": 0}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_un_item_de_otro_carrito_no_se_puede_tocar(self):
        item = self.agregar(self.mesa).json()["items"][0]
        otro = self.api.post("/api/carritos/").json()
        ruta = f"/api/carritos/{otro['token']}/items/{item['id']}/"
        self.assertEqual(self.api.delete(ruta).status_code, 404)
        self.assertEqual(
            self.api.patch(ruta, {"cantidad": 2}, format="json").status_code, 404
        )
        self.assertEqual(ItemCarrito.objects.count(), 1)

    def test_los_carritos_son_independientes(self):
        otro = self.api.post("/api/carritos/").json()
        self.agregar(self.mesa)
        r = self.api.get(f"/api/carritos/{otro['token']}/").json()
        self.assertEqual(r["items"], [])

    # --- reglas de alcance
    def test_el_carrito_no_descuenta_existencias(self):
        self.agregar(self.mesa, 3)
        self.mesa.refresh_from_db()
        self.assertEqual(self.mesa.existencias, 4)

    def test_cambiar_el_precio_se_refleja_en_el_total(self):
        self.agregar(self.mesa, 1)
        self.mesa.precio = Decimal("100000")
        self.mesa.save()
        r = self.api.get(f"{self.base}/").json()
        self.assertEqual(Decimal(r["total"]), Decimal("100000"))

    # --- sesión de administrador y CSRF
    def test_una_sesion_de_administrador_abierta_no_bloquea_el_carrito(self):
        usuario = get_user_model().objects.create_user("admin", password="x", is_staff=True)
        cliente = APIClient(enforce_csrf_checks=True)
        cliente.force_login(usuario)
        creado = cliente.post("/api/carritos/")
        self.assertEqual(creado.status_code, 201)
        ruta = f"/api/carritos/{creado.json()['token']}/items/"
        r = cliente.post(ruta, {"producto": self.mesa.pk}, format="json")
        self.assertEqual(r.status_code, 200)

    def test_el_carrito_no_se_guarda_en_cache(self):
        self.assertEqual(self.api.get(f"{self.base}/")["Cache-Control"], "no-store")

    def test_el_carrito_vive_en_la_base_de_datos(self):
        self.agregar(self.mesa, 2)
        carrito = Carrito.objects.get(token=self.carrito["token"])
        self.assertEqual(carrito.calcular_total(), Decimal("398000"))
