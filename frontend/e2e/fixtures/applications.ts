import type { Page } from '@playwright/test';
import { expect } from '@playwright/test';

/**
 * Creates a draft "Increase in Intake / Additional Course" application
 * (route FULL: scrutiny + EVC), fills every required field, and leaves the
 * page on the draft edit screen's step 1 (review not yet submitted).
 * Returns the application id parsed from the URL.
 */
export async function createDraftApplication(page: Page): Promise<string> {
  await page.goto('/applications/new');
  await page.getByText('Increase in Intake / Additional Course').click();
  await page.getByRole('button', { name: 'Continue' }).click();
  await page.waitForURL(/\/applications\/[^/]+\/edit/);
  const id = page.url().match(/\/applications\/([^/]+)\/edit/)?.[1];
  if (!id) throw new Error('Could not parse application id from URL after draft creation');

  await page.getByLabel('Contact person name').fill('Test Contact');
  await page.getByLabel('Designation').fill('Registrar');
  await page.getByLabel('Contact email').fill('registrar@demo.ac.in');
  await page.getByLabel('Contact phone').fill('9876543210');
  await page.getByLabel('Summary of request').fill('Requesting an intake increase for the upcoming academic year.');
  await page.getByLabel('Programme').fill('Computer Science and Engineering');
  await page.getByLabel('Course').fill('B.Tech CSE');
  await page.getByLabel('Level').selectOption('Under Graduate');
  await page.getByLabel('Current approved intake').fill('60');
  await page.getByLabel('Proposed intake').fill('120');
  await page.getByLabel(/I confirm that the information provided is accurate/).check();

  return id;
}

/** From the draft edit page (step 1, already filled), reviews and submits. */
export async function reviewAndSubmit(page: Page): Promise<void> {
  await page.getByRole('button', { name: 'Review' }).click();
  await expect(page.getByRole('button', { name: 'Submit application' })).toBeVisible();
  await page.getByRole('button', { name: 'Submit application' }).click();
  await page.waitForURL(/\/applications\/[^/]+$/);
}

/**
 * Confirms the mock payment on the detail page. This is what actually
 * triggers the automatic SUBMITTED -> PAYMENT_VERIFIED -> UNDER_SCRUTINY
 * chain server-side — submitting alone does not advance past SUBMITTED,
 * since the PAYMENT_VERIFIED precondition checks payment_status directly.
 */
export async function confirmMockPayment(page: Page): Promise<void> {
  await page.getByRole('button', { name: 'Simulate payment (MOCK)' }).click();
  await expect(page.getByText('Mock confirmed')).toBeVisible();
}
