# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: dashboard.spec.js >> CIRO Emergency Dashboard >> should load the intake form and select a city
- Location: e2e\dashboard.spec.js:9:3

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByText('EMERGENCY INTAKE')
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for getByText('EMERGENCY INTAKE')

```

```yaml
- heading "CIRO PLATFORM" [level=1]
- paragraph: Crisis Intelligence & Response Orchestrator — Mobile Client
- heading "Crisis Orchestration" [level=2]
- text: "SELECT REGIONAL CITY 🌡️ Karachi Live: 28°C"
- button "KARACHI"
- button "LAHORE"
- button "ISLAMABAD"
- text: ⚠️ GPS unavailable. Please enter address manually below. SELECT DISASTER TYPE
- button "Accident"
- button "Flood"
- button "Heatwave"
- text: PATIENT LOCATION ADDRESS
- textbox "Synchronizing device coordinates...": 📍 Live GPS Coordinates Synchronized (Karachi)
- button "Refresh Coordinates Location"
- text: RESOURCE SPECIFICATIONS Requires ICU Bed Reserves intensive trauma care node Requires Ventilator Support Allocates pressurized lung ventilator
- button "LAUNCH AUTONOMOUS DISPATCH"
- text: GOOGLE ANTIGRAVITY AGENTIC PIPELINE WORKFLOW • HACKATHON PRESENTATION MODE
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | 
  3  | test.describe('CIRO Emergency Dashboard', () => {
  4  |   test.beforeEach(async ({ page }) => {
  5  |     // Go to the local dashboard
  6  |     await page.goto('http://localhost:5173');
  7  |   });
  8  | 
  9  |   test('should load the intake form and select a city', async ({ page }) => {
  10 |     // Ensure the title is visible
> 11 |     await expect(page.getByText('EMERGENCY INTAKE')).toBeVisible();
     |                                                      ^ Error: expect(locator).toBeVisible() failed
  12 | 
  13 |     // Select Islamabad
  14 |     await page.getByRole('button', { name: 'Islamabad' }).click();
  15 |     
  16 |     // Check if location text updates
  17 |     await expect(page.getByPlaceholder('e.g. huge fire at clifton, multiple casualties...')).toBeVisible();
  18 |   });
  19 | 
  20 |   test('should trigger fraud alert on fake heatwave', async ({ page }) => {
  21 |     // Select Heatwave
  22 |     await page.getByText('Heatwave', { exact: true }).click();
  23 |     
  24 |     // Type a location
  25 |     await page.getByPlaceholder('e.g. huge fire at clifton').fill('Fake Palace Islamabad');
  26 |     
  27 |     // Trigger SOS
  28 |     await page.getByRole('button', { name: 'TRIGGER SOS PIPELINE' }).click();
  29 | 
  30 |     // Wait for the fraud logic
  31 |     // Heatwave requires temp > 38. If the live API returns < 38, it throws an error toast.
  32 |     await expect(page.getByText('Blocked: Live')).toBeVisible({ timeout: 10000 });
  33 |   });
  34 | 
  35 |   test('should trigger accident and bypass weather checks', async ({ page }) => {
  36 |     // Select Accident
  37 |     await page.getByText('Accident').click();
  38 |     
  39 |     // Type a prompt that triggers ICU
  40 |     await page.getByPlaceholder('e.g. huge fire').fill('Terrible accident at Clifton Karachi, need ICU and ventilator immediately');
  41 |     
  42 |     // Trigger SOS
  43 |     await page.getByRole('button', { name: 'TRIGGER SOS PIPELINE' }).click();
  44 | 
  45 |     // Should transition to loading/dispatch screen
  46 |     await expect(page.getByText('AUTONOMOUS DISPATCH INITIALIZED')).toBeVisible({ timeout: 10000 });
  47 | 
  48 |     // Eventually should show Map view
  49 |     await expect(page.locator('#dashboard-map')).toBeVisible({ timeout: 15000 });
  50 |   });
  51 | });
  52 | 
```