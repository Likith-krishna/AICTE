import { test, expect } from '@playwright/test';
import { loginAs, USERS } from './fixtures/auth';
import { createDraftApplication, reviewAndSubmit, confirmMockPayment } from './fixtures/applications';

test.describe('deficiency response loop and remarks validation', () => {
  test('deficiency requires >=10 char remarks, institution response re-enters scrutiny', async ({ page, browser }) => {
    await loginAs(page, USERS.institutionA);
    await createDraftApplication(page);
    await reviewAndSubmit(page);
    await confirmMockPayment(page); // advances SUBMITTED -> ... -> UNDER_SCRUTINY
    const applicationUrl = page.url();

    const officerContext = await browser.newContext();
    const officerPage = await officerContext.newPage();
    await loginAs(officerPage, USERS.scrutinyOfficerNR);
    await officerPage.goto(applicationUrl);

    await officerPage.getByRole('button', { name: 'Record deficiency' }).click();
    const confirmBtn = officerPage.getByRole('button', { name: 'Confirm: Record deficiency' });

    // No remarks yet: DEFICIENCY_NOTED requires written remarks (spec: reasons
    // must be recorded for deficiencies), so the confirm action stays disabled.
    await expect(confirmBtn).toBeDisabled();

    await officerPage.getByLabel(/Remarks/).fill('short');
    await expect(confirmBtn).toBeDisabled();

    await officerPage.getByLabel(/Remarks/).fill('Missing the updated faculty ratio annexure.');
    await expect(confirmBtn).toBeEnabled();
    await confirmBtn.click();

    // DEFICIENCY_NOTED -> AWAITING_INSTITUTION_RESPONSE is an automatic follow-up.
    await expect(officerPage.getByText('Awaiting Institution Response').first()).toBeVisible();
    await officerContext.close();

    // Institution responds; RESPONSE_RECEIVED also requires remarks.
    await page.reload();
    await page.getByRole('button', { name: 'Submit deficiency response' }).click();
    const responseConfirm = page.getByRole('button', { name: 'Confirm: Submit deficiency response' });
    await expect(responseConfirm).toBeDisabled();
    await page.getByLabel(/Remarks/).fill('Updated annexure attached as requested.');
    await expect(responseConfirm).toBeEnabled();
    await responseConfirm.click();

    // RESPONSE_RECEIVED -> RE_SCRUTINY is automatic.
    await expect(page.getByText('Re-Scrutiny').first()).toBeVisible();
  });
});
