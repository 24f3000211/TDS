const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  let total = 0;

  for (let seed = 87; seed <= 96; seed++) {
    await page.goto(`https://sanand0.github.io/tdsdata/js_table/?seed=${seed}`);
    await page.waitForSelector("table");

    const nums = await page.$$eval("table td", tds =>
      tds
        .map(td => Number(td.textContent))
        .filter(n => !Number.isNaN(n))
    );

    total += nums.reduce((a, b) => a + b, 0);
  }

  console.log("TOTAL =", total);

  await browser.close();
})();
