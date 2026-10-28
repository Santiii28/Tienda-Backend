# Tienda en Línea Modular — Backend

API REST de la **Tienda en Línea Modular** (Proyecto de Aula, Desarrollo de Aplicaciones Web). Expone el catálogo de categorías y productos, el carrito de compras y el inicio de sesión del administrador. **No renderiza vistas**: toda la comunicación con el frontend pasa por peticiones HTTP a esta API.

El frontend es un proyecto independiente: [Tienda-Frontend](https://github.com/Santiii28/Tienda-Frontend).

## Tecnologías

| Pieza | Herramienta |
|---|---|
| Lenguaje y framework | Python 3.13, Django 6.1.1 |
| API REST | Django REST Framework 3.18.1 |
| Documentación | drf-spectacular (OpenAPI 3 + Swagger UI) |
| Base de datos | PostgreSQL en Neon (SQLite solo para las pruebas) |
| Servidor de producción | gunicorn + WhiteNoise |
| Despliegue previsto | Render (backend), Vercel (frontend), Neon (base de datos) |

## Ejecutar en local

Requisitos: Python 3.13 y una cadena de conexión de Neon.

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # y completa los valores
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

La API queda en `http://127.0.0.1:8000/`. El administrador debe ser un usuario con `is_staff` (el superusuario lo es).

### Catálogo de demostración

`python manage.py cargar_catalogo` agrega 24 productos de ejemplo en 7 categorías (silla, sala, comedor, dormitorio, oficina, almacenamiento y decoración e iluminación). No duplica ni modifica lo que ya existe, así que se puede ejecutar varias veces. Los nombres, precios y existencias son datos de demostración, no un inventario real, y están en `catalogo/datos_catalogo.py`. Cuatro de ellos traen un `precio_anterior` de ejemplo (oferta de demostración, no una promoción real). Cada producto apunta a una foto con la ruta `/productos/<archivo>.jpg`, que sirve el frontend desde su carpeta `public/productos/`; mientras la foto no exista, la tarjeta muestra la letra inicial.

### Variables de entorno

| Variable | Para qué sirve |
|---|---|
| `SECRET_KEY` | Clave secreta de Django. Obligatoria si `DEBUG` no es `True`. |
| `DEBUG` | `True` solo en local. Si no existe se asume producción. |
| `ALLOWED_HOSTS` | Hosts permitidos, separados por comas. |
| `DATABASE_URL` | Cadena de conexión de PostgreSQL (Neon). |
| `FRONTEND_ORIGINS` | Dominio(s) del frontend en producción, separados por comas y sin barra final. Se agregan a CORS y a los orígenes de confianza de CSRF. |
| `HSTS_SECONDS` | Opcional. Duración de HSTS en segundos (por defecto un año). |
| `COSTO_ENVIO` | Opcional. Costo fijo de envío en pesos (por defecto `10000`). |

El archivo `.env` está en `.gitignore`: no se sube al repositorio.

## Documentación de la API

Con el servidor en marcha:

- Swagger UI: `/api/docs/`
- Esquema OpenAPI: `/api/schema/`

### Endpoints

| Método y ruta | Descripción | Quién puede |
|---|---|---|
| `GET /api/categorias/` · `GET /api/categorias/{id}/` | Listar y ver categorías | Público |
| `POST` · `PUT` · `PATCH` · `DELETE /api/categorias/…` | Crear, editar y eliminar categorías | Administrador |
| `GET /api/productos/` (`?categoria={id}`) · `GET /api/productos/{id}/` | Listar (filtrable por categoría) y ver productos | Público |
| `POST` · `PUT` · `PATCH` · `DELETE /api/productos/…` | Crear, editar y eliminar productos | Administrador |
| `POST /api/carritos/` | Crear un carrito vacío; devuelve su `token` | Público |
| `GET /api/carritos/{token}/` | Ver el carrito con subtotal, envío y total a pagar | Quien tenga el token |
| `POST /api/carritos/{token}/items/` | Agregar un producto (suma si ya estaba) | Quien tenga el token |
| `PATCH` · `DELETE /api/carritos/{token}/items/{id}/` | Cambiar la cantidad o quitar un producto | Quien tenga el token |
| `POST /api/carritos/{token}/comprar/` | Compra simulada: valida contacto y entrega, devuelve el resumen y vacía el carrito | Quien tenga el token |
| `GET /api/auth/csrf/` | Entrega la cookie `csrftoken` | Público |
| `POST /api/auth/login/` · `POST /api/auth/logout/` · `GET /api/auth/yo/` | Sesión del administrador | Ver abajo |
| `GET /api/salud/` | Estado del servicio (lo usa Render) | Público |

Reglas del carrito: no permite superar las existencias (responde 400 con el mensaje) y cada respuesta incluye el `total` recalculado, el `envio` (fijo, $ 10.000, variable `COSTO_ENVIO`; $ 0 si el carrito está vacío) y el `total_a_pagar`. La compra es simulada: no hay pasarela ni datos de tarjeta, no guarda los datos del comprador y no descuenta existencias (no hay pedidos en el alcance); responde 400 si el carrito está vacío o los datos son inválidos y 409 si las existencias ya no alcanzan.

Eliminar una categoría con productos, o un producto que esté en algún carrito, responde **409** con un mensaje en español.

## Seguridad

- **Autenticación:** sesión de Django. `POST /api/auth/login/` solo admite usuarios con `is_staff`.
- **Permisos:** `SoloAdminEscribe` es el permiso por defecto de toda la API: la lectura es pública y cualquier escritura exige un administrador.
- **CSRF:** toda petición que modifica datos con sesión abierta debe llevar la cabecera `X-CSRFToken` (el valor de la cookie `csrftoken`). Sin ella la API responde `403 CSRF Failed`. El login también la exige. Los orígenes de confianza salen de `FRONTEND_ORIGINS`.
- **HTTPS (con `DEBUG` apagado):** redirección a HTTPS, cookies de sesión y CSRF con `Secure`, HSTS, y detección del esquema por `X-Forwarded-Proto` (el hosting termina el TLS).
- **XSS:** la API responde siempre JSON con `X-Content-Type-Options: nosniff`, y la URL de imagen de un producto solo admite `http`/`https`. La defensa principal está en el frontend, que escribe los datos con `textContent` y nunca con `innerHTML`.
- **Cabeceras:** `X-Frame-Options: DENY`, `Referrer-Policy: same-origin`, y `Cache-Control: no-store` en las rutas de sesión y carrito.

Revisión automática de Django para producción:

```powershell
$env:DEBUG="False"; $env:SECRET_KEY="una-clave-larga-y-aleatoria"; python manage.py check --deploy
```

## Pruebas

Las pruebas usan SQLite en memoria, así que no tocan la base de datos de Neon:

```powershell
$env:DATABASE_URL="sqlite:///pruebas.sqlite3"
python manage.py test catalogo
```

Cubren el CRUD de categorías y productos, el filtro por categoría, el login y los permisos, la protección CSRF (con y sin token, origen no confiable), la carga del catálogo de demostración, el precio anterior de las ofertas (debe ser mayor que el precio, y el carrito cobra siempre el precio actual), la validación de la imagen (dirección web o ruta propia, nunca `javascript:`), el carrito (recálculo del total, existencias, aislamiento entre carritos), el envío y la compra simulada y la configuración de HTTPS, cookies y XSS.

## Despliegue en Render

El archivo `render.yaml` describe el servicio y `build.sh` instala dependencias, reúne los estáticos y aplica las migraciones. Pasos:

1. En Render: **New → Blueprint** y elegir este repositorio.
2. Completar las variables que Render deja en blanco: `DATABASE_URL` (la de Neon) y `FRONTEND_ORIGINS` (el dominio de Vercel).
3. Esperar el despliegue y comprobar `https://<servicio>.onrender.com/api/salud/` y `/api/docs/`.

El plan gratuito de Render duerme el servicio tras 15 minutos sin tráfico: la primera petición después tarda cerca de un minuto en responder.

## Estructura

```
config/                 Configuración de Django (settings, urls, wsgi)
catalogo/
  models.py             Categoria, Producto, Carrito, ItemCarrito
  serializers.py        Serializadores de la API
  views.py              CRUD de categorías y productos
  carrito.py            Endpoints del carrito
  autenticacion.py      Login, logout, CSRF y sesión
  permisos.py           Permiso SoloAdminEscribe
  middleware.py         Cache-Control: no-store en sesión y carrito
  salud.py              Chequeo de salud
  datos_catalogo.py     Productos del catálogo de demostración
  management/commands/  cargar_catalogo (carga el catálogo de demostración)
  tests.py, test_*.py   Pruebas automáticas
build.sh                Comando de build de Render
render.yaml             Definición del servicio en Render
```
