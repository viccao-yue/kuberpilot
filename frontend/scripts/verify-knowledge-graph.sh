#!/bin/sh
set -eu

VERIFY_URL="${VERIFY_URL:-http://127.0.0.1:4173/aiops/knowledge}"
TMP_ROOT="${TMPDIR:-/tmp}/kuberpilot-playwright"

mkdir -p "$TMP_ROOT"

if [ ! -f "$TMP_ROOT/package.json" ]; then
  (
    cd "$TMP_ROOT"
    npm init -y >/dev/null 2>&1
  )
fi

if [ ! -d "$TMP_ROOT/node_modules/playwright" ]; then
  (
    cd "$TMP_ROOT"
    npm install --no-save playwright@1.54.2 >/dev/null
  )
fi

(
  cd "$TMP_ROOT"
  VERIFY_URL="$VERIFY_URL" node <<'NODE'
const { chromium } = require('playwright');

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 960 } });
  const pageErrors = [];
  page.on('pageerror', (err) => pageErrors.push(String(err)));

  await page.goto(process.env.VERIFY_URL, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForTimeout(1800);

  const configTab = page.locator('.el-tabs__item').filter({ hasText: '图谱配置' }).first();
  const graphTab = page.locator('.el-tabs__item').filter({ hasText: '图谱视图' }).first();

  let tabSwitchOk = false;
  if (await configTab.count()) {
    await configTab.click();
    await page.waitForTimeout(500);
    await graphTab.click();
    await page.waitForTimeout(800);
    tabSwitchOk = true;
  }

  const result = {
    url: page.url(),
    titleVisible: await page.locator('h2').filter({ hasText: '知识图谱' }).count() > 0,
    graphPanelVisible: await page.locator('.graph-panel').count() > 0,
    sidePanelVisible: await page.locator('.side-panel').count() > 0,
    configTabVisible: await configTab.count() > 0,
    graphNodeCount: await page.locator('.board-node').count(),
    emptyStateVisible: await page.locator('.graph-empty').count() > 0,
    tabSwitchOk,
    pageErrors,
  };

  console.log(JSON.stringify(result, null, 2));
  await browser.close();

  const requiredChecks = [
    result.titleVisible,
    result.graphPanelVisible,
    result.sidePanelVisible,
    result.configTabVisible,
    result.tabSwitchOk,
    result.pageErrors.length === 0,
    result.graphNodeCount > 0 || result.emptyStateVisible,
  ];

  if (requiredChecks.some((item) => !item)) {
    process.exit(1);
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
NODE
)
