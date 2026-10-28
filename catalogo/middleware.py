class SinCacheEnDatosPrivados:
    """Evita que el navegador o un proxy guarde en caché las respuestas de
    la sesión y del carrito (datos que cambian y que son de un solo visitante)."""

    PREFIJOS = ("/api/auth/", "/api/carritos/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        respuesta = self.get_response(request)
        if request.path.startswith(self.PREFIJOS):
            respuesta["Cache-Control"] = "no-store"
        return respuesta


class BarraFinalEnApi:
    """Acepta las rutas de la API con o sin barra final.

    Django exige la barra final (APPEND_SLASH) y, si falta, responde con una
    redirección hacia el dominio del backend. Detrás del proxy del frontend
    (rewrite de Vercel) esa redirección sacaría al navegador del dominio único
    y rompería las cookies, así que aquí se completa la barra sin redirigir.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ruta = request.path_info
        if ruta.startswith("/api/") and not ruta.endswith("/"):
            request.path_info = ruta + "/"
        return self.get_response(request)
