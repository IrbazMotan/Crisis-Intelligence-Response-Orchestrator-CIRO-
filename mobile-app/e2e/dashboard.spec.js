import { test, expect } from '@playwright/test';

test.describe('CIRO Emergency Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Go to the local dashboard
    await page.goto('http://localhost:5173');
  });

  test('should load the intake form and select a city', async ({ page }) => {
    // Ensure the title is visible
    await expect(page.getByText('EMERGENCY INTAKE')).toBeVisible();

    // Select Islamabad
    await page.getByRole('button', { name: 'Islamabad' }).click();
    
    // Check if location text updates
    await expect(page.getByPlaceholder('e.g. huge fire at clifton, multiple casualties...')).toBeVisible();
  });

  test('should trigger fraud alert on fake heatwave', async ({ page }) => {
    // Select Heatwave
    await page.getByText('Heatwave', { exact: true }).click();
    
    // Type a location
    await page.getByPlaceholder('e.g. huge fire at clifton').fill('Fake Palace Islamabad');
    
    // Trigger SOS
    await page.getByRole('button', { name: 'TRIGGER SOS PIPELINE' }).click();

    // Wait for the fraud logic
    // Heatwave requires temp > 38. If the live API returns < 38, it throws an error toast.
    await expect(page.getByText('Blocked: Live')).toBeVisible({ timeout: 10000 });
  });

  test('should trigger accident and bypass weather checks', async ({ page }) => {
    // Select Accident
    await page.getByText('Accident').click();
    
    // Type a prompt that triggers ICU
    await page.getByPlaceholder('e.g. huge fire').fill('Terrible accident at Clifton Karachi, need ICU and ventilator immediately');
    
    // Trigger SOS
    await page.getByRole('button', { name: 'TRIGGER SOS PIPELINE' }).click();

    // Should transition to loading/dispatch screen
    await expect(page.getByText('AUTONOMOUS DISPATCH INITIALIZED')).toBeVisible({ timeout: 10000 });

    // Eventually should show Map view
    await expect(page.locator('#dashboard-map')).toBeVisible({ timeout: 15000 });
  });
});
