import { test, expect } from '@playwright/test';
import { loginAs, USERS } from './fixtures/auth';
import { createDraftApplication, reviewAndSubmit, confirmMockPayment } from './fixtures/applications';

test.describe('core application workflow', () => {
  test('institution submits, confirms mock payment, scrutiny clears into EVC queue', async ({ page, browser }) => {
    await loginAs(page, USERS.institutionA);
    await createDraftApplication(page);
    await reviewAndSubmit(page);

    // Submitting alone does not auto-advance past SUBMITTED (the PAYMENT_VERIFIED
    // precondition checks payment_status directly), so the flash must say exactly
    // that — not claim payment is already verified. This is the fix under test.
    await expect(page.getByText('Application submitted. Current stage: "Submitted".')).toBeVisible();

    await confirmMockPayment(page);
    // Confirming payment triggers the automatic PAYMENT_VERIFIED -> UNDER_SCRUTINY chain,
    // and the stale "submitted" flash must disappear now that it's superseded — this is
    // the lingering post-payment flash bug this change set fixes.
    await expect(page.getByText('Under Scrutiny').first()).toBeVisible();
    await expect(page.getByText('Application submitted. Current stage: "Submitted".')).toBeHidden();

    const applicationUrl = page.url();

    // Switch actor: a scrutiny officer in the same region clears scrutiny.
    const officerContext = await browser.newContext();
    const officerPage = await officerContext.newPage();
    await loginAs(officerPage, USERS.scrutinyOfficerNR);
    await officerPage.goto(applicationUrl);
    await officerPage.getByRole('button', { name: 'Mark scrutiny clear' }).click();
    await officerPage.getByRole('button', { name: 'Confirm: Mark scrutiny clear' }).click();

    // SCRUTINY_CLEAR -> EVC_QUEUED is an automatic follow-up transition.
    await expect(officerPage.getByText('EVC Queued').first()).toBeVisible();
    await officerContext.close();
  });
});
