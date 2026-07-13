## Deploy manual

Esta guia usa lo que ya existe en `render.yaml`, `.env.example` y `Procfile`. NO despliega nada por vos: deja el paso a paso para que alguien lo haga manualmente.

### Fuente de verdad del deploy actual

- `render.yaml`: define `buildCommand`, `startCommand` y variables sugeridas para conectar un MySQL externo
- `Procfile`: deja el start command portable para plataformas estilo Heroku/Railway
- `.env.example`: lista las variables base que hay que completar

### Configuracion recomendada para esta entrega

- base de datos: MySQL gestionado
- variable principal: `DATABASE_URL`
- app server: `gunicorn config.wsgi --log-file -`
- migraciones: se ejecutan en el arranque (`python manage.py migrate && ...`)

### Variables minimas

Definir manualmente:

- `DJANGO_SECRET_KEY`: valor real, no `change-me-before-deploy`
- `DJANGO_DEBUG=False`
- `DJANGO_USE_SQLITE=False`
- `DATABASE_URL=mysql://USER:PASSWORD@HOST:3306/DBNAME`
- `DJANGO_DB_CHARSET=utf8mb4`
- `DJANGO_DB_SQL_MODE=STRICT_TRANS_TABLES`
- `DJANGO_DB_SSL_CA` si tu proveedor exige CA explicita
- `DJANGO_DB_SSL_CERT` y `DJANGO_DB_SSL_KEY` si tu proveedor usa mTLS
- `DJANGO_DB_CONNECT_TIMEOUT=5`
- `DJANGO_DB_CONN_MAX_AGE=60`
- `DJANGO_DB_CONN_HEALTH_CHECKS=True`
- `DJANGO_SECURE_SSL_REDIRECT=True`
- `DJANGO_USE_X_FORWARDED_HOST=True`
- `EUNOIA_DEFAULT_TEMPORARY_PASSWORD`
- `EUNOIA_ADMIN_EMAIL`
- `EUNOIA_ADMIN_PASSWORD`

Segun host final:

- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DJANGO_COOKIE_DOMAIN` si queres compartir cookies entre dominio raiz y subdominios (por ejemplo `.pilateseunoia.com`)

Notas:

- si el host expone `RENDER_EXTERNAL_HOSTNAME`, `config/settings.py` lo agrega solo a `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS`
- `DJANGO_USE_X_FORWARDED_HOST=True` deja que Django valide CSRF contra el host publico enviado por el proxy, en lugar del host interno
- si `DJANGO_ALLOWED_HOSTS` incluye un dominio raiz y sus subdominios compatibles, `config/settings.py` ahora puede derivar automaticamente `SESSION_COOKIE_DOMAIN` y `CSRF_COOKIE_DOMAIN`; para casos mas raros conviene fijar `DJANGO_COOKIE_DOMAIN` a mano

SQLite queda solo para local/demo. Si alguien realmente quiere deployar con SQLite, ahora tiene que hacerlo de forma explicita con `DJANGO_USE_SQLITE=True` y asumir el costo operativo.

Importante sobre Render: al momento de esta guia, Render documenta Postgres gestionado pero no un recurso gestionado equivalente para MySQL. Por eso `render.yaml` ya no aprovisiona base propia: deja la app lista y espera que conectes un MySQL externo por `DATABASE_URL`.

### Paso a paso manual

1. Crear un servicio Python en Render y provisionar un MySQL gestionado externo en el proveedor que elijas.
2. Cargar el repo tal como esta.
3. Configurar el build command de `render.yaml`:

```bash
pip install -r requirements.txt && python manage.py collectstatic --noinput
```

4. Configurar el start command de `render.yaml` o `Procfile`:

```bash
python manage.py migrate && gunicorn config.wsgi --log-file -
```

5. Cargar `DATABASE_URL` con la cadena de conexion MySQL y definir las variables del bloque anterior.
6. Hacer el primer arranque de la app.
7. Abrir una shell del servicio y correr una sola vez el bootstrap inicial:

```bash
python manage.py bootstrap_eunoia
```

8. Importar alumnas:

```bash
python manage.py import_students_csv ruta/alumnas.csv
```

9. Cargar slots semanales reales desde admin o sembrar demo minima:

```bash
python manage.py bootstrap_eunoia --with-demo-slots --generate-next-days 14
```

10. Si la agenda es real, generar sesiones del rango operativo:

```bash
python manage.py generate_class_sessions 2026-04-01 2026-04-30
```

11. Verificar readiness minima:

```bash
python manage.py check_eunoia_readiness --strict
```

12. Validar manualmente:

- `/login/` con staff bootstrap
- `/staff/` con listado visible
- login de una alumna
- reserva en `/agenda/`
- cancelacion en `/mis-turnos/`
- recuperacion en `/recuperaciones/<id>/usar/`

### Inconsistencias evitadas en esta guia

- no depende de `createsuperuser` interactivo: usa `bootstrap_eunoia`
- deja MySQL como camino principal de produccion, sin fallback silencioso a SQLite
- no asume slots cargados: si no existen, hay que cargarlos o sembrar demo antes de generar sesiones
- no asume que el arranque crea datos operativos: `migrate` corre solo esquema; el bootstrap sigue siendo paso explicito
