from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from catalogo.autenticacion import CsrfView, LoginView, LogoutView, RegistroView, YoView
from catalogo.carrito import (
    CarritoComprarView,
    CarritoDetalleView,
    CarritoItemDetalleView,
    CarritoItemsView,
    CarritosView,
)
from catalogo.salud import SaludView
from catalogo.views import CategoriaViewSet, ProductoViewSet

router = DefaultRouter()
router.register("categorias", CategoriaViewSet, basename="categoria")
router.register("productos", ProductoViewSet, basename="producto")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/csrf/", CsrfView.as_view(), name="auth-csrf"),
    path("api/auth/login/", LoginView.as_view(), name="auth-login"),
    path("api/auth/registro/", RegistroView.as_view(), name="auth-registro"),
    path("api/auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("api/auth/yo/", YoView.as_view(), name="auth-yo"),
    path("api/carritos/", CarritosView.as_view(), name="carrito-crear"),
    path("api/carritos/<uuid:token>/", CarritoDetalleView.as_view(), name="carrito-detalle"),
    path("api/carritos/<uuid:token>/items/", CarritoItemsView.as_view(), name="carrito-items"),
    path("api/carritos/<uuid:token>/comprar/", CarritoComprarView.as_view(), name="carrito-comprar"),
    path(
        "api/carritos/<uuid:token>/items/<int:item_id>/",
        CarritoItemDetalleView.as_view(),
        name="carrito-item-detalle",
    ),
    path("api/salud/", SaludView.as_view(), name="salud"),
    path("api/", include(router.urls)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]