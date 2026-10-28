"""Pruebas del catálogo: CRUD de categorías y productos (Criterios 3 y 6)."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from django.test import TestCase

from .models import Carrito, Categoria, ItemCarrito, Producto


def cliente_admin():
    """Cliente con sesión de administrador (se omite CSRF: eso se prueba aparte)."""
    usuario = get_user_model().objects.create_user(
        "admin", password="clave-de-prueba-1", is_staff=True
    )
    cliente = APIClient()
    cliente.force_login(usuario)
    return cliente


class CategoriasTests(TestCase):
    def setUp(self):
        self.admin = cliente_admin()

    def test_listar_es_publico(self):
        Categoria.objects.create(nombre="Mueble")
        respuesta = APIClient().get("/api/categorias/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual([c["nombre"] for c in respuesta.json()], ["Mueble"])

    def test_crear_editar_y_eliminar(self):
        creada = self.admin.post(
            "/api/categorias/", {"nombre": "Silla", "descripcion": "Para sentarse"}
        )
        self.assertEqual(creada.status_code, 201)
        id_ = creada.json()["id"]
        self.assertTrue(Categoria.objects.filter(pk=id_).exists())

        editada = self.admin.patch(f"/api/categorias/{id_}/", {"nombre": "Sillas"})
        self.assertEqual(editada.status_code, 200)
        self.assertEqual(Categoria.objects.get(pk=id_).nombre, "Sillas")

        borrada = self.admin.delete(f"/api/categorias/{id_}/")
        self.assertEqual(borrada.status_code, 204)
        self.assertFalse(Categoria.objects.filter(pk=id_).exists())

    def test_nombre_obligatorio_y_unico(self):
        Categoria.objects.create(nombre="Mueble")
        sin_nombre = self.admin.post("/api/categorias/", {"descripcion": "x"})
        self.assertEqual(sin_nombre.status_code, 400)
        self.assertIn("nombre", sin_nombre.json())
        repetida = self.admin.post("/api/categorias/", {"nombre": "Mueble"})
        self.assertEqual(repetida.status_code, 400)

    def test_no_se_elimina_una_categoria_con_productos(self):
        categoria = Categoria.objects.create(nombre="Mueble")
        Producto.objects.create(nombre="Mesa", precio=100, existencias=1, categoria=categoria)
        respuesta = self.admin.delete(f"/api/categorias/{categoria.pk}/")
        self.assertEqual(respuesta.status_code, 409)
        self.assertIn("todavía tiene productos", respuesta.json()["detail"])
        self.assertTrue(Categoria.objects.filter(pk=categoria.pk).exists())


class ProductosTests(TestCase):
    def setUp(self):
        self.admin = cliente_admin()
        self.mueble = Categoria.objects.create(nombre="Mueble")
        self.silla = Categoria.objects.create(nombre="Silla")

    def datos(self, **cambios):
        datos = {
            "nombre": "Mesa de comedor",
            "precio": "199000.00",
            "existencias": 4,
            "descripcion": "Roble",
            "imagen": "",
            "categoria": self.mueble.pk,
        }
        datos.update(cambios)
        return datos

    def test_crear_editar_y_eliminar(self):
        creado = self.admin.post("/api/productos/", self.datos())
        self.assertEqual(creado.status_code, 201)
        cuerpo = creado.json()
        self.assertEqual(cuerpo["categoria_nombre"], "Mueble")
        id_ = cuerpo["id"]

        editado = self.admin.patch(f"/api/productos/{id_}/", {"precio": "210000.00"})
        self.assertEqual(editado.status_code, 200)
        self.assertEqual(Producto.objects.get(pk=id_).precio, Decimal("210000.00"))

        borrado = self.admin.delete(f"/api/productos/{id_}/")
        self.assertEqual(borrado.status_code, 204)
        self.assertFalse(Producto.objects.filter(pk=id_).exists())

    def test_catalogo_filtrado_por_categoria(self):
        """Criterio 6: al elegir una categoría solo salen sus productos."""
        Producto.objects.create(nombre="Mesa", precio=1, existencias=1, categoria=self.mueble)
        Producto.objects.create(nombre="Silla roja", precio=1, existencias=1, categoria=self.silla)
        publico = APIClient()

        todos = publico.get("/api/productos/").json()
        self.assertEqual(len(todos), 2)

        solo_sillas = publico.get(f"/api/productos/?categoria={self.silla.pk}").json()
        self.assertEqual([p["nombre"] for p in solo_sillas], ["Silla roja"])

    def test_categoria_obligatoria_y_existente(self):
        sin_categoria = self.datos()
        del sin_categoria["categoria"]
        self.assertEqual(self.admin.post("/api/productos/", sin_categoria).status_code, 400)
        inexistente = self.admin.post("/api/productos/", self.datos(categoria=9999))
        self.assertEqual(inexistente.status_code, 400)

    def test_precio_no_puede_ser_negativo(self):
        respuesta = self.admin.post("/api/productos/", self.datos(precio="-5.00"))
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("precio", respuesta.json())

    def test_existencias_no_pueden_ser_negativas(self):
        respuesta = self.admin.post("/api/productos/", self.datos(existencias=-1))
        self.assertEqual(respuesta.status_code, 400)

    def test_no_se_elimina_un_producto_que_esta_en_un_carrito(self):
        producto = Producto.objects.create(nombre="Mesa", precio=1, existencias=5, categoria=self.mueble)
        carrito = Carrito.objects.create()
        ItemCarrito.objects.create(carrito=carrito, producto=producto, cantidad=1)
        respuesta = self.admin.delete(f"/api/productos/{producto.pk}/")
        self.assertEqual(respuesta.status_code, 409)
        self.assertIn("está en uno o más carritos", respuesta.json()["detail"])
        self.assertTrue(Producto.objects.filter(pk=producto.pk).exists())
