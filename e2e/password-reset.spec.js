const { test, expect } = require('@playwright/test');

const oldPassword = 'E2E-Only-Password-2026!';

async function expectCompactConfirmation(page) {
  await expect(page.getByRole('heading', { name: 'Revisá tu email' })).toBeVisible();
  await expect(page.getByText('Si existe una cuenta con ese email, te enviamos un enlace para crear una nueva contraseña.')).toBeVisible();
  await expect(page.getByText('Puede tardar unos minutos. Revisá también Spam o Correo no deseado.')).toBeVisible();
  await expect(page.getByText('Agenda a mano')).toHaveCount(0);
  await expect(page.getByText('Señales claras')).toHaveCount(0);
}

async function expectSimplePasswordResetComplete(page, testInfo) {
  await expect(page.getByRole('heading', { name: '¡Listo!' })).toBeVisible();
  await expect(page.getByText('Tu contraseña fue actualizada.', { exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Ingresar' })).toHaveAttribute('href', '/login/');
  await expect(page.getByText('Contraseña actualizada', { exact: true })).toHaveCount(0);
  await expect(page.getByText('Tu acceso está protegido', { exact: true })).toHaveCount(0);
  await expect(page.getByText('Ingresá con tu nueva contraseña.', { exact: true })).toHaveCount(0);
  await expect(page.getByText('Ya está, tu contraseña cambió.', { exact: true })).toHaveCount(0);
  await expect(page.locator('.auth-panel:visible')).toHaveCount(0);

  if (testInfo.project.name === 'chromium-mobile') {
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollHeight <= window.innerHeight)).toBe(true);
  }
}

test('password reset disables a double submission and shows sending state', async ({ page }) => {
  await page.goto('/password-reset/');
  await page.getByLabel('Email').fill('e2e.password-reset-manual@example.test');
  await page.evaluate(() => {
    document.querySelector('[data-password-reset-form]').addEventListener('submit', (event) => event.preventDefault());
  });

  await page.getByRole('button', { name: 'Enviar instrucciones' }).click();
  await page.evaluate(() => {
    document.querySelector('[data-password-reset-form]').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
  });

  await expect(page.locator('[data-password-reset-submit]')).toBeDisabled();
  await expect(page.locator('[data-submit-pending]')).toBeVisible();
  await expect(page.locator('[data-password-reset-status]')).toBeVisible();
});

for (const email of ['e2e.password-reset-desktop@example.test', 'e2e.password-reset-mobile@example.test']) {
  test(`password reset works end-to-end for ${email}`, async ({ page, context }, testInfo) => {
    test.skip((testInfo.project.name === 'chromium-mobile') !== email.includes('mobile'), 'Use one seeded account per viewport.');
    const newPassword = `Nueva-E2E-${testInfo.project.name}-2026!`;

    await context.clearCookies();
    await page.goto('/login/');
    await page.getByRole('link', { name: 'Olvidé mi contraseña' }).click();
    await page.getByLabel('Email').fill(email);
    await page.getByRole('button', { name: 'Enviar instrucciones' }).click();
    await expectCompactConfirmation(page);

    const outbox = await page.request.get('/__e2e__/outbox/');
    const { emails } = await outbox.json();
    const body = emails.at(-1).body;
    const resetPath = new URL(body.match(/http:\/\/127\.0\.0\.1:8000([^\s]+)/)[1], 'http://127.0.0.1:8000').pathname;

    await page.goto(resetPath);
    await page.locator('input[name="new_password1"]').fill(newPassword);
    await page.locator('input[name="new_password2"]').fill(newPassword);
    await page.getByRole('button', { name: 'Guardar nueva contraseña' }).click();
    await expectSimplePasswordResetComplete(page, testInfo);

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

test('password reset keeps its server-rendered fallback without JavaScript', async ({ browser }) => {
  const context = await browser.newContext({ baseURL: 'http://127.0.0.1:8000', javaScriptEnabled: false });
  const page = await context.newPage();

  try {
    await page.goto('/password-reset/');
    await page.getByLabel('Email').fill('e2e.password-reset-manual@example.test');
    await page.getByRole('button', { name: 'Enviar instrucciones' }).click();
    await page.waitForURL('**/password-reset/done/');
    await expectCompactConfirmation(page);
  } finally {
    await context.close();
  }
});

test('password reset re-enables submit after a server validation error', async ({ page }) => {
  await page.goto('/password-reset/');
  await page.getByLabel('Email').fill('email-inválido');
  await page.getByRole('button', { name: 'Enviar instrucciones' }).click();

  await expect(page.locator('[data-password-reset-submit]')).toBeEnabled();
  await expect(page.locator('[data-submit-label]')).toBeVisible();
  await expect(page.locator('[data-submit-pending]')).toBeHidden();
});
