# Remediacion de cancelaciones por acceso automatico

La remediacion es **dry-run por defecto**. Solo restaura una reserva fija cancelada cuando su `cancellation_origin` es `automatic_access_impact` o existe una fila explicita en `scheduling_bookingremediationapproval`. Un `cancelled_by_id` nulo es historico desconocido, no evidencia de automatizacion.

Las cancelaciones nuevas de reservas registran procedencia de alumna o staff; una cancelacion de clase conserva sus reservas y registra `session_cancellation` en `ClassSession.cancellation_origin`.

## Revisar candidatos (solo SELECT)

Reemplaza las fechas y deja los IDs como placeholders durante la revision.

```sql
SELECT b.id AS booking_id, b.student_id, b.session_id, cs.date AS session_date,
       b.status, b.source, b.cancelled_at, b.cancelled_by_id,
       b.cancellation_origin, b.cancellation_reason,
       a.id AS approval_id, a.approved_at, a.approved_by_id, a.notes
FROM scheduling_booking AS b
JOIN scheduling_classsession AS cs ON cs.id = b.session_id
LEFT JOIN scheduling_bookingremediationapproval AS a ON a.booking_id = b.id
WHERE b.status = 'cancelled'
  AND b.source = 'fixed_slot'
  AND cs.date BETWEEN '<start_date>' AND '<end_date>'
  AND (b.cancellation_origin = 'automatic_access_impact' OR a.id IS NOT NULL)
ORDER BY cs.date, b.id;
```

Para inspeccionar legado no aprobado, sin inferir origen:

```sql
SELECT b.id AS booking_id, b.student_id, b.session_id, cs.date AS session_date,
       b.cancelled_at, b.cancelled_by_id, b.cancellation_origin
FROM scheduling_booking AS b
JOIN scheduling_classsession AS cs ON cs.id = b.session_id
LEFT JOIN scheduling_bookingremediationapproval AS a ON a.booking_id = b.id
WHERE b.status = 'cancelled'
  AND b.source = 'fixed_slot'
  AND b.cancellation_origin IS NULL
  AND a.id IS NULL
ORDER BY cs.date, b.id;
```

## Aprobar legado revisado

Ejecutar solo despues de revisar el `SELECT`; reemplazar placeholders. La transaccion no altera la reserva: deja la evidencia de revision para que el comando aplique sus propias salvaguardas.

```sql
START TRANSACTION;

SELECT id, status, source, cancellation_origin
FROM scheduling_booking
WHERE id = <booking_id>
  AND status = 'cancelled'
  AND source = 'fixed_slot'
FOR UPDATE;

INSERT INTO scheduling_bookingremediationapproval
    (booking_id, approved_by_id, approved_at, notes, created_at, updated_at)
SELECT b.id, <reviewer_user_id>, UTC_TIMESTAMP(),
       'Reviewed legacy cancellation for remediation: <review_reference>',
       UTC_TIMESTAMP(), UTC_TIMESTAMP()
FROM scheduling_booking AS b
WHERE b.id = <booking_id>
  AND b.status = 'cancelled'
  AND b.source = 'fixed_slot'
ON DUPLICATE KEY UPDATE
    approved_by_id = VALUES(approved_by_id),
    approved_at = VALUES(approved_at),
    notes = VALUES(notes),
    updated_at = VALUES(updated_at);

COMMIT;
```

Run the command as review first, then apply only after checking its CSV:

```powershell
.venv\Scripts\python.exe manage.py remediate_automatic_access_impact --start-date <start_date> --end-date <end_date>
.venv\Scripts\python.exe manage.py remediate_automatic_access_impact --start-date <start_date> --end-date <end_date> --apply
```
