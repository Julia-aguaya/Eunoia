## Deploy y mantenimiento de producción

Producción se despliega desde GitHub Actions por SSH a un servidor DigitalOcean. La fuente de verdad es `.github/workflows/deploy.yml` y `deploy-eunoia.sh`; Render no forma parte de esta infraestructura.

### Deploy

El workflow **Deploy Eunoia** usa únicamente los GitHub Secrets `DO_HOST`, `DO_USER` y `DO_SSH_KEY`. En el servidor trabaja en `~/eunoia` y ejecuta `deploy-eunoia.sh`, que activa `.venv`, instala dependencias, aplica migraciones, recolecta estáticos y reinicia el servicio `eunoia`.

El servicio web usa:

- `WorkingDirectory=~/eunoia`;
- entorno productivo en `~/eunoia/.env`;
- Python en `~/eunoia/.venv/bin/python`;
- Gunicorn de `~/eunoia/.venv/bin/gunicorn`.

Las variables Django y `DATABASE_URL` se configuran exclusivamente en `~/eunoia/.env`; no se almacenan en workflows ni en el repositorio.

### Configurar API de Resend

Después de que este cambio esté desplegado en `main`, crear el GitHub Actions secret de repositorio `RESEND_SMTP_API_KEY` con la API key de Resend. No usar variables de repositorio ni incluir la clave en commits, logs o `.env.example`.

Luego ejecutar manualmente **Configure Resend API** desde GitHub Actions. El workflow reutiliza `RESEND_SMTP_API_KEY` sólo como variable de entorno de la acción SSH y la guarda como `ANYMAIL_RESEND_API_KEY` en `~/eunoia/.env`. Configura el backend `anymail.backends.resend.EmailBackend` y elimina únicamente las claves SMTP obsoletas. Antes del cambio toma un lock, crea un backup local protegido y hace un reemplazo atómico; si falla la actualización, la validación Django o el reinicio, restaura ese backup. La validación previa comprueba presencia de key, construcción de settings, import del backend Anymail y `manage.py check`; no hace llamadas HTTPS porque una key con sólo Sending access no tiene un endpoint de autenticación sin envío documentado. El smoke test real y controlado se realiza después del deploy. La verificación no muestra destinatario, key, token, contenido o `.env`.

### Primer arranque

1. Configurar los GitHub Secrets `DO_HOST`, `DO_USER` y `DO_SSH_KEY`.
2. Crear `~/eunoia/.env` con las variables Django productivas y `DATABASE_URL`.
3. Ejecutar **Deploy Eunoia** desde GitHub Actions sobre `main`.
4. Ejecutar una vez en el servidor:

```bash
cd "$HOME/eunoia"
set -a
. "$HOME/eunoia/.env"
set +a
./.venv/bin/python manage.py bootstrap_eunoia
```

### Mantenimiento de reservas fijas

El workflow **Maintain Eunoia Fixed Booking Horizon** ejecuta en el mismo entorno que el servicio web:

```bash
cd "$HOME/eunoia"
set -a
. "$HOME/eunoia/.env"
set +a
./.venv/bin/python manage.py maintain_fixed_booking_horizon --days-ahead 42
```

Antes de cargar el entorno verifica, sin leer ni imprimir secretos, que el directorio del proyecto, `.venv/bin/python` y `.env` existan, y que el directorio actual sea exactamente `~/eunoia`.

GitHub Actions interpreta cron en UTC:

- `5 3 * * 6`: sábado 03:05 UTC, sábado 00:05 ART.
- `15 3 * * *`: todos los días 03:15 UTC, 00:15 ART.

Para ejecutarlo manualmente: **Actions → Maintain Eunoia Fixed Booking Horizon → Run workflow**.

El workflow no ejecuta deploy, `pip`, migraciones, collectstatic ni reinicios. Comparte la concurrencia `eunoia-production-maintenance` con deploy, sin cancelar ejecuciones en curso: una ejecución espera a la otra y no se superponen. El exit code remoto se propaga a GitHub Actions; conflictos de capacidad o errores hacen fallar visiblemente el job y el resumen del comando queda disponible en los logs del workflow.

### Variables mínimas

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG=False`
- `DJANGO_USE_SQLITE=False`
- `DATABASE_URL`
- `DJANGO_DB_CHARSET=utf8mb4`
- `DJANGO_DB_SQL_MODE=STRICT_TRANS_TABLES`
- `DJANGO_DB_CONNECT_TIMEOUT=5`
- `DJANGO_DB_CONN_MAX_AGE=60`
- `DJANGO_DB_CONN_HEALTH_CHECKS=True`
- `DJANGO_SECURE_SSL_REDIRECT=True`
- `EUNOIA_DEFAULT_TEMPORARY_PASSWORD`
- `EUNOIA_ADMIN_EMAIL`
- `EUNOIA_ADMIN_PASSWORD`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
