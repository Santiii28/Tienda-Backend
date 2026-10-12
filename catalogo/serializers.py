from rest_framework import serializers

from .models import Carrito, Categoria, ItemCarrito, Producto


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ["id", "nombre", "descripcion"]


class ProductoSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source="categoria.nombre", read_only=True)

    class Meta:
        model = Producto
        fields = [
            "id",
            "nombre",
            "precio",
            "existencias",
            "descripcion",
            "imagen",
            "categoria",
            "categoria_nombre",
        ]


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

    class Meta:
        model = Carrito
        fields = ["token", "fecha_creacion", "items", "total"]


class AgregarItemSerializer(serializers.Serializer):
    producto = serializers.PrimaryKeyRelatedField(queryset=Producto.objects.all())
    cantidad = serializers.IntegerField(min_value=1, default=1)


class CambiarCantidadSerializer(serializers.Serializer):
    cantidad = serializers.IntegerField(min_value=1)
