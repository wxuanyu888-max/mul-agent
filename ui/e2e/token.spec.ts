import { test, expect } from "@playwright/test";

test.describe("Token Usage Panel", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    // Wait for app to load
    await page.waitForSelector("nav");
  });

  test("should display Token panel when clicked", async ({ page }) => {
    const tokenButton = page.locator("nav").getByRole("button", { name: "Token" });
    await tokenButton.click();

    const header = page.locator("h1").filter({ hasText: "Token" });
    await expect(header).toBeVisible();
  });

  test("should display token usage content area", async ({ page }) => {
    const tokenButton = page.locator("nav").getByRole("button", { name: "Token" });
    await tokenButton.click();

    // Check for token container - look for the white card
    const tokenContainer = page.locator("div.bg-white").first();
    await expect(tokenContainer).toBeVisible();
  });

  test("should display token usage statistics table", async ({ page }) => {
    const tokenButton = page.locator("nav").getByRole("button", { name: "Token" });
    await tokenButton.click();

    // Wait for table to load
    await page.waitForSelector("table", { timeout: 10000 });

    // Check for the statistics table
    const table = page.locator("table").first();
    await expect(table).toBeVisible();
  });

  test("should display LLM call details section", async ({ page }) => {
    const tokenButton = page.locator("nav").getByRole("button", { name: "Token" });
    await tokenButton.click();

    // Wait for the LLM section header
    const llmHeader = page.locator("h3").filter({ hasText: "表 2" });
    await expect(llmHeader).toBeVisible();
  });

  test("should have refresh button for LLM logs", async ({ page }) => {
    const tokenButton = page.locator("nav").getByRole("button", { name: "Token" });
    await tokenButton.click();

    // Wait for and check for refresh button
    const refreshButton = page
      .locator("button")
      .filter({ hasText: "刷新" })
      .or(page.locator('[aria-label*="refresh" i]'));
    await expect(refreshButton.first()).toBeVisible({ timeout: 10000 });
  });

  test("should call token usage API when loading panel", async ({ page }) => {
    // Navigate to home first
    await page.goto("/");
    await page.waitForSelector("nav");

    // Set up request watcher BEFORE clicking
    const tokenRequestPromise = page.waitForRequest(
      (request) => request.url().includes("/api/v1/token-usage") && request.method() === "GET",
    );

    // Navigate to token panel
    const tokenButton = page.locator("nav").getByRole("button", { name: "Token" });
    await tokenButton.click();

    // Wait for API call
    const tokenRequest = await tokenRequestPromise;

    // Verify API was called
    expect(tokenRequest).toBeTruthy();
  });

  test("should display agent token usage data", async ({ page }) => {
    const tokenButton = page.locator("nav").getByRole("button", { name: "Token" });
    await tokenButton.click();

    // Wait for table
    await page.waitForSelector("table", { timeout: 10000 });

    // Should show agent names in the table (core_brain or wangyue)
    const agentCell = page.locator("td").filter({ hasText: /core_brain|wangyue/ });
    await expect(agentCell.first()).toBeVisible();
  });

  test("should display token counts in table", async ({ page }) => {
    const tokenButton = page.locator("nav").getByRole("button", { name: "Token" });
    await tokenButton.click();

    // Wait for table
    await page.waitForSelector("table", { timeout: 10000 });

    // Should show token count numbers in the table
    const table = page.locator("table").first();
    const numbers = table.locator("td").filter({ hasText: /\d+/ });
    await expect(numbers.first()).toBeVisible();
  });

  test("should load LLM logs when clicking refresh", async ({ page }) => {
    const tokenButton = page.locator("nav").getByRole("button", { name: "Token" });
    await tokenButton.click();

    // Wait for table first
    await page.waitForSelector("table", { timeout: 10000 });

    // Find and click refresh button - try multiple selectors
    const refreshButton = page.locator("button").filter({ hasText: "刷新" }).first();
    await refreshButton.click({ timeout: 10000 });

    // Should show loading state or data
    await page.waitForTimeout(2000);

    // Check for either the logs table or loading message
    const hasLogsOrLoading =
      (await page.locator("text=LLM 调用").count()) > 0 ||
      (await page.locator("text=正在加载").count()) > 0 ||
      (await page.locator("text=点击刷新").count()) > 0;

    expect(hasLogsOrLoading).toBeTruthy();
  });

  test("should show table structure", async ({ page }) => {
    const tokenButton = page.locator("nav").getByRole("button", { name: "Token" });
    await tokenButton.click();

    // Wait for data to load and check table has structure
    await page.waitForSelector("table", { timeout: 10000 });
    const table = page.locator("table").first();
    await expect(table).toBeVisible();
  });
});
