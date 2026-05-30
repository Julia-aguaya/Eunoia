# Roadmap Frontend Ejecutable (Django Templates) - Eunoia

## Objetivo
- Entregar un frontend web operativo para turnos de pilates, 100% server-rendered con Django templates, que permita a alumna y staff completar flujos reales de punta a punta sin depender de Django admin para lo cotidiano.

## Principios de implementacion
- Backend manda: reglas de negocio viven en modelos/servicios (`Booking`, `MonthlyAccessStatus`, `RecoveryCredit`, `HolidayClosure`).
- Frontend refleja: templates muestran estado y acciones; no duplican validaciones de dominio.
- Una accion = un POST chico y trazable, con feedback via `django.contrib.messages`.
- Evolucion incremental: cada sprint termina en demo ejecutable sobre `/login/`, `/`, `/agenda/`, `/mis-turnos/`, `/staff/`.

## Orden exacto de pantallas

### Alumna
1. `/login/`
2. `/change-password-required/` (solo si `must_change_password=True`)
3. `/` (home)
4. `/agenda/`
5. `/mis-turnos/`
6. `/recuperaciones/<id>/usar/` (cuando hay recuperaciones)

### Staff
1. `/login/`
2. `/staff/`
3. `/staff/alumnas/<id>/`
4. `/staff/clases/`
5. `/staff/clases/<id>/`

## Fases y sprints

### Sprint 1 (1 semana): Base UX alumna
**Estado**: Ejecutado

**Entregables**
- Navegacion consistente en portal alumna (`/`, `/agenda/`, `/mis-turnos/`).
- Estados visibles de acceso mensual: activa, impaga/suspendida, sin acceso cargado.
- Listados con vacios utiles y CTAs claros (sin botones muertos).

**Criterios de aceptacion**
- Alumna logueada puede recorrer las 3 pantallas sin romper flujo.
- Si no puede reservar por estado mensual, UI lo muestra en texto claro.
- No hay logica de negocio nueva en template o JS.

**Plan de demo (fin de sprint)**
- Login como alumna -> home -> agenda -> mis turnos.
- Mostrar caso con acceso activo y caso suspendido.

**Checklist demo interna (viernes - activa/suspendida)**
- [ ] Alumna activa: en `/` se ve `Acceso operativo activo` y CTA a agenda/mis turnos.
- [ ] Alumna activa: en `/agenda/` puede reservar cuando el dominio devuelve `Reservar`.
- [ ] Alumna activa: en `/mis-turnos/` ve reservas activas, cancelacion disponible y recuperaciones.
- [ ] Alumna suspendida/impaga: en `/` aparece bloqueo operativo con acciones claramente deshabilitadas.
- [ ] Alumna suspendida/impaga: en `/agenda/` se ven horarios/cupos pero no permite reservar.
- [ ] Alumna suspendida/impaga: en `/mis-turnos/` se explica que no puede operar y conserva visibilidad de sus turnos.

### Sprint 2 (1 semana): Reserva y cancelacion operativas
**Estado**: Ejecutado

**Entregables**
- Accion `Reservar` desde `/agenda/` conectada a `Booking.objects.create_booking(...)`.
- Accion `Cancelar turno` desde `/mis-turnos/` conectada a `Booking.cancel_by_student(...)`.
- Mensajeria clara para errores de negocio (cupo, ventana de 2 horas, seccion, duplicado).

**Criterios de aceptacion**
- Reserva exitosa aparece en `/mis-turnos/` y home en el mismo flujo.
- Cancelacion valida genera recuperacion y libera la reserva activa.
- Cancelacion fuera de ventana se rechaza con mensaje entendible.

**Plan de demo (fin de sprint)**
- Alumna reserva una clase futura.
- Alumna cancela con mas de 2 horas.
- Mostrar rechazo de cancelacion fuera de ventana.

**Checklist demo Sprint 2 (reserva/cancelacion operativa)**
- [ ] En `/agenda/`, una clase disponible muestra `Reservar` y al confirmar aparece feedback de exito.
- [ ] En `/agenda/`, una clase sin cupo muestra estado `Sin cupo` y accion bloqueada coherente.
- [ ] En `/agenda/`, una clase ya reservada muestra `Ya reservado` y evita duplicado desde la UI.
- [ ] En `/mis-turnos/`, cancelar con mas de 2 horas confirma exito y genera recuperacion disponible.
- [ ] En `/mis-turnos/`, cancelar dentro de 2 horas rechaza la accion con mensaje claro.
- [ ] En `/mis-turnos/`, luego de cancelacion valida se refleja la reserva removida y la recuperacion vigente.

### Sprint 3 (1 semana): Recuperaciones + staff base
**Estado**: Ejecutado

**Entregables**
- Flujo de recuperaciones en `/recuperaciones/<id>/usar/` usando `create_booking(..., used_recovery_credit=...)`.
- Portal staff `/staff/` con buscador y accion de activar/suspender acceso mensual.
- Ficha de alumna `/staff/alumnas/<id>/` con contexto operativo (reservas, recuperaciones, estado mensual).

**Criterios de aceptacion**
- Recuperacion solo permite reservar clases futuras de la misma `Section`.
- Staff no-admin/no-staff queda bloqueado (403) en portal staff.
- Cambios de acceso mensual se reflejan en UI staff y en portal alumna.

**Plan de demo (fin de sprint)**
- Alumna usa una recuperacion en clase compatible.
- Staff busca alumna, activa/suspende acceso y valida efecto inmediato.

**Checklist demo Sprint 3 (recuperaciones + staff base)**
- [ ] En `/mis-turnos/`, la alumna ve recuperaciones disponibles y vencidas con CTA claro para operar solo las vigentes.
- [ ] En `/recuperaciones/<id>/usar/`, se listan sesiones futuras de la misma seccion con estado compatible/no compatible segun reglas de backend.
- [ ] Si la recuperacion ya no esta disponible, el flujo redirige a `/mis-turnos/` con mensaje claro y sin permitir reservas inconsistentes.
- [ ] En `/staff/`, staff filtra por nombre/email y ve seccion principal + estado operativo/pago del mes actual.
- [ ] En `/staff/alumnas/<id>/`, staff puede activar/suspender acceso mensual y ver el impacto inmediato en la ficha.
- [ ] En `/staff/alumnas/<id>/`, staff puede otorgar recuperacion manual, marcar disponible como vencida y ver auditoria reciente.

### Sprint 4 (1 semana): Agenda staff y pulido final demo
**Estado**: Ejecutado

**Entregables**
- Agenda staff `/staff/clases/` con filtro por fecha/seccion y accion de cierre por feriado.
- Detalle de sesion `/staff/clases/<id>/` con ocupacion, reservas activas y recuperaciones asociadas.
- Pulido final de textos, estados y navegacion para demo/handoff.

**Criterios de aceptacion**
- Cierre por feriado aplica impacto visible en sesiones/reservas del dia.
- Staff puede seguir hilo completo: listado -> detalle alumna -> agenda clases -> detalle sesion.
- Demo end-to-end se ejecuta sin pasar por Django admin.

**Plan de demo (fin de sprint)**
- Staff aplica cierre de feriado y muestra impacto del dia.
- Staff abre detalle de sesion y explica ocupacion/recuperaciones.
- Alumna valida estado final en su portal.

## Riesgos y mitigaciones
- Riesgo: duplicar reglas de dominio en templates/vistas.
- Mitigacion: toda accion POST delega a metodos de dominio existentes; code review bloquea logica en template.

- Riesgo: datos de demo inconsistentes para mostrar flujo completo.
- Mitigacion: usar `seed_demo_eunoia` + `smoke_test_eunoia_demo` antes de cada demo de sprint.

- Riesgo: regresiones entre flujos alumna/staff por cambios de UI.
- Mitigacion: smoke manual fijo por sprint y tests `manage.py test scheduling`.

- Riesgo: sobrecarga de alcance (querer SPA/React temprano).
- Mitigacion: mantener stack Django templates hasta cerrar este roadmap; React se evalua recien con metricas de uso reales.

## Checklist semanal de avance
- Lunes: definir alcance de sprint (3-5 historias maximo) y criterios de aceptacion.
- Martes: implementar templates + vistas POST/GET del sprint.
- Miercoles: integrar mensajes UX y estados de error reales.
- Jueves: smoke manual completo alumna + staff.
- Viernes: demo de sprint, cierre de pendientes, y backlog del proximo sprint.

## Definicion de terminado por sprint
- Flujo demo ejecutado de punta a punta sin bloqueos.
- Criterios de aceptacion del sprint validados manualmente.
- Sin cambios de arquitectura: se mantiene enfoque server-rendered Django.

## Checklist final demo completa (alumna + staff)
- [ ] Login como staff y recorrido completo: `/staff/` -> `/staff/alumnas/<id>/` -> `/staff/clases/` -> `/staff/clases/<id>/`.
- [ ] En `/staff/clases/`, validar lectura operativa por fecha/seccion: estado, cupo, reservas activas, recuperaciones en uso y recuperaciones generadas.
- [ ] Aplicar cierre por feriado desde `/staff/clases/` y verificar impacto del dia (sesiones cerradas + recuperaciones creadas/ya existentes).
- [ ] En `/staff/clases/<id>/`, validar detalle de ocupacion, reservas activas, historial reciente e impacto de cierre cuando aplica.
- [ ] Login como alumna activa: revisar `/`, `/agenda/`, `/mis-turnos/`, `/recuperaciones/<id>/usar/` con mensajes consistentes.
- [ ] Confirmar que bloqueos operativos (impaga/suspendida) muestran agenda visible pero acciones no operables, sin romper flujo.
- [ ] Ejecutar smoke de reserva/cancelacion/recuperacion para comprobar coherencia end-to-end sin usar Django admin.
