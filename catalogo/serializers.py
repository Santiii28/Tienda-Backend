import re

from django.core.validators import URLValidator
from django.core.exceptions import ValidationError as ErrorDeDjango
from rest_framework import serializers

from .models import Carrito, Categoria, ItemCarrito, Producto


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ["id", "nombre", "descripcion"]


# Ruta de una foto de este mismo sitio, por ejemplo "/productos/mesa.jpg".
# No acepta "//otro.sitio" ni barras invertidas.
RUTA_PROPIA = re.compile(r"^/(?![/\\])[\w\-./%]+$")


class ProductoSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source="categoria.nombre", read_only=True)
    # La imagen puede ser una dirección web (http/https) o una ruta de la tienda.
    imagen = serializers.CharField(max_length=200, allow_blank=True, required=False)

    class Meta:
        model = Producto
        fields = [
            "id",
            "nombre",
            "precio",
            "precio_anterior",
            "existencias",
            "descripcion",
            "imagen",
            "categoria",
            "categoria_nombre",
        ]
        # Un precio negativo haría que el total del carrito se calcule mal.
        extra_kwargs = {"precio": {"min_value": 0}, "precio_anterior": {"min_value": 0}}

    def validate(self, datos):
        # Un precio anterior solo tiene sentido si es mayor que el precio actual.
        # En una actualización parcial se usa el valor que ya tiene el producto.
        precio = datos.get("precio", getattr(self.instance, "precio", None))
        anterior = datos.get("precio_anterior", getattr(self.instance, "precio_anterior", None))
        if anterior is not None and precio is not None and anterior <= precio:
            raise serializers.ValidationError(
                {"precio_anterior": "El precio anterior debe ser mayor que el precio actual."}
            )
        return datos

    def validate_imagen(self, valor):
        valor = valor.strip()
        if valor == "" or RUTA_PROPIA.match(valor):
            return valor
        try:
            URLValidator(schemes=["http", "https"])(valor)
        except ErrorDeDjango:
            raise serializers.ValidationError(
                "Escribe una dirección web (http o https) o una ruta que empiece con /."
            )
        return valor


class ItemCarritoSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    precio_unitario = serializers.DecimalField(
        source="producto.precio", max_digits=12, decimal_places=2, read_only=True
    )
    existencias = serializers.IntegerField(
        source="producto.existencias", read_only=True
    )
    subtotal = serializers.DecimalField(
        source="calcular_subtotal", max_digits=14, decimal_places=2, read_only=True
    )

    class Meta:
        model = ItemCarrito
        fields = [
            "id",
            "producto",
            "producto_nombre",
            "precio_unitario",
            "existencias",
            "cantidad",
            "subtotal",
        ]


class CarritoSerializer(serializers.ModelSerializer):
    items = ItemCarritoSerializer(many=True, read_only=True)
    total = serializers.DecimalField(
        source="calcular_total", max_digits=14, decimal_places=2, read_only=True
    )
    envio = serializers.DecimalField(
        source="calcular_envio", max_digits=14, decimal_places=2, read_only=True
    )
    total_a_pagar = serializers.DecimalField(
        source="calcular_total_a_pagar", max_digits=14, decimal_places=2, read_only=True
    )

    class Meta:
        model = Carrito
        fields = ["token", "fecha_creacion", "items", "total", "envio", "total_a_pagar"]


class AgregarItemSerializer(serializers.Serializer):
    producto = serializers.PrimaryKeyRelatedField(queryset=Producto.objects.all())
    cantidad = serializers.IntegerField(min_value=1, default=1)


class CambiarCantidadSerializer(serializers.Serializer):
    cantidad = serializers.IntegerField(min_value=1)


class ComprarSerializer(serializers.Serializer):
    """Datos de contacto y entrega. Se validan, pero no se guardan en ninguna parte."""

    nombre = serializers.CharField(max_length=100)
    correo = serializers.EmailField(max_length=150)
    telefono = serializers.RegexField(
        r"^[0-9+()\- ]{7,20}$",
        error_messages={"invalid": "Escribe un teléfono válido (solo números, de 7 a 20 caracteres)."},
    )
    direccion = serializers.CharField(max_length=200)
    ciudad = serializers.CharField(max_length=100)


class LineaCompraSerializer(serializers.Serializer):
    producto_nombre = serializers.CharField()
    cantidad = serializers.IntegerField()
    subtotal = serializers.DecimalField(max_digits=14, decimal_places=2)


class CompraRealizadaSerializer(serializers.Serializer):
    mensaje = serializers.CharField()
    nombre = serializers.CharField()
    direccion = serializers.CharField()
    ciudad = serializers.CharField()
    items = LineaCompraSerializer(many=True)
    total = serializers.DecimalField(max_digits=14, decimal_places=2)
    envio = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_a_pagar = serializers.DecimalField(max_digits=14, decimal_places=2)
