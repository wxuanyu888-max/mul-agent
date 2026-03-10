import { test, expect } from "@playwright/test";

test.describe("Chat Functionality", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    // Wait for chat to fully load
    await page.waitForSelector('textarea[placeholder*="Type your message"]');
  });

  test("should display chat interface", async ({ page }) => {
    // Check chat header - use the h1 element
    await expect(page.locator("h1").filter({ hasText: "Chat" })).toBeVisible();

    // Check message area exists
    const messageArea = page.locator("div.flex-1.overflow-y-auto");
    await expect(messageArea).toBeVisible();
  });

  test("should display empty state when no messages", async ({ page }) => {
    // Check for empty state message
    const emptyState = page.locator("p").filter({ hasText: "No messages yet" });
    await expect(emptyState).toBeVisible();
  });

  test("should allow typing in message input", async ({ page }) => {
    const textarea = page.locator('textarea[placeholder*="Type your message"]');
    await textarea.fill("Hello, this is a test message");
    await expect(textarea).toHaveValue("Hello, this is a test message");
  });

  test("should send a message and display it", async ({ page }) => {
    const textarea = page.locator('textarea[placeholder*="Type your message"]');
    const sendButton = page.getByRole("button", { name: "Send" });

    // Type and send message
    await textarea.fill("Test message");
    await sendButton.click();

    // Check user message appears
    const userMessage = page
      .locator("div.flex.flex-row-reverse")
      .filter({ hasText: "Test message" });
    await expect(userMessage).toBeVisible();
  });

  test("should show loading state while waiting for response", async ({ page }) => {
    const textarea = page.locator('textarea[placeholder*="Type your message"]');
    const sendButton = page.getByRole("button", { name: "Send" });

    await textarea.fill("Test message");
    await sendButton.click();

    // Loading indicator should appear briefly
    const loadingIndicator = page.locator("span").filter({ hasText: "Agent is thinking..." });
    // Note: This might disappear quickly, so we just check it exists at some point
    await expect(loadingIndicator).toBeVisible({ timeout: 5000 });
  });

  test("should display agent selector", async ({ page }) => {
    const agentSelector = page.locator("select").first();
    await expect(agentSelector).toBeVisible();
  });

  test("should have clear chat button", async ({ page }) => {
    const clearButton = page.locator('button[title="Clear chat"]');
    await expect(clearButton).toBeVisible();
  });

  test("should have refresh button", async ({ page }) => {
    const refreshButton = page.locator('button[title="Refresh"]');
    await expect(refreshButton).toBeVisible();
  });

  test("should display API error when backend is unavailable", async ({ page }) => {
    // This test assumes the backend might be unavailable
    const textarea = page.locator('textarea[placeholder*="Type your message"]');
    const sendButton = page.getByRole("button", { name: "Send" });

    await textarea.fill("Test message");
    await sendButton.click();

    // Either we get a response or an error message
    const errorMessage = page.locator("div").filter({ hasText: "Error: Failed to get response" });
    const assistantMessage = page
      .locator("div.bg-white")
      .filter({ hasText: /Test message/ })
      .last();

    // Wait for either response or error
    await expect(errorMessage.or(assistantMessage)).toBeVisible({ timeout: 10000 });
  });
});

test.describe("Chat API Integration", () => {
  test("should load chat history on page load", async ({ page }) => {
    await page.goto("/");

    // Wait for history to load (check for either messages or empty state)
    const messageArea = page.locator("div.flex-1.overflow-y-auto");
    await expect(messageArea).toBeVisible();
  });

  test("should load agents list", async ({ page }) => {
    await page.goto("/");

    // Wait for agents to load and populate selector
    const agentSelector = page.locator("select").first();
    await expect(agentSelector).toBeVisible();
  });
});
