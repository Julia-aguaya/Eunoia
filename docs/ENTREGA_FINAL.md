## Entrega final

Usa esta guia para la entrega. El `README.md` conserva historial de etapas, pero para handoff final este es el camino corto y ejecutable.

### 1. Preparar entorno

```bash
copy .env.example .env
```

Completar como minimo:

- `DJANGO_SECRET_KEY`
- `EUNOIA_ADMIN_EMAIL`
- `EUNOIA_ADMIN_PASSWORD`
- `EUNOIA_DEFAULT_TEMPORARY_PASSWORD`
- `DJANGO_ALLOWED_HOSTS` y `DJANGO_CSRF_TRUSTED_ORIGINS` si cambia el host

### 2. Migrar y bootstrap

```bash
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py bootstrap_eunoia --admin-email admin@example.com --admin-password "ChangeThisAdminPassword2026!"
```

Si queres una base minima de demo para arrancar rapido:

```bash
.venv\Scripts\python.exe manage.py bootstrap_eunoia --admin-email admin@example.com --admin-password "ChangeThisAdminPassword2026!" --with-demo-slots --generate-next-days 14
```

### 3. Importar alumnas

```bash
.venv\Scripts\python.exe manage.py import_students_csv ruta\alumnas.csv
```

CSV esperado:

- obligatorias: `email`, `first_name`, `last_name`, `primary_section`
- opcionales: `role`, `is_active`, `must_change_password`, `temporary_password`, `phone`, `notes`

### 4. Crear agenda operativa

Opciones pragmaticas:

- demo: usar `bootstrap_eunoia --with-demo-slots --generate-next-days 14`
- real: cargar `WeeklyClassSlot` desde `/admin/` y despues generar sesiones

```bash
.venv\Scripts\python.exe manage.py generate_class_sessions 2026-04-01 2026-04-30
```

### 5. Verificar readiness local

```bash
.venv\Scripts\python.exe manage.py check_eunoia_readiness --strict
```

El comando revisa staff/admin, secciones base y agenda minima (`WeeklyClassSlot` o `ClassSession`). Si falla, todavia no esta listo para handoff.

### 6. Checklist corta de entrega

- `migrate` ejecutado sin errores
- `bootstrap_eunoia` ejecutado y login staff disponible en `/login/`
- alumnas importadas o creadas manualmente
- existe al menos un `WeeklyClassSlot` o una `ClassSession` futura
- al menos una alumna con acceso mensual activo para el mes a validar
- login staff validado en `/staff/`
- login alumna validado en `/login/` y cambio de password forzado si corresponde
- reserva validada desde `/agenda/`
- cancelacion validada desde `/mis-turnos/` con mas de 2 horas de anticipacion
- recuperacion validada desde `/recuperaciones/<id>/usar/`

### 7. Smoke test manual sugerido

1. Entrar con staff a `/login/` y abrir `/staff/`.
2. Confirmar que se ve al menos una alumna y una seccion principal coherente.
3. Activar acceso mensual de una alumna si todavia no lo tiene.
4. Entrar con esa alumna a `/login/`.
5. Si tiene password temporal, completar `/change-password-required/`.
6. Abrir `/agenda/`, reservar una clase futura y verificarla en `/mis-turnos/`.
7. Cancelar esa reserva con mas de 2 horas de margen y confirmar que aparece una recuperacion.
8. Usar la recuperacion en otra clase de la misma seccion y validar que vuelva a aparecer en `/mis-turnos/`.
