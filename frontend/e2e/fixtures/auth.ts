import type { Page } from '@playwright/test';
import { expect } from '@playwright/test';

export const DEMO_PASSWORD = 'Demo@123';

/** Seeded demo accounts this suite relies on (see backend/seed.py). */
export const USERS = {
  institutionA: 'institution@demo.ac.in', // NR region
  institutionB: 'institution2@demo.ac.in', // SR region — different institution, for access-control tests
  scrutinyOfficerNR: 'scrutiny@flowguard.gov.in',
  admin: 'admin@flowguard.gov.in',
  authority: 'authority@flowguard.gov.in',
} as const;

/**
 * Logs in through the real login form and waits for the authenticated shell
 * to actually render before returning. This is the "safe navigation
 * sequence": it waits on the post-login URL change and a landmark becoming
 * visible, rather than a fixed sleep, so callers never race the auth
 * redirect or a half-rendered dashboard.
 */
export async function loginAs(page: Page, email: string, password: string = DEMO_PASSWORD): Promise<void> {
  await page.goto('/login');
  await page.getByPlaceholder('you@example.com').fill(email);
  await page.getByPlaceholder('Enter your password').fill(password);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.waitForURL((url) => !url.pathname.startsWith('/login'));
  await expect(page.getByText('AICTE FlowGuard').first()).toBeVisible();
}
