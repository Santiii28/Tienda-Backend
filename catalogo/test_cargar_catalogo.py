import re
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from .datos_catalogo import FOTOS_LISTAS, PRECIOS_ANTERIORES, PRODUCTOS
from .models import Categoria, Producto
from .serializers import RUTA_PROPIA
from .tests import cliente_admin


def cargar():
    salida = StringIO()
    call_command("cargar_catalogo", stdout=salida)
    return salida.getvalue()


class DatosDelCatalogoTests(TestCase):
    def test_nombres_y_fotos_no_se_repiten(self):
        nombres = [p[0].lower() for p in PRODUCTOS]
        fotos = [p[5] for p in PRODUCTOS]
        self.assertEqual(len(nombres), len(set(nombres)))
        self.assertEqual(len(fotos), len(set(fotos)))

    def test_datos_validos(self):
        for nombre, categoria, precio, existencias, descripcion, foto in PRODUCTOS:
            self.assertTrue(0 < len(nombre) <= 150, nombre)
            self.assertGreater(precio, 0, nombre)
            self.assertGreaterEqual(existencias, 0, nombre)
            self.assertTrue(descripcion, nombre)
            self.assertRegex(foto, r"^[a-z0-9-]+$")
            self.assertTrue(RUTA_PROPIA.match(f"/productos/{foto}.jpg"), nombre)

    def test_las_ofertas_son_de_productos_del_catalogo_y_bajan_el_precio(self):
        precios = {archivo: precio for _, _, precio, _, _, archivo in PRODUCTOS}
        for archivo, anterior in PRECIOS_ANTERIORES.items():
            self.assertIn(archivo, precios)
            self.assertGreater(anterior, precios[archivo])

    def test_las_fotos_listas_corresponden_a_productos(self):
        self.assertTrue(FOTOS_LISTAS <= {p[5] for p in PRODUCTOS})

    def test_hay_un_producto_agotado_para_mostrar_la_insignia(self):
        self.assertTrue(any(p[3] == 0 for p in PRODUCTOS))


class CargarCatalogoTests(TestCase):
    def test_carga_y_es_idempotente(self):
        cargar()
        total = Producto.objects.count()
        categorias = Categoria.objects.count()
        self.assertEqual(total, len(PRODUCTOS))

        salida = cargar()
        self.assertEqual(Producto.objects.count(), total)
        self.assertEqual(Categoria.objects.count(), categorias)
        self.assertIn("0 productos nuevos", salida)
        self.assertIn("0 fotos asignadas", salida)

    def test_reutiliza_categoria_existente_sin_distinguir_mayusculas(self):
        existente = Categoria.objects.create(nombre="silla")
        cargar()
        self.assertEqual(Categoria.objects.filter(nombre__iexact="silla").count(), 1)
        self.assertTrue(Producto.objects.filter(categoria=existente).exists())

    def test_no_toca_productos_que_ya_existen(self):
        categoria = Categoria.objects.create(nombre="Sala")
        propio = Producto.objects.create(
            nombre="sofá de tres puestos", precio=1, existencias=99, categoria=categoria
        )
        cargar()
        propio.refresh_from_db()
        self.assertEqual(propio.precio, 1)
        self.assertEqual(propio.existencias, 99)
        self.assertEqual(Producto.objects.filter(nombre__iexact="Sofá de tres puestos").count(), 1)

    def test_la_api_los_entrega_con_su_foto_solo_si_ya_existe(self):
        cargar()
        productos = APIClient().get("/api/productos/").json()
        self.assertEqual(len(productos), len(PRODUCTOS))
        con_foto = [p for p in productos if p["imagen"]]
        self.assertEqual(len(con_foto), len(FOTOS_LISTAS))
        self.assertTrue(all(re.match(r"^/productos/[a-z0-9-]+\.jpg$", p["imagen"]) for p in con_foto))

    def test_completa_la_foto_de_un_producto_del_catalogo_sin_imagen(self):
        cargar()
        producto = Producto.objects.get(nombre="Sofá de tres puestos")
        producto.imagen = ""
        producto.save()
        salida = cargar()
        producto.refresh_from_db()
        self.assertEqual(producto.imagen, "/productos/sofa-de-tres-puestos.jpg")
        self.assertIn("1 fotos asignadas", salida)

    def test_no_cambia_una_imagen_que_el_administrador_ya_puso(self):
        cargar()
        producto = Producto.objects.get(nombre="Sofá de tres puestos")
        producto.imagen = "https://ejemplo.com/otra.jpg"
        producto.save()
        cargar()
        producto.refresh_from_db()
        self.assertEqual(producto.imagen, "https://ejemplo.com/otra.jpg")


class ImagenDelProductoTests(TestCase):
    def setUp(self):
        self.admin = cliente_admin()
        self.categoria = Categoria.objects.create(nombre="Mueble")

    def crear(self, imagen):
        return self.admin.post(
            "/api/productos/",
            {"nombre": "Mesa", "precio": "1000.00", "existencias": 1, "imagen": imagen,
             "categoria": self.categoria.pk},
        )

    def test_acepta_ruta_propia_direccion_web_y_vacio(self):
        for valor in ["/productos/mesa.jpg", "https://ejemplo.com/mesa.jpg", "http://ejemplo.com/a.png", ""]:
            self.assertEqual(self.crear(valor).status_code, 201, valor)

    def test_rechaza_valores_peligrosos(self):
        for valor in ["javascript:alert(1)", "//otro.sitio/x.jpg", "data:text/html,hola",
                      "ftp://ejemplo.com/a.jpg", "mesa.jpg", "/..\\x", "/a b.jpg"]:
            respuesta = self.crear(valor)
            self.assertEqual(respuesta.status_code, 400, valor)
            self.assertIn("imagen", respuesta.json())


class PrecioAnteriorTests(TestCase):
    def setUp(self):
        self.admin = cliente_admin()
        self.categoria = Categoria.objects.create(nombre="Mueble")

    def crear(self, **extra):
        datos = {"nombre": "Mesa", "precio": "1000.00", "existencias": 1,
                 "categoria": self.categoria.pk}
        datos.update(extra)
        return self.admin.post("/api/productos/", datos, format="json")

    def test_la_carga_pone_precio_anterior_solo_a_las_ofertas(self):
        cargar()
        sofa = Producto.objects.get(nombre="Sofá de tres puestos")
        self.assertEqual(sofa.precio_anterior, PRECIOS_ANTERIORES["sofa-de-tres-puestos"])
        self.assertIsNone(Producto.objects.get(nombre="Mesa de noche").precio_anterior)

    def test_la_api_entrega_precio_anterior_o_null(self):
        cargar()
        productos = {p["nombre"]: p for p in APIClient().get("/api/productos/").json()}
        self.assertIsNotNone(productos["Mesa de centro"]["precio_anterior"])
        self.assertIsNone(productos["Mesa de noche"]["precio_anterior"])

    def test_se_puede_crear_sin_precio_anterior_o_con_null(self):
        self.assertEqual(self.crear().status_code, 201)
        respuesta = self.crear(nombre="Otra", precio_anterior=None)
        self.assertEqual(respuesta.status_code, 201)
        self.assertIsNone(respuesta.json()["precio_anterior"])

    def test_acepta_un_precio_anterior_mayor(self):
        respuesta = self.crear(precio_anterior="1500.00")
        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(respuesta.json()["precio_anterior"], "1500.00")

    def test_rechaza_un_precio_anterior_igual_menor_o_negativo(self):
        for valor in ["1000.00", "900.00", "-5"]:
            respuesta = self.crear(precio_anterior=valor)
            self.assertEqual(respuesta.status_code, 400, valor)
            self.assertIn("precio_anterior", respuesta.json())

    def test_al_bajar_el_precio_en_una_actualizacion_parcial_se_valida_contra_el_anterior(self):
        producto = self.crear(precio_anterior="1500.00").json()
        malo = self.admin.patch(f"/api/productos/{producto['id']}/", {"precio": "1600.00"}, format="json")
        self.assertEqual(malo.status_code, 400)
        bueno = self.admin.patch(f"/api/productos/{producto['id']}/", {"precio": "1200.00"}, format="json")
        self.assertEqual(bueno.status_code, 200)
        quitar = self.admin.patch(f"/api/productos/{producto['id']}/", {"precio_anterior": None}, format="json")
        self.assertEqual(quitar.status_code, 200)
        self.assertIsNone(quitar.json()["precio_anterior"])

    def test_el_carrito_cobra_el_precio_actual_no_el_anterior(self):
        producto = self.crear(precio_anterior="1500.00", existencias=5).json()
        cliente = APIClient()
        carrito = cliente.post("/api/carritos/").json()
        cliente.post(
            f"/api/carritos/{carrito['token']}/items/",
            {"producto": producto["id"], "cantidad": 2},
            format="json",
        )
        r = cliente.get(f"/api/carritos/{carrito['token']}/").json()
        self.assertEqual(r["total"], "2000.00")
