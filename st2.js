const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  let total = 0;

  for (let seed = 55; seed <= 64; seed++) {
    const url = `https://sanand0.github.io/tdsdata/js_table/?seed=${seed}`;

    console.log("Visiting:", url);

    await page.goto(url, {
      waitUntil: "networkidle",
    });

    await page.waitForSelector("table");

    const pageSum = await page.$$eval("table td", (cells) =>
      cells.reduce((sum, cell) => {
        const n = Number(cell.textContent.trim());
        return Number.isFinite(n) ? sum + n : sum;
      }, 0)
    );

    console.log(`Seed ${seed}: ${pageSum}`);

    total += pageSum;
  }

  console.log("=================================");
  console.log("TOTAL =", total);
  console.log("=================================");

  await browser.close();
})();
