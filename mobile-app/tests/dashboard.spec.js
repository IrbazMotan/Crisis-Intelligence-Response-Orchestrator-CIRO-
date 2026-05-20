import { test, expect } from '@playwright/test';

test.describe('CIRO Emergency Dashboard', () => {
  test('should load the dashboard and display critical elements', async ({ page }) => {
    // Navigate to the React frontend
    await page.goto('http://localhost:5173');

    // Check if the main title/brand is visible
    await expect(page.locator('text=CIRO')).toBeVisible();

    // Check if tabs are present
    const tabs = ['Emergency Trigger', 'Crisis Intelligence', 'Agent Trace Logs'];
    for (const tab of tabs) {
      await expect(page.locator(`button:has-text("${tab}")`).first()).toBeVisible();
    }
  });

  test('should be able to switch to Crisis Intelligence tab', async ({ page }) => {
    await page.goto('http://localhost:5173');
    
    // Click on the Crisis Intelligence tab
    await page.click('button:has-text("Crisis Intelligence")');
    
    // Verify that the Analyze button appears
    await expect(page.locator('button:has-text("Analyze Crisis Signals")')).toBeVisible();
  });
});
