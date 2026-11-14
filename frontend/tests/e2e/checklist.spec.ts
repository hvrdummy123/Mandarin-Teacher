import { expect, test } from "@playwright/test";

/**
 * UI checklist. Prefers a running API on :8000; falls back to route mocks
 * so CI without keys still checks navigation and labels.
 */

test.describe("UI checklist", () => {
  test("rail labels are English and screens differ", async ({ page }) => {
    await page.route("**/api/topics", async (route) => {
      await route.fulfill({
        json: [
          {
            id: "restaurant",
            title_en: "Ordering at a restaurant",
            title_zh: "在餐厅点餐",
            ai_role: "waiter",
            scenario: "ordering",
            user_goal: "order food",
            keywords: ["菜单"],
            min_level: 5,
          },
        ],
      });
    });
    await page.route("**/api/progress", async (route) => {
      await route.fulfill({
        json: {
          xp_today: 0,
          daily_goal: 100,
          streak: 0,
          level: 10,
          tier: 1,
          note: "stub",
        },
      });
    });
    await page.route("**/api/words**", async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({ json: [] });
      } else {
        await route.fulfill({ json: { id: 1, word: "面", pinyin: "miàn", definition: "noodle", hsk_level: 1, context_sentence: null } });
      }
    });

    await page.goto("/");
    await expect(page.getByRole("button", { name: /Chat/ })).toBeVisible();
    await expect(page.getByRole("button", { name: /Topics/ })).toBeVisible();
    await expect(page.getByRole("button", { name: /Saved words/ })).toBeVisible();
    await expect(page.getByRole("button", { name: /Progress/ })).toBeVisible();

    await expect(page.getByText(/Free conversation at your level/)).toBeVisible();

    await page.getByRole("button", { name: /Topics/ }).click();
    await expect(page.getByText(/Pick a scenario/)).toBeVisible();
    await expect(page.getByText(/Ordering at a restaurant/)).toBeVisible();

    await page.getByRole("button", { name: /Saved words/ }).click();
    await expect(page.getByText(/No saved words yet/)).toBeVisible();

    await page.getByRole("button", { name: /Progress/ }).click();
    await expect(page.getByText(/XP today/)).toBeVisible();
    await expect(page.getByText(/placeholders/i)).toBeVisible();

    await page.getByRole("button", { name: /Hide Chinese labels/ }).click();
    await expect(page.getByRole("button", { name: /^Chat$/ })).toBeVisible();
  });

  test("mic is primary control on Chat", async ({ page }) => {
    await page.route("**/api/topics", (route) => route.fulfill({ json: [] }));
    await page.goto("/");
    await expect(page.getByRole("button", { name: /Hold to speak|Tap mic/i })).toBeVisible();
    await expect(page.getByPlaceholder(/fallback/i)).toBeVisible();
  });
});
