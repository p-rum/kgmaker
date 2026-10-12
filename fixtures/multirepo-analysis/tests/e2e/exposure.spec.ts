import { test, expect } from '@playwright/test';
import { clientFixture } from './fixture';
test('decline is displayed', async ({ request, page }) => {
  const response = await request.get('/api/exposure');
  const data = await response.json();
  expect(data.decline).toBe(2);
  await expect(page.getByTestId('decline')).toHaveText('2');
});
test('request only', async ({ request }) => {
  await request.get('/api/exposure');
});
