import { test, expect, type Page } from './coverageFixtures';

// The 3-D electorate. The orbital scene is read-only and draws the electorate; what
// changing the view or a parameter does to it is the contract here: the elected
// candidate and the Condorcet winner are ringed in the scene, the lens overlays live on
// the x–y plane, and the camera survives a trip to that plane.

async function openScene(page: Page) {
  await page.goto('/playground');
  await expect(page.locator('[data-testid="moment-electorate-panel"]')).toBeVisible();
  await page.locator('[data-testid="electorate-advanced-toggle"]').click();
  await page.locator('#pg-dims').selectOption('3');
  await page.locator('[data-testid="moment-method"]').click();
  await expect(page.locator('[data-testid="scene-3d"]')).toBeVisible();
}

test.describe('Playground — 3D scene', () => {
  test.beforeEach(async ({ page }) => openScene(page));

  test('rings the elected candidate, and the Condorcet winner under the criteria lens', async ({
    page,
  }) => {
    const crashes: string[] = [];
    page.on('pageerror', (err) => crashes.push(err.message));

    await expect(page.locator('[data-testid="scene-winner"]')).toBeAttached();
    // The Méthode moment opens on the criteria lens: pick the plain one explicitly.
    await page.locator('[data-testid="lens-winner"]').click();
    await expect(page.locator('[data-testid="scene-condorcet"]')).toHaveCount(0);

    await page.locator('[data-testid="lens-criteria"]').click();
    await expect(page.locator('[data-testid="scene-condorcet"]')).toBeAttached();
    // The matrix is not an x–y overlay: it is shown under the scene too.
    await expect(page.locator('[data-testid="criteria-matrix"]')).toBeVisible();
    expect(crashes).toEqual([]);
  });

  test('the lens overlay lives on the x–y plane, and the camera survives the trip', async ({
    page,
  }) => {
    const crashes: string[] = [];
    page.on('pageerror', (err) => crashes.push(err.message));

    await page.locator('[data-testid="scene-spin"]').click(); // pause the auto-spin
    const scene = page.locator('[data-testid="scene-3d"]');
    const box = (await scene.boundingBox())!;
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
    await page.mouse.down();
    await page.mouse.move(box.x + box.width / 2 + 120, box.y + box.height / 2 + 40, { steps: 5 });
    await page.mouse.up();
    const cx = () =>
      page.locator('[data-testid="scene-candidate-0"] circle').first().getAttribute('cx');
    // The last orbit move renders on a later frame than the mouse-up. Read the position only once it
    // has stopped changing: reading at once could catch the frame before it, and the camera that
    // comes back from the x–y plane is the final one (a ~1 in 20 flake on a loaded runner).
    let orbited = await cx();
    for (let i = 0; i < 30; i++) {
      await page.waitForTimeout(100);
      const next = await cx();
      if (next === orbited) break;
      orbited = next;
    }

    await page.locator('[data-testid="view-plane"]').click();
    await expect(scene).toBeHidden();
    await page.locator('[data-testid="lens-winner"]').click();
    await expect(page.locator('[data-testid="winregion"]')).toBeAttached();

    await page.locator('[data-testid="view-3d"]').click();
    await expect(scene).toBeVisible();
    expect(await cx()).toBe(orbited);
    expect(crashes).toEqual([]);
  });
});
