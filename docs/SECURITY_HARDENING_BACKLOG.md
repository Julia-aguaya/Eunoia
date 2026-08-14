# Backlog de hardening de autenticación

Estos puntos se identificaron durante el diseño de recuperación de contraseña y quedan fuera del alcance de `feat/password-reset` para mantener el cambio aislado.

1. **Configuración productiva fail-closed.** Exigir `DJANGO_SECRET_KEY` y `DJANGO_DEBUG=False` fuera de desarrollo, sin valores de respaldo.
2. **Cambio de email.** Requerir la contraseña actual y verificar el nuevo email antes de convertirlo en identificador de acceso.
3. **Logout.** Cambiar el endpoint actual para aceptar únicamente `POST` protegido por CSRF.
4. **Artefactos legacy.** Auditar y retirar de Git exports históricos que puedan incluir hashes o material sensible de recuperación.
5. **Correo transaccional.** Antes de habilitar entrega real, configurar SMTP, SPF, DKIM y DMARC fuera del repositorio; mantener desactivado el click tracking para enlaces de recuperación.
