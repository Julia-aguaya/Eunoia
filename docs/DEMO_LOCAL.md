# Demo local operativa

Esta guia deja una base demo completa sin datos sensibles y sin depender de servicios externos. Para este flujo local/demo SQLite sigue siendo suficiente; para deploy productivo la ruta recomendada pasa a ser MySQL.

## Que crea `seed_demo_eunoia`

- secciones base: `reformer_arriba`, `reformer_abajo`, `cadillac`;
- dos usuarias staff (`admin` y `staff`) con password fija de demo;
- seis alumnas demo con estados operativos distintos;
- slots semanales base y sesiones futuras para las proximas 4 semanas;
- estados mensuales representativos: activa, impaga y suspendida;
- reservas demo ya cargadas;
- una recuperacion disponible por cancelacion y otra ya usada en una reserva futura.

## Pasos exactos

1. migrar la base:

```bash
.venv\Scripts\python.exe manage.py migrate
```

2. sembrar la demo local:

```bash
.venv\Scripts\python.exe manage.py seed_demo_eunoia
```

3. validar integridad minima y smoke flow:

```bash
.venv\Scripts\python.exe manage.py check_eunoia_readiness --strict
.venv\Scripts\python.exe manage.py smoke_test_eunoia_demo
```

4. levantar la app:

```bash
.venv\Scripts\python.exe manage.py runserver
```

## Usuarios demo

### Staff

- `admin.demo@example.com` / `DemoAdmin2026!` -> superuser para `/admin/` y `/staff/`
- `staff.demo@example.com` / `DemoStaff2026!` -> staff operativo para `/staff/`

### Alumnas

Todas usan la misma password: `DemoStudent2026!`

- `ada.demo@example.com` -> activa, con reserva futura
- `bea.demo@example.com` -> impaga, sirve para mostrar bloqueo operativo
- `clara.demo@example.com` -> suspendida
- `dora.demo@example.com` -> con recuperacion ya usada
- `eva.demo@example.com` -> con recuperacion disponible por cancelacion
- `sofia.demo@example.com` -> sin datos previos de reserva, ideal para repetir el smoke test manual

## Smoke test manual sugerido

1. entrar a `http://127.0.0.1:8000/login/` con `sofia.demo@example.com`;
2. abrir `Agenda`, reservar una clase de `Reformer Abajo` y revisar `Mis turnos`;
3. cancelar esa reserva con mas de 2 horas de anticipacion y validar que aparece la recuperacion;
4. entrar al flujo `Elegir clase` de esa recuperacion y usarla en otra clase compatible;
5. salir e ingresar con `staff.demo@example.com`;
6. revisar `http://127.0.0.1:8000/staff/`, la ficha de `Eva Peron` y `http://127.0.0.1:8000/staff/clases/`.

## Notas de repetibilidad

- `seed_demo_eunoia` solo recrea las alumnas demo conocidas por email `*.demo@example.com`; no intenta borrar datos reales ajenos a la demo.
- las usuarias staff demo siempre quedan con password conocida porque el comando las actualiza en cada corrida.
- el smoke automatizado usa `sofia.demo@example.com` dentro de una transaccion y deja la base igual que antes de correrlo.
