# Evidencias del laboratorio de seguridad

Capturas hechas por el autor en el navegador y en el panel de Neon. Cada una respalda un punto de `INFORME_SEGURIDAD.md`.

| Archivo | Qué muestra | Punto del informe |
|---------|-------------|-------------------|
| `01_cookies.png` | Application → Cookies: `sessionid` HttpOnly + Secure; `csrftoken` Secure; SameSite Lax | Hallazgo 8 |
| `02_document_cookie.png` | `document.cookie` solo devuelve `csrftoken` (no `sessionid`) | Hallazgo 8 |
| `03_csp_bloqueo.png` | La CSP bloquea un manejador en línea inyectado | Hallazgo 6 |
| `04_csrf_403.png` | Con sesión admin y sin token: 403 "CSRF token missing" | Hallazgo 7 |
| `05_login_429.png` | Sexto intento fallido: "Demasiados intentos. Espere 15 minutos…" | Hallazgo 1 |
| `06_error_404_json.png` | Ruta inexistente en el backend: JSON genérico | Hallazgo 2 |
| `07_neon_roles.png` | Neon: un solo rol, `neondb_owner` | Riesgo R6 |
| `08_neon_red.png` | Neon: acceso desde cualquier IP; lista de IP y VPC requieren plan de pago | Riesgo R6 |
