// 五段终审 reviewer's own probes: A (contact CTA), D (All products active weight),
// C (phase/power facet order), E (PDP 390 five items), F (DE SKU label).
// Same chromium channel as the capture protocol.
import { createRequire } from 'node:module';
import path from 'node:path';
import fs from 'node:fs';
const repo = '/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-t16';
const { chromium } = createRequire(path.join(repo, 'plugins/linker-tools/package.json'))('playwright');
const browser = await chromium.launch({ channel: 'chromium' });
const out = {};

const CAT = [
  ['shop-en', 'https://de-linker.com/products/', 'http://127.0.0.1:8924/products/'],
  ['archive-en', 'https://de-linker.com/product-category/inverters/', 'http://127.0.0.1:8924/product-category/inverters/'],
  ['shop-de', 'https://de-linker.com/de/produkte/', 'http://127.0.0.1:8924/de/produkte/'],
  ['archive-de', 'https://de-linker.com/de/produkt-kategorie/wechselrichter/', 'http://127.0.0.1:8924/de/produkt-kategorie/wechselrichter/'],
];

// ---- A + D + C on the four catalogue pages at 1440 ----
for (const [key, liveUrl, t16Url] of CAT) {
  out[key] = {};
  for (const [side, url] of [['live', liveUrl], ['t16', t16Url]]) {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await ctx.newPage();
    await page.goto(url + (url.includes('?') ? '&' : '?') + 'cbq=' + Date.now(), { waitUntil: 'domcontentloaded', timeout: 90000 });
    await page.waitForTimeout(2500);
    out[key][side] = await page.evaluate(() => {
      const rect = (el) => { if (!el) return null; const r = el.getBoundingClientRect(); return [+r.x.toFixed(1), +(r.y + scrollY).toFixed(1), +r.width.toFixed(2), +r.height.toFixed(2)]; };
      const band = document.querySelector('.linker-contact-invitation');
      const cta = band && band.querySelector('.linker-contact-primary, a[class*="primary"]');
      const mail = band && band.querySelector('.linker-contact-email, a[href^="mailto"]');
      const c = (el, p) => el ? getComputedStyle(el).getPropertyValue(p) : null;
      // rail
      const rail = document.querySelector('.sidebar-filters, .rail');
      const sections = {};
      if (rail) for (const s of rail.querySelectorAll('details')) {
        const t = (s.querySelector(':scope > summary')?.textContent || '').trim();
        if (/^(Phase|Power|Leistung)$/.test(t)) {
          sections[t] = [...s.querySelectorAll('.filter-option')].map((o) => {
            const lab = (o.querySelector('.filter-label, span')?.textContent || o.textContent).trim().replace(/\s+/g, ' ');
            const cnt = o.querySelector('.filter-count')?.textContent.trim() ?? null;
            return [lab, cnt];
          });
        }
      }
      // all-products row
      let allRow = null;
      if (rail) {
        for (const a of rail.querySelectorAll('a')) {
          const t = a.textContent.trim();
          if (/^(All products|Alle Produkte|Alle Modelle)$/.test(t)) {
            allRow = { text: t, aria: a.getAttribute('aria-current'), fw: getComputedStyle(a).fontWeight, cls: a.className };
            break;
          }
        }
      }
      // current category row too (archive)
      let curRow = null;
      if (rail) {
        const a = rail.querySelector('a[aria-current="page"]:not(:first-of-type)');
        if (a) curRow = { text: a.textContent.trim().slice(0, 30), fw: getComputedStyle(a).fontWeight };
      }
      return {
        contact: band ? {
          rect: rect(band),
          ctaText: cta?.textContent.trim().slice(0, 40) ?? null,
          ctaColor: c(cta, 'color'), ctaBg: c(cta, 'background-color'),
          mailColor: c(mail, 'color'), mailDeco: c(mail, 'text-decoration-line'), mailText: mail?.textContent.trim().slice(0, 30) ?? null,
        } : null,
        allRow, curRow, sections,
      };
    });
    await ctx.close();
  }
}

// ---- E: PDP 390 (EN) ----
out['pdp-390'] = {};
for (const [side, url] of [
  ['live', 'https://de-linker.com/product/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/'],
  ['t16', 'http://127.0.0.1:8924/product/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/'],
]) {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await ctx.newPage();
  await page.goto(url + '?cbq=' + Date.now(), { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForTimeout(2500);
  out['pdp-390'][side] = await page.evaluate(() => {
    const rect = (el) => { if (!el) return null; const r = el.getBoundingClientRect(); return [+r.x.toFixed(1), +(r.y + scrollY).toFixed(1), +r.width.toFixed(1), +r.height.toFixed(1)]; };
    const q = (s) => document.querySelector(s);
    const c = (el, p) => el ? getComputedStyle(el).getPropertyValue(p) : null;
    const tabs = q('.pdp-info-tabs');
    const tabEls = tabs ? [...tabs.children] : [];
    const ov = q('.pdp-overview');
    const copy = q('.pdp-overview-copy');
    const main = q('.pdp-gallery-main');
    const dark = q('.pdp-btn-dark');
    return {
      tabsFlexWrap: c(tabs, 'flex-wrap'),
      tabRows: [...new Set(tabEls.map((t) => Math.round(t.getBoundingClientRect().top)))].length,
      tabs: tabEls.map((t) => ({ text: t.textContent.trim().slice(0, 20), rect: rect(t), flex: c(t, 'flex') })),
      overviewRect: rect(ov),
      copyRect: rect(copy),
      copyDeltaFromCardTop: copy && ov ? +(copy.getBoundingClientRect().top - ov.getBoundingClientRect().top).toFixed(1) : null,
      firstCopyChild: copy?.firstElementChild?.tagName + '.' + (copy?.firstElementChild?.className || ''),
      heroMain: main ? { rect: rect(main), blend: c(main, 'mix-blend-mode'), src: (main.currentSrc || '').split('/').pop(), natural: [main.naturalWidth, main.naturalHeight], srcsetAttr: main.getAttribute('srcset') } : null,
      heroWrapRect: rect(q('.pdp-gallery-main-wrap')),
      hero: { brand: rect(q('.pdp-brand')), h1: rect(q('.pdp-h1')), designation: rect(q('.pdp-designation')), sku: rect(q('.pdp-sku')), gallery: rect(q('.pdp-gallery')), thumbs: rect(q('.pdp-thumbs')) },
      btnDark: dark ? { text: dark.textContent.trim().slice(0, 30), bg: c(dark, 'background-color'), color: c(dark, 'color') } : null,
      pageH: document.documentElement.scrollHeight,
    };
  });
  await ctx.close();
}

// ---- F: PDP DE at 1440 ----
out['pdp-de'] = {};
for (const [side, url] of [
  ['live', 'https://de-linker.com/de/produkt/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/'],
  ['t16', 'http://127.0.0.1:8924/de/produkt/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/'],
]) {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  await page.goto(url + '?cbq=' + Date.now(), { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForTimeout(2000);
  out['pdp-de'][side] = await page.evaluate(() => {
    const sku = document.querySelector('.pdp-sku');
    const doc = document.documentElement.lang;
    return { skuText: sku?.textContent.trim() ?? null, lang: doc, title: document.title.slice(0, 60) };
  });
  await ctx.close();
}

await browser.close();
fs.writeFileSync(process.argv[2] || 'probe-v5.json', JSON.stringify(out, null, 1));
console.log(JSON.stringify(out, null, 1));
