from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from .models import Carrito, Categoria, ItemCarrito, Producto


def borrar(*args):
    salida = StringIO()
    call_command("borrar_productos_sin_foto", *args, stdout=salida)
    return salida.getvalue()


class BorrarProductosSinFotoTests(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(nombre="Sala")
        self.con_foto = Producto.objects.create(
            nombre="Con foto", precio=1000, existencias=1, categoria=self.categoria,
            imagen="/productos/a.jpg",
        )
        self.sin_foto = Producto.objects.create(
            nombre="Sin foto", precio=1000, existencias=1, categoria=self.categoria
        )

    def test_borra_solo_los_que_no_tienen_foto(self):
        salida = borrar("--si")
        self.assertIn("1 productos borrados", salida)
        self.assertTrue(Producto.objects.filter(pk=self.con_foto.pk).exists())
        self.assertFalse(Producto.objects.filter(pk=self.sin_foto.pk).exists())

    def test_pide_confirmacion_y_cancela_si_no_se_escribe_si(self):
        with patch("builtins.input", return_value="no"):
            salida = borrar()
        self.assertIn("Cancelado", salida)
        self.assertTrue(Producto.objects.filter(pk=self.sin_foto.pk).exists())

    def test_borra_si_se_confirma(self):
        with patch("builtins.input", return_value="si"):
            borrar()
        self.assertFalse(Producto.objects.filter(pk=self.sin_foto.pk).exists())

    def test_no_borra_un_producto_que_esta_en_un_carrito_y_lo_avisa(self):
        ItemCarrito.objects.create(carrito=Carrito.objects.create(), producto=self.sin_foto, cantidad=1)
        salida = borrar("--si")
        self.assertIn("0 productos borrados", salida)
        self.assertIn("Sin foto", salida)
        self.assertTrue(Producto.objects.filter(pk=self.sin_foto.pk).exists())

    def test_sin_productos_sin_foto_no_hace_nada(self):
        self.sin_foto.delete()
        self.assertIn("nada que borrar", borrar("--si"))
