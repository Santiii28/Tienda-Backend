from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class EstadoSerializer(serializers.Serializer):
    estado = serializers.CharField()


class SaludView(APIView):
    """Responde sin tocar la base de datos. Lo usa el hosting para saber si
    el servicio está vivo."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(summary="Estado del servicio", responses={200: EstadoSerializer})
    def get(self, request):
        return Response({"estado": "ok"})
