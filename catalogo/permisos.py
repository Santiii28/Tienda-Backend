from rest_framework.permissions import SAFE_METHODS, BasePermission


class SoloAdminEscribe(BasePermission):
    """Lectura pública; crear, editar y borrar solo para administradores."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)
