from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Carrito, ItemCarrito
from .serializers import (
    AgregarItemSerializer,
    CambiarCantidadSerializer,
    CarritoSerializer,
)

# El carrito de un visitante se identifica solo por su token (va en la URL).
# No usa la sesión ni cookies, así que no depende de CSRF: authentication_classes
# vacío evita además que una sesión de administrador abierta bloquee estas
# peticiones por falta de token CSRF.


class VistaCarrito(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def obtener_carrito(self, token):
        return get_object_or_404(
            Carrito.objects.prefetch_related("items__producto"), token=token
        )

    def respuesta(self, carrito, codigo=status.HTTP_200_OK):
        carrito = self.obtener_carrito(carrito.token)  # relee con los items al día
        return Response(CarritoSerializer(carrito).data, status=codigo)


def error_existencias(producto):
    if producto.existencias == 0:
        mensaje = "Este producto está agotado."
    else:
        mensaje = f"Solo hay {producto.existencias} disponibles."
    return Response({"cantidad": [mensaje]}, status=status.HTTP_400_BAD_REQUEST)


class CarritosView(VistaCarrito):
    @extend_schema(
        summary="Crear un carrito vacío",
        request=None,
        responses={201: CarritoSerializer},
    )
    def post(self, request):
        carrito = Carrito.objects.create()
        return self.respuesta(carrito, status.HTTP_201_CREATED)


class CarritoDetalleView(VistaCarrito):
    @extend_schema(summary="Ver el carrito y su total", responses=CarritoSerializer)
    def get(self, request, token):
        return self.respuesta(self.obtener_carrito(token))


class CarritoItemsView(VistaCarrito):
    @extend_schema(
        summary="Agregar un producto al carrito",
        description="Si el producto ya estaba, suma la cantidad. "
        "No permite superar las existencias.",
        request=AgregarItemSerializer,
        responses=CarritoSerializer,
    )
    def post(self, request, token):
        carrito = self.obtener_carrito(token)
        datos = AgregarItemSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        producto = datos.validated_data["producto"]
        cantidad = datos.validated_data["cantidad"]

        item = ItemCarrito.objects.filter(carrito=carrito, producto=producto).first()
        nueva_cantidad = cantidad + (item.cantidad if item else 0)
        if not producto.hay_existencias(nueva_cantidad):
            return error_existencias(producto)

        if item:
            item.cantidad = nueva_cantidad
            item.save()
        else:
            ItemCarrito.objects.create(
                carrito=carrito, producto=producto, cantidad=cantidad
            )
        return self.respuesta(carrito)


class CarritoItemDetalleView(VistaCarrito):
    def obtener_item(self, carrito, item_id):
        return get_object_or_404(ItemCarrito, carrito=carrito, pk=item_id)

    @extend_schema(
        summary="Cambiar la cantidad de un producto del carrito",
        request=CambiarCantidadSerializer,
        responses=CarritoSerializer,
    )
    def patch(self, request, token, item_id):
        carrito = self.obtener_carrito(token)
        item = self.obtener_item(carrito, item_id)
        datos = CambiarCantidadSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        cantidad = datos.validated_data["cantidad"]

        if not item.producto.hay_existencias(cantidad):
            return error_existencias(item.producto)

        item.cantidad = cantidad
        item.save()
        return self.respuesta(carrito)

    @extend_schema(summary="Quitar un producto del carrito", responses=CarritoSerializer)
    def delete(self, request, token, item_id):
        carrito = self.obtener_carrito(token)
        self.obtener_item(carrito, item_id).delete()
        return self.respuesta(carrito)
