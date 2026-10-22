import { test, expect } from '@playwright/test';
import { loginAs, USERS } from './fixtures/auth';

test.describe('application detail page tabs', () => {
  test('timeline, details and clock tabs switch panels', async ({ page }) => {
    await loginAs(page, USERS.institutionA);
    await page.goto('/applications');
    await page.locator('table tbody tr').first().click();
    await page.waitForURL(/\/applications\/[^/]+$/);

    const timelineTab = page.getByRole('tab', { name: 'Workflow history' });
    const detailsTab = page.getByRole('tab', { name: 'Application details' });
    const clockTab = page.getByRole('tab', { name: 'Clock log' });

    await expect(timelineTab).toHaveAttribute('aria-selected', 'true');

    await detailsTab.click();
    await expect(detailsTab).toHaveAttribute('aria-selected', 'true');
    await expect(timelineTab).toHaveAttribute('aria-selected', 'false');
    await expect(page.getByRole('tabpanel')).toBeVisible();

    await clockTab.click();
    await expect(clockTab).toHaveAttribute('aria-selected', 'true');

    await timelineTab.click();
    await expect(timelineTab).toHaveAttribute('aria-selected', 'true');
  });
});
