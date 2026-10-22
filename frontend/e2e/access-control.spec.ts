import { test, expect } from '@playwright/test';
import { loginAs, USERS } from './fixtures/auth';
import { createDraftApplication, reviewAndSubmit } from './fixtures/applications';

test.describe('backend-enforced access control', () => {
  test('a different institution cannot open another institution\'s application', async ({ page, browser }) => {
    await loginAs(page, USERS.institutionA);
    await createDraftApplication(page);
    await reviewAndSubmit(page);
    const applicationUrl = page.url();

    const otherContext = await browser.newContext();
    const otherPage = await otherContext.newPage();
    await loginAs(otherPage, USERS.institutionB);

    const response = await otherPage.goto(applicationUrl);
    // The API call for the detail page must be rejected server-side (403),
    // regardless of what the page renders — this is the actual safeguard
    // (app.core.scoping), not a frontend route guard.
    const apiResponse = await otherPage.waitForResponse((r) => /\/api\/applications\/[^/]+$/.test(r.url()));
    expect(apiResponse.status()).toBe(403);
    void response;
    await otherContext.close();
  });

  test('a non-admin role is blocked by the backend from the user-management API', async ({ page }) => {
    await loginAs(page, USERS.institutionA);
    const [apiResponse] = await Promise.all([
      page.waitForResponse((r) => /\/api\/users(\?|$)/.test(r.url())),
      page.goto('/users'),
    ]);
    // The sidebar hides this nav entry for non-admins, but the real safeguard
    // is server-side role enforcement — assert on that directly.
    expect(apiResponse.status()).toBe(403);
  });
});
