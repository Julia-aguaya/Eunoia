const { test, expect } = require('@playwright/test');

const password = 'E2E-Only-Password-2026!';

function projectSuffix(testInfo) {
  return testInfo.project.name === 'chromium-mobile' ? 'mobile' : 'desktop';
}

async function login(page, email) {
  await page.goto('/login/');
  await page.getByLabel('Email').fill(email);
  await page.getByRole('textbox', { name: 'Contraseña' }).fill(password);
  await page.getByRole('button', { name: 'Ingresar' }).click();
  await page.waitForURL((url) => url.pathname !== '/login/');
}

test('staff reactivates a suspended student and the student can use the portal', async ({ page }, testInfo) => {
  const suffix = projectSuffix(testInfo);
  const studentEmail = `e2e.suspendida-${suffix}@example.test`;
  await login(page, 'e2e.staff@example.test');
  await page.getByPlaceholder('Nombre, apellido o email').fill(studentEmail);
  await page.getByRole('button', { name: 'Buscar' }).click();
  await expect(page.getByText('Bloqueado', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Reactivar acceso' }).click();
  await expect(page.getByText('Activo', { exact: true })).toBeVisible();

  await page.context().clearCookies();
  await login(page, studentEmail);
  await expect(page.getByText('Activa', { exact: true })).toBeVisible();
});

test('staff recurring-slot automation generates a visible class', async ({ page }, testInfo) => {
  const startHour = testInfo.project.name === 'chromium-mobile' ? '16:00' : '15:00';
  const endHour = testInfo.project.name === 'chromium-mobile' ? '17:00' : '16:00';
  await login(page, 'e2e.staff@example.test');
  await page.goto('/staff/clases/');

  const form = page.getByTestId('recurring-slot-form');
  await form.getByLabel('Actividad').selectOption({ label: 'Cadillac' });
  await form.getByLabel('Día de la semana').selectOption({ label: 'Lunes' });
  await form.getByLabel('Hora de inicio').fill(startHour);
  await form.getByLabel('Hora de fin').fill(endHour);
  await form.getByLabel('Cupo').fill('2');
  await form.getByRole('button', { name: 'Crear horario recurrente' }).click();

  await expect(page.getByText('Sesiones futuras generadas:', { exact: false })).toBeVisible();
  await expect(page.getByText(`${startHour} - ${endHour}`, { exact: true })).toBeVisible();
});
