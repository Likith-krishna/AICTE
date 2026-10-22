import { test, expect } from '@playwright/test';
import { loginAs, USERS } from './fixtures/auth';

test.describe('390px mobile viewport', () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test('sidebar is an off-canvas drawer with no horizontal overflow', async ({ page }) => {
    await loginAs(page, USERS.institutionA);

    // The drawer sits in the DOM but is translated off-canvas by default on
    // mobile — assert its actual screen position rather than visibility,
    // since a CSS transform does not make Playwright consider it hidden.
    const drawerBoxBefore = await page.getByRole('link', { name: 'Applications' }).boundingBox();
    expect(drawerBoxBefore && drawerBoxBefore.x + drawerBoxBefore.width).toBeLessThanOrEqual(0);

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow).toBe(0);

    await page.getByRole('button', { name: 'Open navigation' }).click();
    const applicationsLink = page.getByRole('link', { name: 'Applications' });
    await expect(applicationsLink).toBeVisible();

    await applicationsLink.click();
    await page.waitForURL(/\/applications$/);
    // Drawer closes (slides back off-canvas, 200ms transition) after navigating.
    await expect.poll(async () => {
      const box = await page.getByRole('link', { name: 'Applications' }).boundingBox();
      return box ? box.x + box.width : null;
    }).toBeLessThanOrEqual(0);

    const overflowAfterNav = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflowAfterNav).toBe(0);
  });
});
