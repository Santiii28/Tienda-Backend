# Informe de seguridad — Tienda en Línea Modular (Taller Nogal)

**Autor:** Santiago Anaya · **Materia:** Desarrollo de Aplicaciones Web (UPB)
**Rama:** `seguridad` · **Stack:** Django 6.1.1 + DRF 3.18.2 + PostgreSQL (Neon) en Render; frontend Vite en Vercel

> Marcas: **[HECHO]** verificado con pruebas automáticas o comandos; **[PENDIENTE]** requiere evidencia manual (navegador, capturas) o dato que no está confirmado.

---

## 1. Diagnóstico inicial

| # | Hallazgo | OWASP | Evidencia | Corrección aplicada | Estado |
|---|----------|-------|-----------|---------------------|--------|
| 1 | El login no limitaba intentos: se podían probar contraseñas sin freno | A07 | Antes: 6.º intento fallido seguía respondiendo 401 | Límite de 5 fallos por usuario en 15 min; el 6.º responde **429** con `Retry-After: 900` (`catalogo/seguridad.py`, `autenticacion.py`) | HECHO |
| 2 | Las rutas inexistentes y los errores internos podían mostrar páginas HTML de Django | A05 | — | `handler404`/`handler500` devuelven JSON genérico (`{"detail": "No encontrado."}`) en `config/urls.py` | HECHO |
| 3 | No había registro de eventos de seguridad | A09 | — | `LOGGING` en `settings.py`; se registra login fallido (usuario enmascarado, ej. `sa***@correo.com`, y "intento N de 5") y login exitoso (id y rol). Nunca se registran contraseñas | HECHO |
| 4 | DRF 3.18.1 con vulnerabilidades conocidas | A06 | `pip-audit` reportó CVE en DRF | Actualizado a `djangorestframework==3.18.2`; `pip-audit` → *No known vulnerabilities found* | HECHO |
| 5 | Mensaje de login distinto según si el usuario existe | A07 | — | Ya era genérico: "Usuario o contraseña incorrectos." para ambos casos (prueba incluida) | HECHO |
| 6 | Sin cabecera `Content-Security-Policy` en el frontend | A05 | `index.html` no la define | Mitigado: el frontend usa `textContent` y no `innerHTML` con datos de la API (`src/utils.js`). La cabecera CSP en Vercel (`vercel.json`) queda como mejora | PENDIENTE |

## 2. Lo que ya estaba bien (verificado con pruebas)

- **HTTPS y HSTS:** con `DEBUG=False`, http → https (301), `Strict-Transport-Security: max-age=31536000`, `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: same-origin` (`test_seguridad.py`).
- **Cookies:** sesión `HttpOnly` + `Secure` + `SameSite=Lax`; `csrftoken` `Secure` + `SameSite=Lax` y legible por JS (necesario para el encabezado `X-CSRFToken`).
- **Contraseñas:** hash PBKDF2 de Django; nunca en texto plano.
- **CSRF:** escritura sin token → 403; token falso → 403; origen no confiable → 403 aunque lleve token (`CsrfTests`).
- **Roles:** lectura pública; escribir catálogo exige `is_staff`. El registro nunca crea administradores (`test_cuentas.py`).
- **Secretos:** `SECRET_KEY`, `DATABASE_URL` y orígenes salen de variables de entorno; `.env` está en `.gitignore`; `.env.example` solo trae valores de ejemplo. Con `DEBUG=False` la app se niega a arrancar con una clave insegura.
- **CORS/CSRF:** solo los orígenes de `FRONTEND_ORIGINS`.
- **XSS:** la compra con `<img src=x onerror=alert(1)>` se devuelve como texto en JSON (`test_compra.py`).
- **IDOR en carrito:** el carrito se identifica por un UUID aleatorio no adivinable; token desconocido → 404.

## 3. Cambios de esta rama (por archivo)

| Archivo | Cambio |
|---------|--------|
| `catalogo/seguridad.py` (nuevo) | Contador de fallos por usuario en caché (clave = SHA-256 del usuario en minúsculas), bloqueo, limpieza y enmascarado para logs |
| `catalogo/autenticacion.py` | `LoginView`: 429 + `Retry-After`, registro de fallos/aciertos, reinicio al acertar |
| `config/settings.py` | `LOGIN_MAX_INTENTOS` (5) y `LOGIN_VENTANA_SEGUNDOS` (900), configurables por variable de entorno; caché `LocMem`; `LOGGING` |
| `config/urls.py` | `handler404` y `handler500` en JSON |
| `catalogo/test_laboratorio_seguridad.py` (nuevo) | 21 pruebas del laboratorio |
| `requirements.txt` | DRF 3.18.1 → 3.18.2 |

**Decisión de diseño — límite por usuario y no por IP:** el frontend llega al backend a través del proxy de Vercel, así que todas las peticiones parecen venir de la misma IP; limitar por IP bloquearía a todos a la vez. **Contrapartida:** alguien podría bloquear temporalmente la cuenta de otra persona fallando a propósito (15 min). **Limitación:** la caché es por proceso; funciona porque Render (plan gratuito) corre un solo worker de gunicorn. Si se escalara a varios workers habría que usar Redis o la base de datos.

## 4. Verificaciones ejecutadas

| Comprobación | Resultado |
|--------------|-----------|
| `python manage.py test` | 150 pruebas, OK |
| `pip-audit -r requirements.txt` | No known vulnerabilities found |
| `python manage.py check --deploy` (con `SECRET_KEY` larga y `DEBUG=False`) | Sin advertencias propias del proyecto. La W009 solo aparece si la clave es corta; en Render debe ser una clave larga aleatoria |
| Servidor real con gunicorn | 301 http→https; cabeceras de seguridad; 404 JSON genérico; intentos 1–5 → 401, intento 6 → **429** (`Retry-After: 900`); logs con correo enmascarado |

## 5. Pruebas de A06 (no confiar en datos del cliente)

| Prueba | Resultado esperado | Estado |
|--------|--------------------|--------|
| Registro enviando `is_staff: true` / `is_superuser: true` / `rol: admin` | Se ignora; el usuario queda sin privilegios | HECHO (prueba automática) |
| Agregar al carrito cantidad negativa o cero | 400, el carrito no cambia | HECHO (prueba automática) |
| Cliente intentando enviar `precio` o `total` propios | El servidor calcula con el precio de la base de datos | HECHO (prueba automática) |

## 6. Mapa OWASP Top 10 (2021)

| Código | Categoría | Situación en el proyecto |
|--------|-----------|--------------------------|
| A01 | Control de acceso roto | Escritura solo `is_staff`; carrito por UUID; pruebas de permisos |
| A02 | Fallas criptográficas | HTTPS + HSTS, cookies `Secure`, PBKDF2 |
| A03 | Inyección | ORM de Django (consultas parametrizadas); sin SQL crudo; salida por `textContent` |
| A04 | Diseño inseguro | Total y envío se calculan en el servidor; la compra es simulada y no guarda datos de pago |
| A05 | Configuración incorrecta | `DEBUG=False` por defecto, `ALLOWED_HOSTS`, errores genéricos; **falta CSP** (hallazgo 6) |
| A06 | Componentes vulnerables | `pip-audit` limpio tras actualizar DRF; repetir antes de cada entrega |
| A07 | Fallas de autenticación | Límite de intentos 429, mensaje genérico, sesión con cookie HttpOnly |
| A08 | Integridad de software | Dependencias con versión fija en `requirements.txt`; **sin firma de artefactos** |
| A09 | Fallas de registro y monitoreo | `LOGGING` con eventos de login; **no hay alertas automáticas** |
| A10 | SSRF | El backend no hace peticiones a URLs que entregue el usuario (la URL de imagen se valida y solo se muestra) |

## 7. Matriz de riesgos

| # | Riesgo | Probabilidad | Impacto | Tratamiento |
|---|--------|--------------|---------|-------------|
| R1 | Fuga de la cadena de conexión de Neon (`DATABASE_URL`) | Media | Alto | Mitigar: solo en variables de Render, nunca en git; rotar la contraseña si se expone (ver plan §8) |
| R2 | Fuerza bruta contra el login | Media | Medio | Mitigado: 429 tras 5 fallos; vigilar logs |
| R3 | Bloqueo intencional de cuenta ajena (efecto del límite por usuario) | Baja | Bajo | Aceptar: el bloqueo dura 15 min |
| R4 | Dependencia con vulnerabilidad nueva | Media | Medio | Mitigar: `pip-audit` periódico y antes de cada entrega |
| R5 | XSS por contenido del catálogo | Baja | Alto | Mitigado: `textContent`; reforzar con CSP |

## 8. Plan de respuesta a incidentes (NIST SP 800-61) — fuga de la cadena de conexión de Neon

1. **Preparación:** secretos solo en variables de entorno de Render; `.env` ignorado; copia de seguridad disponible en Neon.
2. **Detección y análisis:** ver si aparece en el repositorio (`git log -S "postgres"`), revisar actividad inusual en el panel de Neon y los logs de Render; definir desde cuándo estuvo expuesta.
3. **Contención:** rotar de inmediato la contraseña del rol en Neon (o crear un rol nuevo y revocar el anterior); actualizar `DATABASE_URL` en Render y redesplegar.
4. **Erradicación:** si estuvo en git, eliminarla del historial y asumir que está comprometida aunque se borre; revisar que no existan otras copias (capturas, chats, documentos).
5. **Recuperación:** comprobar la tienda (catálogo, registro, login, compra), revisar que no haya filas ni usuarios extraños, restaurar desde copia si hay alteraciones.
6. **Lecciones aprendidas:** documentar causa y tiempo de detección; añadir revisión de secretos antes de cada commit.

## 9. Datos personales (Ley 1581 de 2012)

La compra recoge nombre, correo, teléfono, dirección y ciudad. Medidas: se piden solo los datos necesarios para el envío, viajan por HTTPS, la contraseña se guarda con hash y el pago es simulado (no se guardan datos de tarjeta). **[PENDIENTE]** Para un uso real faltaría: política de tratamiento de datos visible, autorización expresa del titular antes de enviar el formulario y un procedimiento para consultar, corregir o eliminar sus datos.

## 10. Respuestas de cierre

**¿Qué fue lo más importante que se corrigió?** [PENDIENTE: redactar con tus palabras; sugerencia basada en lo hecho: el límite de intentos de login, porque era la brecha explotable más directa].

**¿Qué riesgo queda abierto?** Falta la cabecera CSP, no hay alertas automáticas sobre los logs, y el límite de intentos depende de un solo worker.

**¿Qué haría distinto en un proyecto real?** [PENDIENTE: redactar con tus palabras].

## 11. Evidencia manual pendiente (la haces tú en el navegador)

- [ ] F12 → Application → Cookies: captura de `sessionid` con HttpOnly y Secure, y `csrftoken` con Secure.
- [ ] Consola: `document.cookie` no muestra `sessionid`.
- [ ] CSP: bloqueo visible en consola (solo si se agrega la cabecera).
- [ ] CSRF: abrir `ataque.html` (del laboratorio) con sesión iniciada y mostrar el 403.
- [ ] Login: 6 intentos fallidos en la página y captura del mensaje de 429.
- [ ] (Opcional) HTTPS local con mkcert.
- [ ] Revisar en Neon el rol y la lista de IP/red permitidas.
- [ ] Git: `git checkout -b seguridad`, commits por partes, push.
