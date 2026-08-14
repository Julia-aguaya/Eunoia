# Revisión manual local: reset de contraseña

Desde el worktree `Eunoia-password-reset`, iniciá el preview aislado:

```powershell
& "C:\Users\julia\Desktop\Eunoia\.venv\Scripts\python.exe" scripts\run_password_reset_preview.py
```

- Login: `http://127.0.0.1:8000/login/`
- Alumna exclusiva: `e2e.password-reset-manual@example.test`
- Contraseña actual: `E2E-Only-Password-2026!`
- Buzón local: `http://127.0.0.1:8000/__e2e__/outbox/`

El preview fuerza `settings_e2e`, una SQLite temporal y el backend `locmem`; no usa `.env`, `DATABASE_URL`, Resend ni ningún servicio externo. Después de solicitar el reset, abrí el buzón local y copiá el enlace **local** del cuerpo del último email: empieza con `http://127.0.0.1:8000/password-reset/`. El servidor escucha únicamente en `127.0.0.1`.

Probá el flujo desde el enlace **Olvidé mi contraseña**, verificá la pantalla neutra, elegí una contraseña nueva, iniciá sesión con ella, comprobá que la anterior falla y que el enlace no puede reutilizarse. Revisá el mismo flujo con el emulador móvil del navegador y en escritorio.

Detené el preview con `Ctrl+C`. El script borra automáticamente la SQLite temporal y sus datos E2E.
