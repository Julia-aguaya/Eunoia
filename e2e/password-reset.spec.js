const { test, expect } = require('@playwright/test');

const oldPassword = 'E2E-Only-Password-2026!';

for (const email of ['e2e.password-reset-desktop@example.test', 'e2e.password-reset-mobile@example.test']) {
  test(`password reset works end-to-end for ${email}`, async ({ page, context }, testInfo) => {
    test.skip((testInfo.project.name === 'chromium-mobile') !== email.includes('mobile'), 'Use one seeded account per viewport.');
    const newPassword = `Nueva-E2E-${testInfo.project.name}-2026!`;

    await context.clearCookies();
    await page.goto('/login/');
    await page.getByRole('link', { name: 'Olvidé mi contraseña' }).click();
    await page.getByLabel('Email').fill(email);
    await page.getByRole('button', { name: 'Enviar instrucciones' }).click();
    await expect(page.getByText('Si existe una cuenta con ese email', { exact: false })).toBeVisible();

    const outbox = await page.request.get('/__e2e__/outbox/');
    const { emails } = await outbox.json();
    const body = emails.at(-1).body;
    const resetPath = new URL(body.match(/http:\/\/127\.0\.0\.1:8000([^\s]+)/)[1], 'http://127.0.0.1:8000').pathname;

    await page.goto(resetPath);
    await page.locator('input[name="new_password1"]').fill(newPassword);
    await page.locator('input[name="new_password2"]').fill(newPassword);
    await page.getByRole('button', { name: 'Guardar nueva contraseña' }).click();
    await expect(page.getByText('Contraseña actualizada', { exact: true })).toBeVisible();

    await page.getByRole('link', { name: 'Ingresar' }).click();
    await page.getByLabel('Email').fill(email);
    await page.getByRole('textbox', { name: 'Contraseña' }).fill(newPassword);
    await page.getByRole('button', { name: 'Ingresar' }).click();
    await page.waitForURL((url) => url.pathname !== '/login/');

    await context.clearCookies();
    await page.goto('/login/');
    await page.getByLabel('Email').fill(email);
    await page.getByRole('textbox', { name: 'Contraseña' }).fill(oldPassword);
    await page.getByRole('button', { name: 'Ingresar' }).click();
    await expect(page.getByText('No pudimos iniciar sesion', { exact: true })).toBeVisible();

    await page.goto(resetPath);
    await expect(page.getByText('El enlace ya no es válido', { exact: true })).toBeVisible();
  });
}
