# Eunoia - Django MVP base

Base inicial de backend/admin para gestionar turnos de pilates con foco en dominio y persistencia.

## Entrega final y deploy manual

Para handoff final usa estas guias primero:

- `docs/ENTREGA_FINAL.md`
- `docs/DEPLOY_MANUAL.md`
- `docs/DEMO_LOCAL.md`

El resto del `README.md` mantiene contexto e historial de etapas. Para una entrega ejecutable, la ruta corta y actualizada es la de esos dos documentos.

## Demo local operativa

Si queres dejar el proyecto listo para mostrar sin mezclar bootstrap productivo con datos ficticios, usa el comando dedicado de demo:

```bash
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py seed_demo_eunoia
.venv\Scripts\python.exe manage.py check_eunoia_readiness --strict
.venv\Scripts\python.exe manage.py smoke_test_eunoia_demo
.venv\Scripts\python.exe manage.py runserver
```

Credenciales y flujo exacto: `docs/DEMO_LOCAL.md`.

## Entrega minima operativa

Este bloque deja el proyecto mas cerca de una entrega real y NO solo de demo:

- settings minimos de produccion parametrizados por entorno;
- Postgres como camino recomendado de produccion por `DATABASE_URL` o vars explicitas;
- SQLite reservado para local/demo con opt-in claro por `DJANGO_USE_SQLITE=True`;
- static files listos para `collectstatic` con WhiteNoise;
- deploy basico repetible con `Procfile` y `render.yaml`;
- bootstrap operativo idempotente para admin inicial y helpers opcionales de agenda base;
- runbook corto para setup, carga inicial y smoke test manual.

## Setup local rapido

1. copiar `.env.example` a `.env` si queres personalizar secretos y flags locales;
2. correr migraciones;
3. crear o actualizar el admin inicial;
4. levantar el server.

```bash
copy .env.example .env
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py bootstrap_eunoia --admin-email admin@example.com --admin-password "ChangeThisAdminPassword2026!" --admin-first-name Admin --admin-last-name Eunoia
.venv\Scripts\python.exe manage.py runserver
```

Variables relevantes:

- `DJANGO_SECRET_KEY`: secreto real para deploy;
- `DJANGO_DEBUG`: `True` en local, `False` en deploy;
- `DJANGO_ALLOWED_HOSTS`: hosts permitidos separados por coma;
- `DJANGO_USE_SQLITE`: deja SQLite habilitado para local/demo; en produccion debe quedar `False`;
- `DJANGO_DATABASE_PATH`: path del SQLite local/demo, por defecto `db.sqlite3`;
- `DATABASE_URL`: camino principal para Postgres en produccion;
- `DJANGO_DB_ENGINE` + `DJANGO_DB_*`: alternativa explicita si no queres usar `DATABASE_URL`;
- `DJANGO_DB_SSL_MODE`, `DJANGO_DB_CONNECT_TIMEOUT`, `DJANGO_DB_CONN_MAX_AGE`, `DJANGO_DB_CONN_HEALTH_CHECKS`: ajustes utiles para Postgres productivo;
- `DJANGO_CSRF_TRUSTED_ORIGINS`: origins HTTPS/HTTP si el host final lo necesita;
- `EUNOIA_DEFAULT_TEMPORARY_PASSWORD`: password temporal por defecto para altas/importaciones.

## Bootstrap operativo

Comando nuevo para dejar el admin inicial listo sin depender del flujo interactivo de `createsuperuser`:

```bash
.venv\Scripts\python.exe manage.py bootstrap_eunoia --admin-email admin@example.com --admin-password "ChangeThisAdminPassword2026!"
```

Tambien puede leer `EUNOIA_ADMIN_EMAIL` y `EUNOIA_ADMIN_PASSWORD` desde `.env` o variables del deploy.

Si queres dejar una agenda inicial de prueba sin cargar todo a mano:

```bash
.venv\Scripts\python.exe manage.py bootstrap_eunoia --admin-email admin@example.com --admin-password "ChangeThisAdminPassword2026!" --with-demo-slots --generate-next-days 14
```

Que hace:

- asegura las tres `Section` base del sistema;
- crea el admin si no existe;
- normaliza `role=admin`, `is_staff=True`, `is_superuser=True`, `is_active=True`;
- deja el password intacto si la usuaria ya existia, salvo que pases `--reset-password`;
- opcionalmente crea un set chico de `WeeklyClassSlot` base para demo/handoff;
- opcionalmente materializa `ClassSession` proximas reutilizando los slots activos ya cargados.

## Carga inicial recomendada

Flujo pragmatico para una entrega minima:

1. alumnas: importar CSV con `.venv\Scripts\python.exe manage.py import_students_csv ruta\alumnas.csv`;
2. slots semanales: cargarlos desde Django admin o sembrarlos con `bootstrap_eunoia --with-demo-slots` si queres una base inicial rapida;
3. sesiones concretas: materializarlas con `.venv\Scripts\python.exe manage.py generate_class_sessions 2026-04-01 2026-04-30` o, para un arranque corto, con `bootstrap_eunoia --generate-next-days 14`;
4. acceso mensual: activarlo desde `/staff/` o Django admin segun el caso.

## Handoff operativo rapido

Orden recomendado para primer arranque real:

1. `copy .env.example .env` y completar al menos `DJANGO_SECRET_KEY`, `EUNOIA_ADMIN_EMAIL`, `EUNOIA_ADMIN_PASSWORD`;
2. `.venv\Scripts\python.exe manage.py migrate`;
3. `.venv\Scripts\python.exe manage.py bootstrap_eunoia --with-demo-slots --generate-next-days 14` si queres una base de prueba, o sin flags si vas a cargar agenda real;
4. importar alumnas por CSV o alta manual desde admin;
5. revisar/corregir `WeeklyClassSlot` desde admin;
6. generar sesiones del rango operativo real;
7. activar acceso mensual de al menos una alumna;
8. ejecutar el smoke test manual.

## Deploy basico

Queda una ruta clara para Render con PostgreSQL gestionado:

- `render.yaml` aprovisiona `eunoia-db`, expone `DATABASE_URL` al servicio web y fuerza `DJANGO_USE_SQLITE=False`;
- `Procfile` mantiene una entrada portable compatible con plataformas estilo Heroku/Railway cuando ya existe `DATABASE_URL`;
- cuando `RENDER_EXTERNAL_HOSTNAME` existe, settings lo agrega automaticamente a `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS`.

Estrategia final de base de datos:

- Postgres es el camino serio de produccion y el default esperado en cualquier deploy real;
- SQLite queda solo para desarrollo local, handoff rapido y demo controlada;
- si `DJANGO_DEBUG=False` y no configuraste Postgres, settings ahora falla temprano salvo que hagas opt-in explicito de SQLite con `DJANGO_USE_SQLITE=True`;
- el deploy ya no depende de disco persistente para la base principal.

Pasos de despliegue recomendados:

1. crear el servicio en Render usando `render.yaml`;
2. definir `EUNOIA_DEFAULT_TEMPORARY_PASSWORD`, `EUNOIA_ADMIN_EMAIL` y `EUNOIA_ADMIN_PASSWORD`;
3. verificar que `DATABASE_URL` quede conectado al recurso `eunoia-db` y que `DJANGO_USE_SQLITE=False`;
4. abrir shell o job y correr `python manage.py bootstrap_eunoia` una vez;
5. validar login admin, alta/importacion de alumnas y generacion de sesiones.

## Smoke test manual de entrega

1. entrar a `/login/` con admin bootstrap;
2. abrir `/staff/` y validar listado de alumnas;
3. importar una alumna o crearla desde admin;
4. cargar al menos un `WeeklyClassSlot` y generar sesiones;
5. activar acceso mensual de una alumna;
6. entrar como alumna, reservar una clase y verificar `Mis turnos`.

## Limitaciones MVP conscientes

- SQLite sirve para local/demo, pero no es la opcion correcta para operacion sostenida ni para el deploy base del proyecto;
- no hay integraciones externas de notificaciones, pagos ni mensajeria;
- la carga inicial de slots sigue siendo operativa/manual salvo el helper de demo del bootstrap;
- el deploy queda repetible sin credenciales de terceros, pero el bootstrap del admin sigue siendo un paso explicito post-migrate.

## Que se creo

- Proyecto Django `config` con SQLite para arrancar rapido y mantener la base tecnica simple.
- App `scheduling` para concentrar el dominio del negocio.
- Usuario custom autenticado por email, con bandera `must_change_password` para forzar cambio de contrasena temporal.
- Modelos iniciales para actividades, horarios semanales, sesiones concretas, reservas, recuperaciones, cierres por feriado, estado mensual de acceso y auditoria.
- Registro razonable de todo el dominio en Django admin para operar el MVP sin frontend.
- Migraciones iniciales para dejar la estructura lista desde base de datos.

## Decisiones de esta fase

- Se usa `Section` para representar cada actividad configurable (`reformer_arriba`, `reformer_abajo`, `cadillac`) con cupo por defecto editable.
- Se separa `WeeklyClassSlot` de `ClassSession` para distinguir horario fijo semanal de ocurrencia concreta por fecha.
- `MonthlyAccessStatus` controla si la alumna puede reservar sin bloquearle el login.
- `RecoveryCredit` queda atado a una actividad para respetar la regla de uso dentro de la misma seccion.
- `AuditLog` deja una base simple para historial y operaciones manuales futuras.
- ETAPA 1 agrega helpers operativos para activar acceso mensual por pago, suspenderlo manualmente y calcular vencimiento de recuperaciones a 3 meses.
- ETAPA 1 incorpora un comando para materializar `ClassSession` desde `WeeklyClassSlot` en un rango de fechas sin duplicar sesiones ya existentes.
- ETAPA 2 agrega una via unica para crear reservas reales con validaciones de dominio y soporte de historial sin romper re-reservas legitimas.
- ETAPA 3 agrega cancelacion real por la alumna con corte de 2 horas, generacion automatica de recuperaciones validas y uso controlado de recuperaciones dentro de la misma seccion.
- ETAPA 4 agrega cierre operativo de feriados de dia completo, marcado masivo de sesiones como `holiday_closed` y recuperaciones idempotentes para reservas afectadas.
- ETAPA 5A agrega onboarding manual de alumnas desde admin con contrasena temporal operativa, reseteo simple y soporte provisional sin Excel.
- ETAPA 5B agrega importacion inicial de alumnas desde CSV reutilizando la misma logica de onboarding y dejando un camino simple compatible con exportaciones de Excel.
- ETAPA 7 agrega la primera UI web real para alumnas usando templates Django: home util, agenda por actividad y vista de mis turnos con estado operativo visible.
- ETAPA 8 agrega reserva web real desde la agenda reutilizando la misma logica central de `Booking.objects.create_booking(...)`.
- ETAPA 9 agrega cancelacion web desde `Mis turnos` reutilizando `Booking.cancel_by_student(...)` y reflejando recuperaciones en el portal.
- ETAPA 10 agrega uso web de recuperaciones con una vista guiada para elegir clases compatibles de la misma `Section`, siempre reutilizando `Booking.objects.create_booking(..., used_recovery_credit=...)`.
- ETAPA 11 agrega un portal admin inicial protegido para staff con listado web de alumnas, buscador y activacion/suspension operativa del mes actual.
- ETAPA 12 agrega la vista detalle de alumna dentro de `/staff/` para concentrar contexto operativo sin depender tanto de Django admin.
- ETAPA 13 agrega acciones manuales chicas sobre recuperaciones dentro de la ficha de alumna en `/staff/`, con otorgamiento simple y vencimiento manual seguro.
- ETAPA 14 agrega auditado real en `AuditLog` para acciones manuales criticas del staff sobre acceso mensual y recuperaciones, con resumen chico en la ficha de alumna.
- ETAPA 15 agrega una agenda staff simple en `/staff/clases/` para ver clases proximas y aplicar cierres por feriado desde web reutilizando `HolidayClosure.apply(...)`.
- ETAPA 16 agrega el detalle staff de `ClassSession` en `/staff/clases/<id>/`, enlazado desde la agenda para ver ocupacion, alumnas anotadas, reservas con recuperacion y contexto operativo rapido sin salir del portal.
- ETAPA 17 agrega una capa de pulido de producto sobre ambos portales: mejores copies, estados mas legibles, vacios mas utiles y una navegacion mas consistente para demo y validacion.

## Probar ETAPA 17

Esta etapa no agrega features grandes nuevas. Lo que hace es dejar la experiencia mas clara para demo, validacion y operacion cotidiana:

- mejora textos visibles en portal alumna y staff para que hablen mas en lenguaje operativo y menos en lenguaje tecnico;
- refuerza estados importantes como impaga, sin cupo, ultimo lugar, recuperacion disponible o sesion cerrada;
- ordena mejor vacios y CTAs chicos para no dejar pantallas muertas;
- mantiene el enfoque server-rendered, sobrio y pragmatico, reutilizando patrones ya existentes.

Flujo de demo sugerido:

1. entrar con una alumna y abrir `http://127.0.0.1:8000/`;
2. mostrar el estado operativo del mes, despues `Agenda` y despues `Mis turnos`;
3. si hay recuperaciones, entrar al flujo `Elegir clase` para mostrar la guia de uso;
4. entrar con staff a `http://127.0.0.1:8000/staff/`;
5. mostrar listado de alumnas, ficha operativa, agenda staff y detalle de una sesion con o sin cupo.

Comandos para validar esta etapa:

```bash
.venv\Scripts\python.exe manage.py test scheduling
.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.venv\Scripts\python.exe manage.py check
```

## Como levantarlo localmente

```bash
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py bootstrap_eunoia --admin-email admin@example.com --admin-password "ChangeThisAdminPassword2026!"
.venv\Scripts\python.exe manage.py runserver
```

## Probar ETAPA 16

Desde `http://127.0.0.1:8000/staff/clases/` ahora el staff tambien puede:

- entrar desde la agenda al detalle de una `ClassSession` puntual;
- ver fecha, horario, seccion, estado, cupo y ocupacion actual en una sola pantalla;
- revisar alumnas anotadas y distinguir cuales reservas usan recuperacion ya existente;
- mirar reservas no activas recientes y notas/cierre asociado sin abrir Django admin.

La vista sigue server-rendered y reutiliza datos del dominio ya existente:

- reservas activas y relevantes: `Booking` filtradas por `session` y `status`;
- recuperaciones usadas en una reserva: `Booking.used_recovery_credit`;
- recuperaciones generadas por feriado: `RecoveryCredit` trazadas por `origin_session`.

Flujo manual sugerido:

1. entrar con una usuaria `is_staff=True`;
2. abrir `http://127.0.0.1:8000/staff/clases/`;
3. elegir fecha base y, si hace falta, una seccion;
4. abrir `Ver detalle` sobre una clase puntual;
5. validar ocupacion, alumnas anotadas, recuperaciones usadas y enlace simple de vuelta a la agenda.

Comandos para probar esta etapa:

```bash
.venv\Scripts\python.exe manage.py test scheduling
.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.venv\Scripts\python.exe manage.py check
```

## Probar ETAPA 15

Desde `http://127.0.0.1:8000/staff/clases/` ahora el staff puede:

- ver una ventana simple de clases proximas agrupadas por dia;
- filtrar por seccion y fecha base cercana sin salir del portal;
- marcar un dia completo como feriado/cierre desde una forma POST chica;
- ver el impacto del cierre en la misma pantalla: sesiones cerradas, reservas afectadas y recuperaciones generadas;
- dejar auditada la accion sobre `HolidayClosure` dentro de `AuditLog`.

La operacion sigue reutilizando el dominio existente:

- cierre real del dia: `HolidayClosure.apply(actor=...)`;
- recuperaciones por feriado: `RecoveryCredit.objects.grant_holiday_closure_credit(...)` dentro del propio `apply(...)`;
- auditoria del portal staff: `scheduling.audit.log_staff_holiday_closure_applied(...)`.

Flujo manual sugerido:

1. entrar con una usuaria `is_staff=True`;
2. abrir `http://127.0.0.1:8000/staff/clases/`;
3. elegir una fecha base y, si hace falta, una seccion;
4. cargar `Dia a cerrar`, `Motivo visible` y opcionalmente notas;
5. enviar `Aplicar cierre del dia` y verificar el bloque `Impacto del dia elegido`.

Comandos para probar esta etapa:

```bash
.venv\Scripts\python.exe manage.py test scheduling
.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.venv\Scripts\python.exe manage.py check
```

## Probar ETAPA 14

Desde la ficha de alumna en `/staff/` ahora se puede:

- otorgar una recuperacion manual simple sin salir del portal staff;
- ver mas claro el estado, origen y notas de cada recuperacion;
- marcar manualmente como vencida una recuperacion que todavia estaba disponible;
- dejar auditadas en `AuditLog` las acciones manuales criticas del staff sobre acceso mensual y recuperaciones.

La operacion sigue reutilizando el dominio existente:

- alta manual: `RecoveryCredit.objects.grant_manual_credit(...)`;
- vencimiento normal por fecha: `RecoveryCredit.expire_if_needed(...)`;
- vencimiento manual seguro desde staff: `RecoveryCredit.expire_manually(...)`;
- auditado encapsulado: `scheduling.audit.*` crea entradas simples en `AuditLog` con actor, accion, entidad y metadata minima.

Eventos auditados en esta etapa:

- activar acceso mensual desde `/staff/`;
- suspender acceso mensual desde `/staff/`;
- otorgar recuperacion manual desde la ficha de alumna;
- marcar recuperacion como vencida manualmente desde la ficha de alumna.

Ademas, la ficha de alumna muestra un bloque chico de `Auditoria reciente` para revisar las ultimas acciones sin abrir Django admin.

Comandos para probar esta etapa:

```bash
.venv\Scripts\python.exe manage.py test scheduling
.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.venv\Scripts\python.exe manage.py check
```

## Operacion admin en ETAPA 1

- `MonthlyAccessStatus` ahora tiene acciones de admin para activar acceso por pago y suspender acceso operativo sin tocar datos manualmente campo por campo.
- `RecoveryCredit` expone accion para marcar como vencidas las recuperaciones disponibles cuyo vencimiento ya paso.
- `WeeklyClassSlot`, `ClassSession`, `Booking`, `RecoveryCredit`, `MonthlyAccessStatus` y `AuditLog` suman mas filtros, busquedas y relaciones precargadas para operar mas rapido desde Django admin.

## Reservas reales en ETAPA 2

La reserva nueva debe pasar por `Booking.objects.create_booking(...)`. Esa via centraliza las validaciones de dominio y es la misma que usa Django admin al crear una reserva nueva.

Reglas implementadas al reservar:

- la alumna debe tener `MonthlyAccessStatus` activo y con `booking_enabled=True` para el mes de la sesion;
- la alumna solo puede reservar dentro de su `primary_section`;
- no se puede reservar una `ClassSession` con estado `cancelled` ni `holiday_closed`;
- no se puede superar la capacidad configurada de la sesion;
- no se permite una reserva activa duplicada en la misma sesion.

Notas de modelado:

- `User.primary_section` define la actividad principal de la alumna para validar pertenencia de seccion.
- `Booking` mantiene historial permitiendo multiples registros para la misma alumna y sesion, pero solo uno puede quedar activo (`status=booked`) al mismo tiempo.
- Las reservas canceladas siguen existiendo como historial y no bloquean una nueva reserva activa posterior.

Cobertura de tests agregada:

- acceso mensual operativo requerido;
- misma seccion que la alumna;
- sesion cerrada no reservable;
- control de capacidad;
- duplicado activo en la misma sesion;
- re-reserva valida despues de una cancelacion historica;
- formulario de admin usando la misma logica de reserva.

## Generar sesiones desde horarios semanales

Usar el comando de management para crear sesiones concretas desde los horarios semanales activos:

```bash
.venv\Scripts\python.exe manage.py generate_class_sessions 2026-04-01 2026-04-30
```

Opciones utiles:

```bash
.venv\Scripts\python.exe manage.py generate_class_sessions 2026-04-01 2026-04-30 --section cadillac
.venv\Scripts\python.exe manage.py generate_class_sessions 2026-04-01 2026-04-30 --dry-run
```

Reglas del comando:

- toma solo `WeeklyClassSlot` activos y vigentes para cada fecha;
- usa la capacidad propia del slot o, si falta, la capacidad por defecto de `Section`;
- evita duplicados comparando `section + date + start_time`;
- si la fecha coincide con `HolidayClosure`, genera la sesion como `holiday_closed` y la vincula al cierre.

## Cancelaciones y recuperaciones en ETAPA 3

La reserva sigue entrando por `Booking.objects.create_booking(...)`, pero ahora esa via tambien soporta uso de recuperaciones con reglas de dominio reales.

Reglas implementadas en esta etapa:

- la alumna puede cancelar su reserva activa solo si faltan mas de 2 horas para el inicio de la clase;
- una cancelacion valida cambia la reserva a `cancelled`, libera el cupo operativo y genera automaticamente un `RecoveryCredit` disponible;
- si faltan 2 horas o menos, la auto-cancelacion se rechaza;
- una recuperacion usada al reservar cambia automaticamente el `Booking.source` a `makeup` y marca el credito como `used`;
- la recuperacion solo puede usarse en otra `ClassSession` de la misma `Section` y no permite volver a reservar la sesion que origino ese credito;
- el admin puede otorgar una recuperacion manual desde Django admin y el vencimiento sigue siendo a 3 meses.

Ruta de uso:

- auto-cancelacion de alumna: `Booking.cancel_by_student(...)`;
- reserva usando recuperacion: `Booking.objects.create_booking(..., used_recovery_credit=credit)`;
- excepcion manual operativa: alta de `RecoveryCredit` desde Django admin.

Cobertura de tests agregada:

- cancelacion valida generando recuperacion;
- rechazo de cancelacion fuera de ventana;
- uso de recuperacion en la misma actividad;
- rechazo de recuperacion en otra actividad/seccion;
- rechazo de recuperacion para re-reservar la sesion original;
- grant manual de recuperacion desde admin.

## Feriados y recuperaciones en ETAPA 4

La via central para procesar un feriado completo es `HolidayClosure.apply(...)`. Esa operacion toma un dia dado, marca todas las `ClassSession` de esa fecha como `holiday_closed` y genera `RecoveryCredit` por cada reserva activa afectada.

Reglas implementadas en esta etapa:

- el admin puede dar de alta un `HolidayClosure` y al guardar se aplica el cierre operativo sobre ese dia;
- todas las `ClassSession` existentes en esa fecha quedan no reservables con estado `holiday_closed` y vinculadas al feriado;
- cada reserva activa de ese dia genera una recuperacion `holiday_closure` para la misma `Section` de la clase perdida;
- reprocesar el mismo feriado no duplica recuperaciones: se reutiliza la combinacion `student + origin_session + source=holiday_closure`;
- si primero se crea el feriado y despues aparecen sesiones de ese dia, se puede reprocesar desde admin o por comando sin romper consistencia.

Vias operativas:

- desde admin: alta/edicion de `HolidayClosure` o accion masiva `Aplicar cierre de feriado y procesar recuperaciones`;
- por comando: `.venv\Scripts\python.exe manage.py apply_holiday_closure 2026-05-01 --reason "Dia del trabajador"`

Notas de modelado:

- no se agregaron notificaciones ni automatizaciones externas porque quedan fuera del alcance pedido;
- la recuperacion por feriado queda asociada a la `Section` y a la `origin_session` para mantener trazabilidad e idempotencia;
- `generate_class_sessions` sigue respetando `HolidayClosure` al crear sesiones futuras, y `HolidayClosure.apply(...)` cubre las sesiones ya existentes.

Cobertura de tests agregada:

- cierre de dia completo sobre todas las sesiones de la fecha;
- sesiones marcadas como no reservables por `holiday_closed`;
- recuperaciones generadas para reservas activas afectadas y dentro de la misma seccion;
- no duplicacion al reprocesar el mismo feriado;
- comando operativo para crear/aplicar el cierre por fecha.

## Onboarding manual provisional en ETAPA 5A

Hasta tener importacion Excel real, el alta operativa de alumnas se hace desde Django admin sobre `Users`.

Flujo recomendado:

- crear la alumna desde `Users` con email, nombre, apellido, `primary_section`, telefono y notas operativas;
- dejar `must_change_password` activo para que el backend siga marcando que debe cambiar su contrasena en el primer ingreso;
- si no cargas `temporary_password`, admin usa `settings.EUNOIA_DEFAULT_TEMPORARY_PASSWORD` como contrasena temporal inicial;
- si despues necesitas resetear una o varias contrasenas temporales, podes hacerlo desde la accion masiva del admin o por management command.

Configuracion temporal por defecto:

```python
EUNOIA_DEFAULT_TEMPORARY_PASSWORD = os.getenv('EUNOIA_DEFAULT_TEMPORARY_PASSWORD', 'EunoiaTemp2026!')
```

Notas de modelado para esta etapa:

- `User.set_initial_password(...)` y `User.set_temporary_password(...)` concentran el comportamiento de contrasena inicial y la marca `must_change_password`;
- si una usuaria vuelve a quedar con contrasena temporal, se refresca `temporary_password_set_at`;
- si se asigna una contrasena definitiva con `require_password_change=False`, el backend limpia el estado temporal para no dejar senales inconsistentes.

Comando operativo agregado:

```bash
.venv\Scripts\python.exe manage.py set_temporary_password alumna1@example.com alumna2@example.com
.venv\Scripts\python.exe manage.py set_temporary_password --all-students
.venv\Scripts\python.exe manage.py set_temporary_password --all-students --password "TempManual2026!"
```

Reglas cubiertas en esta etapa:

- alta manual simple de alumnas desde admin sin depender de Excel;
- uso de contrasena temporal configurada por defecto o contrasena inicial cargada manualmente;
- reseteo simple de contrasena temporal para una usuaria desde admin y para varias por comando;
- preservacion del flag `must_change_password` para el futuro flujo real de login/cambio de contrasena;
- tests de onboarding manual, formularios admin y command helper.

## Importacion inicial desde CSV en ETAPA 5B

Para esta etapa se usa CSV en vez de parser `.xlsx` directo. Y ACA ESTA LA IDEA IMPORTANTE: Excel puede exportar el archivo a CSV sin problema, asi que resolvemos la necesidad operativa real ahora sin meter complejidad binaria innecesaria en el backend.

Via operativa agregada:

```bash
.venv\Scripts\python.exe manage.py import_students_csv ruta\alumnas.csv
```

Que hace el comando:

- crea usuarias nuevas por `email`;
- actualiza usuarias existentes por `email` de forma segura;
- si la fila es nueva y `temporary_password` viene vacia, usa `settings.EUNOIA_DEFAULT_TEMPORARY_PASSWORD`;
- si la fila ya existe y `temporary_password` viene vacia, NO toca la contrasena actual ni el estado existente de `must_change_password`;
- si `temporary_password` viene informada, reutiliza `User.set_initial_password(...)` para mantener consistente la logica de password temporal y `must_change_password`.

Formato esperado del archivo:

```csv
email,first_name,last_name,primary_section,role,is_active,must_change_password,temporary_password,phone,notes
ada@example.com,Ada,Lovelace,cadillac,student,true,true,,1234,Alta inicial desde Excel exportado a CSV
grace@example.com,Grace,Hopper,reformer_arriba,student,true,true,TempGrace2026!,555-0101,Actualizar datos y resetear password
```

Columnas:

- obligatorias: `email`, `first_name`, `last_name`, `primary_section`;
- opcionales: `role`, `is_active`, `must_change_password`, `temporary_password`, `phone`, `notes`.

Validaciones basicas implementadas:

- `email` debe tener formato valido;
- `primary_section` debe ser uno de `reformer_arriba`, `reformer_abajo`, `cadillac`;
- `role` debe ser `student` o `admin`;
- `is_active` y `must_change_password` aceptan `true/false`, `yes/no`, `si/no`, `1/0` o vacio;
- faltantes en columnas obligatorias, columnas inesperadas y emails duplicados dentro del mismo archivo frenan la importacion completa.

Notas de modelado para esta etapa:

- CSV es un paso previo pragmatico porque Excel lo exporta facil y el backend mantiene una entrada tabular simple;
- la importacion valida todo primero y recien despues guarda, para evitar cargas parciales si el archivo viene roto;
- `role=admin` habilita `is_staff=True`; `role=student` vuelve `is_staff=False` salvo que la usuaria ya sea `is_superuser`;
- en actualizaciones existentes se prioriza seguridad operativa: sin `temporary_password` no se resetean credenciales por accidente.

Cobertura de tests agregada:

- creacion de alumna nueva con password temporal por defecto;
- actualizacion de usuaria existente sin resetear password cuando la columna viene vacia;
- rechazo de email, seccion, rol y booleanos invalidos;
- management command cableado al helper real.

## Login web minimo en ETAPA 6

Esta etapa agrega un flujo web basico con vistas y templates Django simples, sin API ni frontend separado.

Rutas nuevas:

- `/login/` para ingresar con `email + password`;
- `/logout/` para cerrar sesion;
- `/change-password-required/` para forzar cambio de contrasena cuando `must_change_password=True`;
- `/` como dashboard protegido minimo para validar el flujo.

Comportamiento implementado:

- el backend autentica usando el `User` custom por email;
- si la usuaria entra con contrasena temporal y `must_change_password=True`, queda autenticada pero se la redirige obligatoriamente a `/change-password-required/`;
- mientras siga con `must_change_password=True`, un middleware bloquea acceso al dashboard y la devuelve al cambio obligatorio;
- al guardar una contrasena definitiva, se actualiza `password`, se limpia `temporary_password_set_at`, se deja `must_change_password=False` y la sesion sigue activa.

Como probarlo manualmente:

```bash
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py runserver
```

Despues:

1. crear una usuaria desde admin o por shell con email y contrasena temporal;
2. entrar en `http://127.0.0.1:8000/login/`;
3. verificar redireccion obligatoria si `must_change_password=True`;
4. cambiar la contrasena y confirmar acceso normal al dashboard.

Para validar la etapa por tests y chequeos:

```bash
.venv\Scripts\python.exe manage.py test scheduling
.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.venv\Scripts\python.exe manage.py check
```

## Alcance intencionalmente fuera de esta fase

- Importacion de alumnas por Excel.
- Reglas automaticas de negocio para otorgar recuperaciones, bloquear reservas o generar sesiones.
- No-show automatico.
- Movimientos manuales completos.
- Frontend para alumnas.
- API publica.

## Portal web de alumnas en ETAPA 7

Esta etapa reemplaza el dashboard placeholder por una UI web simple, sobria y usable hecha con templates Django. NO hay React en esta fase: la idea es validar experiencia real de alumna reutilizando el dominio ya existente.

Rutas nuevas o mejoradas:

- `/` ahora funciona como home real de la alumna;
- `/agenda/` muestra solo sesiones futuras de su `primary_section`;
- `/mis-turnos/` muestra reservas activas y recuperaciones visibles;
- la navegacion entre pantallas queda disponible dentro del portal protegido.

Que cubre esta primera UI:

- estado operativo del mes bien visible para dejar claro si la alumna esta activa, impaga, suspendida o sin acceso cargado;
- agenda futura solo de la actividad principal de la alumna;
- proximas reservas activas, incluyendo si una fue hecha usando recuperacion;
- recuperaciones vigentes y vencidas con fecha de vencimiento visible;
- placeholders de accion claros cuando reservar desde UI todavia no esta enchufado.

Decision tecnica importante:

- la logica de consultas queda en vistas/helpers simples dentro de `scheduling/views.py` para no sobreingenierizar una primera entrega server-rendered;
- la UI bloquea acciones a nivel presentacion cuando `MonthlyAccessStatus` no permite operar, pero sigue mostrando informacion para contexto;
- la agenda web no mezcla actividades: siempre filtra por `User.primary_section`.

Como probar esta UI localmente:

```bash
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py runserver
```

Luego:

1. entrar con una alumna que ya tenga `primary_section` y estado mensual cargado;
2. abrir `http://127.0.0.1:8000/` para ver la home;
3. navegar a `http://127.0.0.1:8000/agenda/` y `http://127.0.0.1:8000/mis-turnos/`;
4. probar tambien un caso con `MonthlyAccessStatus` pendiente o suspendido para ver el bloqueo visual de acciones.

Validacion pedida para esta etapa:

```bash
.venv\Scripts\python.exe manage.py test scheduling
.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.venv\Scripts\python.exe manage.py check
```

## Reserva web real en ETAPA 8

Esta etapa conecta por fin la agenda web con la reserva real, SIN mover reglas de negocio a la vista. La accion del portal entra por `Booking.objects.create_booking(...)`, igual que admin.

Que cubre esta etapa:

- la alumna autenticada puede reservar una `ClassSession` futura visible en su agenda;
- la vista web no duplica validaciones: usa la misma logica central del dominio y solo traduce el resultado a mensajes claros para la UI;
- si no hay acceso operativo para el mes de la clase, la accion queda bloqueada o deshabilitada con mensaje explicito;
- home y `mis-turnos` reflejan la nueva reserva al volver a cargar el portal;
- errores de negocio visibles en la UI: acceso operativo, actividad incorrecta, sesion cerrada, cupo agotado y duplicado activo.

Decision tecnica importante:

- la agenda arma un estado de accion por sesion para mostrar botones habilitados o bloqueados segun el mes real de la clase, no solo el mes actual del dashboard;
- el POST de reserva queda en una vista minima que busca la sesion, llama a `create_booking(...)` y devuelve feedback con `django.contrib.messages`;
- los textos de error se adaptan a lenguaje de portal, pero la fuente de verdad sigue siendo la validacion del modelo.

Como probarlo manualmente:

```bash
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py runserver
```

Luego:

1. entrar con una alumna que tenga `primary_section` y `MonthlyAccessStatus` activo para el mes de la clase;
2. abrir `http://127.0.0.1:8000/agenda/`;
3. usar el boton `Reservar` sobre una clase futura;
4. verificar el mensaje de exito y que la clase aparezca tambien en `http://127.0.0.1:8000/mis-turnos/` y en la home.

Para validar la etapa por tests y chequeos:

```bash
.venv\Scripts\python.exe manage.py test scheduling
.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.venv\Scripts\python.exe manage.py check
```

## Cancelacion web en ETAPA 9

Esta etapa conecta `Mis turnos` con la cancelacion real de reservas, otra vez SIN mover reglas de negocio a la vista. El POST web entra por `Booking.cancel_by_student(...)`, igual que deberia hacerlo cualquier otra interfaz que quiera respetar la logica central.

Que cubre esta etapa:

- la alumna autenticada puede cancelar una reserva activa futura desde `http://127.0.0.1:8000/mis-turnos/`;
- la regla de corte de 2 horas y la generacion de `RecoveryCredit` siguen viviendo en dominio;
- la UI muestra mensajes claros para exito, ventana vencida, estado invalido y otros errores razonables del negocio;
- despues de cancelar, la reserva desaparece de `Mis turnos` y la home refleja la nueva disponibilidad de recuperaciones.

Decision tecnica importante:

- la vista web de cancelacion es minima: busca la reserva de la alumna, llama a `cancel_by_student(...)` y traduce `ValidationError` a mensajes entendibles;
- `Mis turnos` muestra una accion de cancelacion simple por reserva y usa un estado visual de `Ventana cerrada` cuando ya no llega a tiempo para auto-cancelar;
- ese estado visual es solo UX, NO reemplaza la validacion del dominio.

Como probarlo manualmente:

```bash
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py runserver
```

Luego:

1. entrar con una alumna que tenga una reserva futura activa;
2. abrir `http://127.0.0.1:8000/mis-turnos/`;
3. usar el boton `Cancelar turno` en una reserva con mas de 2 horas de anticipacion;
4. verificar el flash de exito, que la reserva desaparezca y que en la home suba el contador de recuperaciones vigentes.

Para validar la etapa por tests y chequeos:

```bash
.venv\Scripts\python.exe manage.py test scheduling
.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.venv\Scripts\python.exe manage.py check
```

## Uso web de recuperaciones en ETAPA 10

Esta etapa suma el flujo que faltaba: usar una recuperacion disponible desde el portal sin duplicar reglas en la vista. La reserva final sigue entrando por `Booking.objects.create_booking(...)`, ahora pasando el `RecoveryCredit` elegido.

Que cubre esta etapa:

- la alumna puede entrar desde `Mis turnos` a una vista simple de `usar recuperacion` y reservar otra `ClassSession` futura de la misma `Section`;
- el portal expone recuperaciones disponibles con CTA clara y marca en agenda/dashboard cuando una clase es compatible con recuperacion;
- la pantalla guiada prioriza sesiones futuras de la misma actividad y explica por que una opcion no aplica cuando el dominio la rechaza;
- dashboard y `Mis turnos` reflejan tanto recuperaciones vigentes como reservas futuras ya tomadas por recuperacion;
- errores como recuperacion vencida, recuperacion inexistente o sesion invalida se traducen a feedback entendible para la alumna.

Decision tecnica importante:

- la vista nueva no reimplementa reglas: para decidir si una sesion se puede mostrar como compatible arma un `Booking(...)` temporal y deja que `full_clean()` use la validacion real del dominio;
- el POST de reserva existente se reaprovecha y ahora acepta opcionalmente `used_recovery_credit_id`, con lookup seguro limitado a la alumna autenticada;
- la agenda general solo da contexto visual y deriva al flujo especifico de recuperacion cuando corresponde, para no mezclar decisiones operativas en una sola tarjeta.

Como probarlo manualmente:

```bash
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py runserver
```

Luego:

1. entrar con una alumna que tenga al menos una `RecoveryCredit` disponible en su actividad principal;
2. abrir `http://127.0.0.1:8000/mis-turnos/` y usar `Elegir clase` sobre la recuperacion;
3. verificar que `http://127.0.0.1:8000/recuperaciones/<id>/usar/` muestre solo sesiones futuras de esa actividad y marque incompatibilidades con mensaje claro;
4. reservar una clase compatible y confirmar que aparece como `Recuperacion aplicada` en `Mis turnos` y que el dashboard actualiza el conteo de recuperaciones usadas.

Para validar la etapa por tests y chequeos:

```bash
.venv\Scripts\python.exe manage.py test scheduling
.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.venv\Scripts\python.exe manage.py check
```

## Portal admin inicial en ETAPA 11

Esta etapa agrega la primera experiencia web propia para operacion interna. NO reemplaza Django admin completo: saca solo el flujo mas repetido de revisar alumnas y tocar su acceso operativo mensual.

Ruta nueva:

- `/staff/` para staff/admin autenticado.

Que cubre esta etapa:

- buscador por nombre, apellido o email sobre alumnas;
- lectura rapida de `primary_section`;
- estado operativo del mes actual visible junto a una etiqueta de pago operativa (`paid`, `unpaid`, `suspended` o sin definir);
- accion simple para activar o suspender acceso operativo del mes actual reutilizando `MonthlyAccessStatus.activate_by_payment(...)` y `MonthlyAccessStatus.suspend_operational_access(...)`;
- proteccion de acceso: anonimos van a login y usuarios autenticados sin `is_staff` reciben 403.

Decision tecnica importante:

- la UI admin queda server-rendered con templates Django, igual que el portal de alumnas, pero con una identidad visual mas sobria y orientada a operacion;
- la vista no duplica reglas del dominio: para cambiar el estado mensual sigue entrando por los metodos existentes del modelo;
- si la alumna todavia no tiene `MonthlyAccessStatus` para el mes actual, la accion web crea el registro minimo y luego aplica la transicion correspondiente.

Como probar este portal admin inicial:

```bash
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py runserver
```

Luego:

1. entrar con una usuaria `is_staff=True`;
2. abrir `http://127.0.0.1:8000/staff/`;
3. buscar una alumna por nombre o email;
4. usar `Activar acceso` o `Suspender acceso` y verificar el cambio visual en el mismo listado.

Para validar esta etapa por tests y chequeos:

```bash
.venv\Scripts\python.exe manage.py test scheduling
.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.venv\Scripts\python.exe manage.py check
```

## Vista detalle de alumna en ETAPA 12

Esta etapa profundiza el portal admin web con una ficha operativa por alumna. La idea es resolver la consulta diaria mas comun desde `/staff/` sin meterse enseguida en Django admin y SIN duplicar reglas del dominio.

Rutas nuevas o mejoradas:

- `/staff/` ahora enlaza cada alumna a su detalle operativo;
- `/staff/alumnas/<id>/` muestra una vista server-rendered con resumen accionable.

Que cubre esta etapa:

- datos basicos de la alumna, incluyendo email, telefono, notas y seccion principal;
- estado mensual actual con la misma accion simple para activar o suspender acceso operativo del mes;
- proximas reservas activas relevantes para operacion;
- recuperaciones separadas entre disponibles y vencidas;
- resumen reciente de movimientos de reservas y mini historial de estados mensuales;
- navegacion minima entre listado y detalle, preservando el filtro cuando venis desde busqueda.

Decision tecnica importante:

- la vista nueva reutiliza consultas y metodos ya existentes (`get_monthly_access_for`, `activate_by_payment`, `suspend_operational_access`) en vez de crear servicios nuevos artificiales;
- el detalle arma un resumen operativo acotado dentro de `scheduling/views.py`, manteniendo el enfoque server-rendered y evitando sobreingenieria;
- el POST de cambio de acceso acepta `next` seguro para volver al listado filtrado o quedarse en el detalle sin perder contexto.

Como probar esta vista localmente:

```bash
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py runserver
```

Luego:

1. entrar con una usuaria `is_staff=True`;
2. abrir `http://127.0.0.1:8000/staff/` y buscar una alumna si queres filtrar;
3. usar `Ver detalle` o tocar el nombre de la alumna;
4. verificar la ficha en `http://127.0.0.1:8000/staff/alumnas/<id>/`, incluyendo reservas futuras, recuperaciones y accion de acceso mensual;
5. usar `Volver al listado` para confirmar que se conserva el contexto basico de navegacion.

Para validar esta etapa por tests y chequeos:

```bash
.venv\Scripts\python.exe manage.py test scheduling
.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.venv\Scripts\python.exe manage.py check
```
