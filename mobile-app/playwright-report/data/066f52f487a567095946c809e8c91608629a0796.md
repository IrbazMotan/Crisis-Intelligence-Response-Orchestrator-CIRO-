# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: dashboard.spec.js >> CIRO Emergency Dashboard >> should trigger accident and bypass weather checks
- Location: e2e\dashboard.spec.js:35:3

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: locator.fill: Test timeout of 30000ms exceeded.
Call log:
  - waiting for getByPlaceholder('e.g. huge fire')

```

# Page snapshot

```yaml
- generic [ref=e3]:
  - generic [ref=e4]:
    - generic [ref=e5]:
      - img [ref=e6]
      - heading "CIRO PLATFORM" [level=1] [ref=e8]
    - paragraph [ref=e9]: Crisis Intelligence & Response Orchestrator — Mobile Client
  - generic [ref=e18]:
    - heading "Crisis Orchestration" [level=2] [ref=e19]
    - generic [ref=e20]:
      - generic [ref=e21]:
        - generic [ref=e22]: SELECT REGIONAL CITY
        - generic [ref=e25]: "🌡️ Karachi Live: 28°C"
      - generic [ref=e26]:
        - button "KARACHI" [ref=e27]
        - button "LAHORE" [ref=e28]
        - button "ISLAMABAD" [ref=e29]
    - generic [ref=e30]:
      - img [ref=e31]
      - generic [ref=e33]: ⚠️ GPS unavailable. Please enter address manually below.
    - generic [ref=e34]:
      - text: SELECT DISASTER TYPE
      - generic [ref=e35]:
        - button "Accident" [active] [ref=e36]:
          - img [ref=e37]
          - generic [ref=e39]: Accident
        - button "Flood" [ref=e40]:
          - img [ref=e41]
          - generic [ref=e44]: Flood
        - button "Heatwave" [ref=e45]:
          - img [ref=e46]
          - generic [ref=e52]: Heatwave
    - generic [ref=e53]:
      - text: PATIENT LOCATION ADDRESS
      - generic [ref=e54]:
        - generic:
          - img
        - textbox "Synchronizing device coordinates..." [ref=e55]: 📍 Live GPS Coordinates Synchronized (Karachi)
        - button "Refresh Coordinates Location" [ref=e56]:
          - img [ref=e57]
    - generic [ref=e60]:
      - text: RESOURCE SPECIFICATIONS
      - generic [ref=e61]:
        - generic [ref=e63] [cursor=pointer]:
          - img [ref=e65]
          - generic [ref=e67]:
            - generic [ref=e68]: Requires ICU Bed
            - generic [ref=e69]: Reserves intensive trauma care node
        - generic [ref=e73] [cursor=pointer]:
          - img [ref=e75]
          - generic [ref=e77]:
            - generic [ref=e78]: Requires Ventilator Support
            - generic [ref=e79]: Allocates pressurized lung ventilator
    - button "LAUNCH AUTONOMOUS DISPATCH" [ref=e83]
  - generic [ref=e84]: GOOGLE ANTIGRAVITY AGENTIC PIPELINE WORKFLOW • HACKATHON PRESENTATION MODE
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
  11 |     await expect(page.getByText('EMERGENCY INTAKE')).toBeVisible();
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
> 40 |     await page.getByPlaceholder('e.g. huge fire').fill('Terrible accident at Clifton Karachi, need ICU and ventilator immediately');
     |                                                   ^ Error: locator.fill: Test timeout of 30000ms exceeded.
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