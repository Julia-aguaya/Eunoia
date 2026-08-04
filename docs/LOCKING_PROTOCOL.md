# Locking protocol

When a use case needs more than one mutable domain record, acquire locks in this
order. Within each type, lock records by ascending primary key.

1. `User(pk)`
2. `ClassSession(pk)`
3. `MonthlyAccessStatus(month, pk)`
4. `RecoveryCredit(pk)`
5. `Booking(pk)`

This is the global ordering for future concurrency hardening. Phase 1 only
applies it to the admin/import student-activation boundary; it does not change
booking creation or restoration internals.
