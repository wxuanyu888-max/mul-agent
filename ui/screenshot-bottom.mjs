import { chromium } from 'playwright';

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1920, height: 1080 });

  await page.goto('http://localhost:5182');

  // 点击 Token 标签
  await page.click('button[title="Token"]');
  await page.waitForTimeout(3000);

  // 滚动到页面底部
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(1000);

  // 截图
  await page.screenshot({
    path: '/tmp/token_usage_bottom.png',
    fullPage: true
  });

  console.log('截图已保存到 /tmp/token_usage_bottom.png');
  await browser.close();
})();
