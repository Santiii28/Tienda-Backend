from django.core.management.base import BaseCommand
from django.db import transaction

from catalogo.datos_catalogo import FOTOS_LISTAS, PRECIOS_ANTERIORES, PRODUCTOS
from catalogo.models import Categoria, Producto


class Command(BaseCommand):
    help = (
        "Carga el catálogo de demostración (categorías y productos). "
        "No duplica ni modifica lo que ya existe (solo completa la foto de los productos "
        "del catálogo que no tienen imagen): se puede ejecutar varias veces."
    )

    def handle(self, *args, **opciones):
        categorias_nuevas = 0
        productos_nuevos = 0
        productos_existentes = 0
        fotos_asignadas = 0

        with transaction.atomic():
            for nombre, categoria_nombre, precio, existencias, descripcion, archivo in PRODUCTOS:
                # Se busca sin distinguir mayúsculas ("silla" y "Silla" son la misma).
                categoria = Categoria.objects.filter(nombre__iexact=categoria_nombre).first()
                if categoria is None:
                    categoria = Categoria.objects.create(nombre=categoria_nombre)
                    categorias_nuevas += 1

                ruta = f"/productos/{archivo}.jpg" if archivo in FOTOS_LISTAS else ""

                existente = Producto.objects.filter(nombre__iexact=nombre).first()
                if existente is not None:
                    productos_existentes += 1
                    # Solo completa la foto si el producto no tiene ninguna.
                    if ruta and not existente.imagen:
                        existente.imagen = ruta
                        existente.save(update_fields=["imagen"])
                        fotos_asignadas += 1
                    continue

                Producto.objects.create(
                    nombre=nombre,
                    categoria=categoria,
                    precio=precio,
                    precio_anterior=PRECIOS_ANTERIORES.get(archivo),
                    existencias=existencias,
                    descripcion=descripcion,
                    imagen=ruta,
                )
                productos_nuevos += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Listo: {productos_nuevos} productos nuevos, "
                f"{categorias_nuevas} categorías nuevas, "
                f"{productos_existentes} productos que ya existían, "
                f"{fotos_asignadas} fotos asignadas a productos sin imagen."
            )
        )
