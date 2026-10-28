from django.core.management.base import BaseCommand
from django.db.models import ProtectedError, Q

from catalogo.models import Producto


class Command(BaseCommand):
    help = (
        "Borra los productos que no tienen foto (imagen vacía). Muestra la lista y pide "
        "confirmación; con --si no pregunta. Un producto que está en algún carrito no se "
        "puede borrar (protección de la base de datos) y se avisa. "
        "Ojo: 'cargar_catalogo' vuelve a crear los productos del catálogo que no tengan foto lista."
    )

    def add_arguments(self, parser):
        parser.add_argument("--si", action="store_true", help="Borrar sin pedir confirmación.")

    def handle(self, *args, **opciones):
        sin_foto = Producto.objects.filter(Q(imagen="") | Q(imagen__isnull=True)).order_by("nombre")
        if not sin_foto.exists():
            self.stdout.write("Todos los productos tienen foto. No hay nada que borrar.")
            return

        self.stdout.write("Productos sin foto:")
        for producto in sin_foto:
            self.stdout.write(f"  - {producto.nombre} ({producto.categoria.nombre})")

        if not opciones["si"]:
            respuesta = input("¿Borrarlos? Escribe SI para confirmar: ").strip().upper()
            if respuesta != "SI":
                self.stdout.write("Cancelado. No se borró nada.")
                return

        borrados = 0
        protegidos = []
        for producto in list(sin_foto):
            try:
                producto.delete()
                borrados += 1
            except ProtectedError:
                protegidos.append(producto.nombre)

        self.stdout.write(self.style.SUCCESS(f"Listo: {borrados} productos borrados."))
        if protegidos:
            self.stdout.write(
                self.style.WARNING(
                    "No se pudieron borrar porque están en algún carrito: " + ", ".join(protegidos)
                    + ". Quita esos productos de los carritos o bórralos desde el panel cuando ya no estén."
                )
            )
