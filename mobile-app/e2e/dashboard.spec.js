import { test, expect } from '@playwright/test';

test.use({
  geolocation: { latitude: 24.8569, longitude: 67.0531 },
  permissions: ['geolocation']
});

test.describe('CIRO Emergency Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Listen to browser console logs
    page.on('console', msg => {
      console.log(`BROWSER CONSOLE: [${msg.type()}] ${msg.text()}`);
    });
    // Go to the local dashboard
    await page.goto('http://localhost:5173');
  });

  test('should load the intake form and show critical elements', async ({ page }) => {
    await expect(page.locator('text=Crisis Orchestration')).toBeVisible();
    await expect(page.locator('textarea[placeholder*="Type or paste any raw emergency signal"]')).toBeVisible();
    await expect(page.locator('button:has-text("LAUNCH AUTONOMOUS DISPATCH")')).toBeVisible();
  });

  test('should trigger accident and transition to active map tracking', async ({ page }) => {
    // Select the mock Accident button
    await page.locator('button:has-text("Accident (Hadsa)")').click();
    
    // Check if the textarea is populated
    const textareaValue = await page.locator('textarea').inputValue();
    expect(textareaValue).toContain('Terrible multi-car accident');

    // Trigger the autonomous dispatch
    await page.locator('button:has-text("LAUNCH AUTONOMOUS DISPATCH")').click();

    // Should transition to Step 2 reasoning trace
    await expect(page.locator('text=ORCHESTRATING MISSION...')).toBeVisible({ timeout: 10000 });

    // Wait for the reasoning screen to disappear, meaning it transitioned to Step 3
    await expect(page.locator('text=ORCHESTRATING MISSION...')).toBeHidden({ timeout: 35000 });

    // Verify map is visible (or the status card since Leaflet might fail to render the map in headless chrome)
    await expect(page.locator('text=Ambulance Dispatched')).toBeVisible({ timeout: 20000 });
  });
});

