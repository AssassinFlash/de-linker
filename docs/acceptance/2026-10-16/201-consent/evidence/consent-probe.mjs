// #201 measurement probe (docs/research/2026-10-16/consent-ga4-carrier.md).
// Usage: node .scratch/t201/consent-probe.mjs <url> <out.json> [--deny] [--no-click]
//
// What it records: every request that would reach Google, per phase, with the
// `gcs`/`gcd` parameters GA attaches; the loaded state of the gtag script
// (`type` attribute: `text/plain` means the blocker holds it); the cookies the
// two purposes write (_ga*, sbjs_*, cmplz_*, wp_consent_*); and the dataLayer
// as the page has built it.
//
// gtag.js itself is fetched for real (its consent handling is the upstream
// one); every measurement hit (the collect requests) is intercepted and
// recorded, never sent. CSP is bypassed only so the local instance behaves
// like production, whose CSP allows Google — the instances' CSP deliberately
// has no Google origin (tools/local/mu/000-linker-local-isolation.php).
import { writeFileSync } from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const require = createRequire(path.resolve('tests/e2e') + '/');
const { chromium } = require('playwright');

const [url, out] = process.argv.slice(2);
const deny = process.argv.includes('--deny');
const noClick = process.argv.includes('--no-click');
const browser = await chromium.launch();
const ctx = await browser.newContext({ bypassCSP: true, viewport: { width: 1440, height: 900 } });
const page = await ctx.newPage();

const log = [];
let phase = 'before-consent';
const google = /googletagmanager\.com|google-analytics\.com|analytics\.google\.com|doubleclick\.net/;
await ctx.route(google, async (route) => {
  const u = route.request().url();
  const entry = { phase, url: u, t: Date.now() };
  if (/gtag\/js/.test(u)) {
    entry.action = 'gtag.js fetched';
    log.push(entry);
    try {
      const resp = await route.fetch();
      return route.fulfill({ response: resp });
    } catch {
      return route.fulfill({ status: 200, contentType: 'text/javascript', body: '' });
    }
  }
  const q = new URL(u).searchParams;
  entry.action = 'collect';
  entry.gcs = q.get('gcs');
  entry.gcd = q.get('gcd');
  entry.en = q.get('en');
  entry.tid = q.get('tid');
  log.push(entry);
  return route.fulfill({ status: 204, body: '' });
});

const cookies = async () =>
  (await ctx.cookies()).map((c) => c.name).filter((n) => /^(sbjs_|_ga|_gid|_gcl|cmplz_|wp_consent)/.test(n)).sort();

const snap = {};
const snapshot = async () => ({
  cookies: await cookies(),
  gtagType: await page.evaluate(() => document.getElementById('google_gtagjs-js')?.getAttribute('type') ?? null),
  dataLayer: await page.evaluate(() => JSON.stringify(window.dataLayer ?? null)),
  consentDefaults: await page.evaluate(() => JSON.stringify((window.dataLayer ?? []).find((e) => e[0] === 'consent' && e[1] === 'default')?.[2] ?? null)),
  bannerVisible: await page.locator('.cmplz-cookiebanner').isVisible().catch(() => false),
  manageConsentVisible: await page.locator('.tv-footer-bar-legal .cmplz-manage-consent').isVisible().catch(() => false),
});

await page.goto(url, { waitUntil: 'networkidle' });
await page.waitForTimeout(3000);
snap.before = await snapshot();

if (!noClick) {
  phase = deny ? 'after-deny' : 'after-accept';
  await page.locator(deny ? '.cmplz-cookiebanner .cmplz-deny' : '.cmplz-cookiebanner .cmplz-accept').first().click();
  await page.waitForTimeout(4000);
  snap.afterChoice = await snapshot();

  phase = 'after-reload';
  await page.reload({ waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);
  snap.afterReload = await snapshot();

  if (!deny) {
    // The withdrawal path a visitor has: the site's own footer entry.
    phase = 'after-revoke-open';
    await page.locator('.tv-footer-bar-legal .cmplz-manage-consent').click();
    await page.waitForTimeout(1500);
    snap.revokeOpened = { bannerVisible: await page.locator('.cmplz-cookiebanner').isVisible().catch(() => false) };
    phase = 'after-revoke';
    await page.locator('.cmplz-cookiebanner .cmplz-deny').first().click();
    await page.waitForTimeout(3000);
    snap.afterRevoke = await snapshot();
    phase = 'after-revoke-reload';
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);
    snap.afterRevokeReload = await snapshot();
  }
  phase = 'after-reload2';
  await page.reload({ waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);
  snap.final = await snapshot();
}

writeFileSync(out, JSON.stringify({ url, snap, google: log }, null, 1));
console.log(JSON.stringify({
  snap: Object.fromEntries(Object.entries(snap).map(([k, v]) => [k, {
    cookies: v.cookies,
    gtagType: v.gtagType,
    bannerVisible: v.bannerVisible,
    manageConsentVisible: v.manageConsentVisible,
    consentDefaults: v.consentDefaults ? JSON.parse(v.consentDefaults) : null,
    bannerVisibleRevoke: v.bannerVisible,
  }])),
  google: log.map(({ phase: p, action, gcs, gcd, en }) => ({ phase: p, action, gcs, gcd, en })),
}, null, 1));
await browser.close();
