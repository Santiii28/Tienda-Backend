"""Defensas contra la fuerza bruta en el login y registro de eventos de seguridad.

Los intentos fallidos se cuentan por usuario (no por IP): detrás del
intermediario de Vercel todas las peticiones llegan desde las mismas
direcciones, así que la IP no identifica a quien ataca. La cuenta se bloquea
unos minutos y el contador se borra al entrar bien.

El contador vive en la caché de Django. En el plan gratuito de Render se
ejecuta un solo proceso de gunicorn, por eso la caché en memoria alcanza;
con varios procesos habría que usar Redis o una tabla de caché.
"""

import hashlib
import logging

from django.conf import settings
from django.core.cache import cache

registro = logging.getLogger("tienda.seguridad")


def _clave(usuario):
    resumen = hashlib.sha256(usuario.strip().lower().encode("utf-8")).hexdigest()
    return "login-fallos:" + resumen


def bloqueado(usuario):
    return cache.get(_clave(usuario), 0) >= settings.LOGIN_MAX_INTENTOS


def registrar_fallo(usuario):
    """Suma un intento fallido y devuelve el total. La ventana empieza con el primero."""
    clave = _clave(usuario)
    cache.add(clave, 0, settings.LOGIN_VENTANA_SEGUNDOS)
    try:
        return cache.incr(clave)
    except ValueError:  # la entrada venció justo ahora
        cache.set(clave, 1, settings.LOGIN_VENTANA_SEGUNDOS)
        return 1


def limpiar_fallos(usuario):
    cache.delete(_clave(usuario))


def enmascarar(usuario):
    """«ana.perez@correo.com» -> «an***@correo.com»: el registro no guarda el correo completo."""
    nombre, arroba, dominio = usuario.partition("@")
    return nombre[:2] + "***" + arroba + dominio
