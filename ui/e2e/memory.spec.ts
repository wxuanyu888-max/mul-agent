import { test, expect } from "@playwright/test";

test.describe("Memory Panel", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("should display Memory panel when clicked", async ({ page }) => {
    const memoryButton = page.getByRole("button", { name: "Memory" });
    await memoryButton.click();

    const header = page.locator("h1").filter({ hasText: "Memory" });
    await expect(header).toBeVisible();
  });

  test("should display memory content area", async ({ page }) => {
    const memoryButton = page.getByRole("button", { name: "Memory" });
    await memoryButton.click();

    // Check for memory container
    const memoryContainer = page.locator("div.bg-white").first();
    await expect(memoryContainer).toBeVisible();
  });
});
