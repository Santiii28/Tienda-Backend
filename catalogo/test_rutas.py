"""La API acepta las rutas con o sin barra final (ver BarraFinalEnApi)."""

from django.test import TestCase
from rest_framework.test import APIClient

from .models import Categoria


class BarraFinalTests(TestCase):
    def test_sin_barra_final_responde_directo_sin_redireccion(self):
        Categoria.objects.create(nombre="Mueble")
        for ruta in ("/api/categorias", "/api/productos", "/api/auth/yo", "/api/salud"):
            respuesta = APIClient().get(ruta)
            self.assertEqual(respuesta.status_code, 200, ruta)

    def test_con_barra_final_sigue_funcionando(self):
        self.assertEqual(APIClient().get("/api/categorias/").status_code, 200)

    def test_una_escritura_sin_barra_final_no_se_convierte_en_get(self):
        # Una redirección 301 convertiría el POST en GET y la creación se perdería.
        respuesta = APIClient().post("/api/carritos", format="json")
        self.assertEqual(respuesta.status_code, 201)

    def test_las_rutas_fuera_de_la_api_no_se_tocan(self):
        respuesta = APIClient().get("/ruta-que-no-existe")
        self.assertEqual(respuesta.status_code, 404)
