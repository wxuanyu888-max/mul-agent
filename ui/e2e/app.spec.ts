import { test, expect } from "@playwright/test";

test.describe("Application Navigation", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    // Wait for app to fully load
    await page.waitForSelector("div.flex.h-screen");
  });

  test("should display the main app with sidebar", async ({ page }) => {
    // Check sidebar is visible
    const sidebar = page.locator("div.flex.h-screen").first();
    await expect(sidebar).toBeVisible();

    // Check logo text is visible
    const logoText = page.getByText("MUL");
    await expect(logoText).toBeVisible();
  });

  test("should display all navigation tabs", async ({ page }) => {
    // Wait for sidebar to be fully loaded
    await page.waitForSelector("nav");

    // Check all navigation items are present using exact matching
    const navItems = ["Chat", "Workflow", "Logs", "Memory", "Token"];

    for (const item of navItems) {
      const button = page.locator("nav").getByRole("button", { name: item, exact: true });
      await expect(button).toBeVisible();
    }
  });

  test("should switch to Chat tab when clicked", async ({ page }) => {
    // Wait for sidebar and click Chat button
    const nav = page.locator("nav");
    const chatButton = nav.getByRole("button", { name: "Chat", exact: true });
    await chatButton.click();

    // Check header updates to Chat
    const header = page.locator("h1").filter({ hasText: "Chat" });
    await expect(header).toBeVisible();
  });

  test("should switch to Workflow tab when clicked", async ({ page }) => {
    const nav = page.locator("nav");
    const workflowButton = nav.getByRole("button", { name: "Workflow", exact: true });
    await workflowButton.click();

    const header = page.locator("h1").filter({ hasText: "Workflow" });
    await expect(header).toBeVisible();
  });

  test("should switch to Logs tab when clicked", async ({ page }) => {
    const nav = page.locator("nav");
    const logsButton = nav.getByRole("button", { name: "Logs", exact: true });
    await logsButton.click();

    const header = page.locator("h1").filter({ hasText: "Logs" });
    await expect(header).toBeVisible();
  });

  test("should switch to Memory tab when clicked", async ({ page }) => {
    const nav = page.locator("nav");
    const memoryButton = nav.getByRole("button", { name: "Memory", exact: true });
    await memoryButton.click();

    const header = page.locator("h1").filter({ hasText: "Memory" });
    await expect(header).toBeVisible();
  });

  test("should switch to Token tab when clicked", async ({ page }) => {
    const nav = page.locator("nav");
    const tokenButton = nav.getByRole("button", { name: "Token", exact: true });
    await tokenButton.click();

    const header = page.locator("h1").filter({ hasText: "Token" });
    await expect(header).toBeVisible();
  });

  test("should highlight active tab", async ({ page }) => {
    // Wait for nav to load
    await page.waitForSelector("nav");

    // Chat is default tab - check the sidebar button has active styling
    const nav = page.locator("nav");
    const activeChatButton = nav.locator("button.bg-purple-100").first();
    await expect(activeChatButton).toBeVisible();

    // Click Workflow and check it becomes active
    const workflowButton = nav.getByRole("button", { name: "Workflow", exact: true });
    await workflowButton.click();
    await page.waitForTimeout(100);

    const activeWorkflowButton = nav.locator("button.bg-purple-100");
    await expect(activeWorkflowButton).toBeVisible();
  });
});
