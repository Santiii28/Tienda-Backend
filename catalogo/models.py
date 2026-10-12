import uuid

from django.db import models


class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "categoría"
        verbose_name_plural = "categorías"

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    nombre = models.CharField(max_length=150)
    precio = models.DecimalField(max_digits=12, decimal_places=2)
    existencias = models.PositiveIntegerField(default=0)
    descripcion = models.TextField(blank=True)
    imagen = models.URLField(blank=True)
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name="productos",
    )

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    def hay_existencias(self, cantidad):
        return self.existencias >= cantidad


class Carrito(models.Model):
    # Identifica al carrito de un visitante anónimo (no hay registro de clientes).
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Carrito {self.pk}"

    def calcular_total(self):
        return sum(item.calcular_subtotal() for item in self.items.all())


class ItemCarrito(models.Model):
    carrito = models.ForeignKey(
        Carrito,
        on_delete=models.CASCADE,
        related_name="items",
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
    )
    cantidad = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["carrito", "producto"],
                name="producto_unico_por_carrito",
            )
        ]

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"

    def calcular_subtotal(self):
        return self.cantidad * self.producto.precio