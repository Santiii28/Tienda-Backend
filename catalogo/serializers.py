from rest_framework import serializers

from .models import Categoria, Producto


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