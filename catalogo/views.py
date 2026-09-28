from rest_framework import viewsets

from .models import Categoria, Producto
from .serializers import CategoriaSerializer, ProductoSerializer


class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer


class ProductoViewSet(viewsets.ModelViewSet):
    serializer_class = ProductoSerializer

    def get_queryset(self):
        queryset = Producto.objects.select_related("categoria")
        categoria_id = self.request.query_params.get("categoria")
        if categoria_id:
            queryset = queryset.filter(categoria_id=categoria_id)
        return queryset