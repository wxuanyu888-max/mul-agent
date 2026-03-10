import { test, expect } from "@playwright/test";

test.describe("Logs Viewer", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("should display Logs panel when clicked", async ({ page }) => {
    const logsButton = page.getByRole("button", { name: "Logs" });
    await logsButton.click();

    const header = page.locator("h1").filter({ hasText: "Logs" });
    await expect(header).toBeVisible();
  });

  test("should display logs content area", async ({ page }) => {
    const logsButton = page.getByRole("button", { name: "Logs" });
    await logsButton.click();

    // Check for logs container
    const logsContainer = page.locator("div.bg-white").first();
    await expect(logsContainer).toBeVisible();
  });
});
