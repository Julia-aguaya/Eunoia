## Deploy manual

Esta guia usa lo que ya existe en `render.yaml`, `.env.example` y `Procfile`. NO despliega nada por vos: deja el paso a paso para que alguien lo haga manualmente.

### Fuente de verdad del deploy actual

- `render.yaml`: define `buildCommand`, `startCommand`, disco persistente y variables sugeridas
- `Procfile`: deja el start command portable para plataformas estilo Heroku/Railway
- `.env.example`: lista las variables base que hay que completar

### Configuracion recomendada para esta entrega

- base de datos: PostgreSQL gestionado
- variable principal: `DATABASE_URL`
- app server: `gunicorn config.wsgi --log-file -`
- migraciones: se ejecutan en el arranque (`python manage.py migrate && ...`)

### Variables minimas

Definir manualmente:

- `DJANGO_SECRET_KEY`: valor real, no `change-me-before-deploy`
- `DJANGO_DEBUG=False`
- `DJANGO_USE_SQLITE=False`
- `DATABASE_URL=postgresql://...`
- `DJANGO_DB_SSL_MODE=require`
- `DJANGO_DB_CONNECT_TIMEOUT=5`
- `DJANGO_DB_CONN_MAX_AGE=60`
- `DJANGO_DB_CONN_HEALTH_CHECKS=True`
- `DJANGO_SECURE_SSL_REDIRECT=True`
- `EUNOIA_DEFAULT_TEMPORARY_PASSWORD`
- `EUNOIA_ADMIN_EMAIL`
- `EUNOIA_ADMIN_PASSWORD`

Segun host final:

- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`

Nota: si el host expone `RENDER_EXTERNAL_HOSTNAME`, `config/settings.py` lo agrega solo a `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS`.

SQLite queda solo para local/demo. Si alguien realmente quiere deployar con SQLite, ahora tiene que hacerlo de forma explicita con `DJANGO_USE_SQLITE=True` y asumir el costo operativo.

### Paso a paso manual

1. Crear un servicio Python y una base PostgreSQL gestionada.
2. Cargar el repo tal como esta.
3. Configurar el build command de `render.yaml`:

```bash
pip install -r requirements.txt && python manage.py collectstatic --noinput
```

4. Configurar el start command de `render.yaml` o `Procfile`:

```bash
python manage.py migrate && gunicorn config.wsgi --log-file -
```

5. Vincular `DATABASE_URL` a la base PostgreSQL y definir las variables del bloque anterior.
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
- deja Postgres como camino principal de produccion, sin fallback silencioso a SQLite
- no asume slots cargados: si no existen, hay que cargarlos o sembrar demo antes de generar sesiones
- no asume que el arranque crea datos operativos: `migrate` corre solo esquema; el bootstrap sigue siendo paso explicito
