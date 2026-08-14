const { test, expect } = require('@playwright/test');

const password = 'E2E-Only-Password-2026!';
const matrix = {
  cadillac: ['cadillac', 'reformer_arriba', 'reformer_abajo'],
  arriba: ['reformer_arriba', 'reformer_abajo'],
  abajo: ['reformer_arriba', 'reformer_abajo'],
};
const labels = {
  cadillac: 'Cadillac',
  reformer_arriba: 'Reformer Arriba',
  reformer_abajo: 'Reformer Abajo',
};

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

for (const [origin, targets] of Object.entries(matrix)) {
  for (const target of targets) {
    test(`student recovery cross-matrix ${origin} to ${target}`, async ({ page }, testInfo) => {
      await login(page, `e2e.${origin}-${target}-${projectSuffix(testInfo)}@example.test`);
      await page.goto('/mis-turnos/');
      await page.getByRole('link', { name: /Ver actividades|Ver horarios/ }).click();

      const activities = page.getByLabel('Elegir actividad para recuperar');
      for (const allowed of targets) {
        await expect(activities.getByRole('link', { name: labels[allowed], exact: true })).toBeVisible();
      }
      if (origin !== 'cadillac') {
        await expect(activities.getByRole('link', { name: 'Cadillac', exact: true })).toHaveCount(0);
      }

      await activities.getByRole('link', { name: labels[target], exact: true }).click();
      await expect(page).toHaveURL(/#recovery-picker$/);
      await expect(page.locator('#recovery-picker')).toBeInViewport();
      await expect(page.locator('#recovery-picker')).toBeFocused();
      await page.getByRole('link', { name: '11', exact: true }).click();
      await page.getByRole('link', { name: '09:00', exact: true }).click();
      await page.getByRole('button', { name: 'Confirmar recuperación' }).click();
      await expect(page.getByText(`Reservaste ${labels[target]}`, { exact: false })).toBeVisible();
    });
  }
}

test('capacity blocks recovery booking when the only place is occupied', async ({ page }, testInfo) => {
  await login(page, `e2e.capacity-${projectSuffix(testInfo)}@example.test`);
  await page.goto('/mis-turnos/');
  await page.getByRole('link', { name: /Ver actividades|Ver horarios/ }).click();
  await page.getByLabel('Elegir actividad para recuperar').getByRole('link', { name: 'Reformer Arriba' }).click();
  await page.getByRole('link', { name: '11', exact: true }).click();

  const fullSlotName = `${projectSuffix(testInfo) === 'mobile' ? '13' : '12'}:00 - cupo completo`;
  const fullSlot = page.getByText(fullSlotName, { exact: true });
  await expect(fullSlot).toBeVisible();
  await expect(page.getByRole('link', { name: fullSlotName })).toHaveCount(0);
});
