/**
 * Compiles the WindPress cache headless: the WindPress compiler is the
 * plugin's own browser-side JS bundles (Tailwind v4 has no server build),
 * but those bundles are plain ES modules — they run in Node once a `fetch`
 * that serves their `file://` WASM loads from disk is installed. This script
 * replays what the admin's Generate worker does, call for call:
 *
 *   login → scrape the WindPress admin metadata (REST url + nonce)
 *   → GET admin/settings/cache/providers + cache/index + admin/volume/index
 *   → POST admin/settings/cache/providers/scan (paged, per enabled provider)
 *   → download the compiler bundles from the plugin's public assets URL
 *   → compile() → getCandidates() → build() → optimize()  (the same exports
 *     the worker imports)
 *   → POST admin/settings/cache/store  (the same route the worker stores
 *     through; the REST nonce + session cookie are what its permission
 *     callback accepts — an application password alone is rejected)
 *
 * The stored CSS is verified the way `tools/windpress-compile.mjs` and the
 * deploy guard verify it: the REST answer's `cache.last_generated` must be
 * newer than the one before, and the cache file's body — everything after
 * the header comment the store route stamps with the generation time — must
 * hash identically when the inputs did not change.
 *
 * Usage:
 *   node tools/windpress-node-compile.mjs <site-url> \
 *     [--credentials <file>] [--cache-dir <dir>] [--refresh-bundles] [--dry-run]
 *
 * Credentials: `username:` / `password:` lines (the wp-admin.txt format), or
 * the WINDPRESS_COMPILE_USER / WINDPRESS_COMPILE_PASS environment variables.
 * Secrets are never printed.
 */

import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { register } from 'node:module';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const scriptName = path.basename(fileURLToPath(import.meta.url));

// Shared hosting closes an occasional connection; the bundle downloads are
// plain static files, so a short retry is safe and keeps a run from dying on
// one dropped socket.
async function fetchRetry(url, attempts = 3) {
  let lastError;
  for (let attempt = 0; attempt < attempts; attempt++) {
    try {
      const response = await fetch(url);
      if (response.status >= 500 && attempt < attempts - 1) continue;
      return response;
    } catch (error) {
      lastError = error;
      await new Promise((resolve) => setTimeout(resolve, 500 * (attempt + 1)));
    }
  }
  throw lastError;
}

// The WindPress metadata script the admin page prints; `var windpress = …`
// holds the REST root, the nonce, the plugin version and the assets base.
const METADATA_SCRIPT = /<script id="windpress:metadata">\s*var windpress = (\{.*?\});?\s*<\/script>/s;
const ASSET_NAME = /[A-Za-z0-9_.-]+-[A-Za-z0-9_$.-]+\.(?:js|wasm)/g;
const RELATIVE_IMPORT = /(?:from|import)\s*\(?\s*["'`]([^"'`]+\.js)["'`]/g;

const args = process.argv.slice(2);
const siteArg = args.find((a) => !a.startsWith('--'));
const option = (name) => {
  const hit = args.find((a) => a.startsWith(`--${name}=`));
  return hit ? hit.slice(name.length + 3) : null;
};

/** username:/password: lines → { username, password } (the wp-admin.txt format). */
export function parseCredentials(text) {
  const fields = {};
  for (const line of String(text).split('\n')) {
    const match = /^([A-Za-z0-9_-]+)\s*:\s*(.*)$/.exec(line);
    if (match) fields[match[1]] = match[2].trim();
  }
  return fields;
}

/**
 * The worker's HTML-entity decode: the entity list hard-coded in its bundle
 * plus numeric character references (decimal and hex).
 */
export function decodeEntities(text) {
  const entities = { '&amp;': '&', '&lt;': '<', '&gt;': '>', '&quot;': '"', '&#39;': "'", '&apos;': "'", '&nbsp;': ' ' };
  return String(text)
    .replace(/&(amp|lt|gt|quot|apos|nbsp);/g, (m) => entities[m])
    .replace(/&#(\d+);/g, (m, code) => (Number(code) <= 0x10ffff ? String.fromCodePoint(Number(code)) : m))
    .replace(/&#x([0-9a-f]+);/gi, (m, code) => (parseInt(code, 16) <= 0x10ffff ? String.fromCodePoint(parseInt(code, 16)) : m));
}

const yamlScalar = (value) => {
  if (value === null || value === undefined) return 'null';
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  const s = String(value);
  if (s === '') return "''";
  // Plain unless it would parse as something else or trip YAML syntax.
  if (/^(?:~|null|true|false|yes|no|on|off)$/i.test(s)) return `'${s}'`;
  if (/^\d+(?:\.\d+)?$/.test(s)) return `'${s}'`;
  if (/^[\s&*!|>'"%@`{}[\],#-]|[:?\s]$|[:#]\s|\n/.test(s)) {
    return `'${s.replace(/'/g, "''")}'`;
  }
  return s;
};

/** The worker stringifies JSON-typed provider contents to YAML before scanning. */
export function toYaml(value, level = 0) {
  const indent = ' '.repeat(level * 2);
  if (Array.isArray(value)) {
    if (value.length === 0) return '[]';
    return value.map((item) => {
      const rendered = toYaml(item, level + 1);
      const first = rendered.split('\n')[0];
      const rest = rendered.split('\n').slice(1);
      return `${indent}- ${first}${rest.length ? '\n' + rest.join('\n') : ''}`;
    }).join('\n');
  }
  if (value && typeof value === 'object') {
    const keys = Object.keys(value);
    if (keys.length === 0) return '{}';
    return keys.map((key) => {
      const item = value[key];
      const nested = toYaml(item, level + 1);
      if (typeof item === 'object' && item !== null && ((Array.isArray(item) && item.length) || (!Array.isArray(item) && Object.keys(item).length))) {
        return `${indent}${yamlScalar(key)}:\n${nested}`;
      }
      return `${indent}${yamlScalar(key)}: ${nested}`;
    }).join('\n');
  }
  return yamlScalar(value);
}

/**
 * Provider contents as the worker feeds them to the scanner: base64-decode,
 * JSON-typed contents stringify to YAML, then entity-decode.
 */
export function decodeProviderContents(contents) {
  return contents.map((entry) => {
    let text = Buffer.from(entry.content, 'base64').toString('utf8');
    if (entry.type === 'json') text = toYaml(JSON.parse(text));
    return decodeEntities(text);
  });
}

/** Volume entries → the virtual CSS file map `compile({ volume })` takes. */
export function volumeMap(entries) {
  const map = {};
  for (const entry of entries) {
    if (!entry.directory) map[`/${entry.relative_path}`] = entry.content;
  }
  return map;
}

async function login(site, username, password) {
  const probe = await fetch(`${site}/wp-login.php`);
  const testCookie = probe.headers.getSetCookie().map((c) => c.split(';')[0]).join('; ');
  const response = await fetch(`${site}/wp-login.php`, {
    method: 'POST',
    headers: {
      'content-type': 'application/x-www-form-urlencoded',
      cookie: `${testCookie}; wordpress_test_cookie=Cookie%20check`,
    },
    body: new URLSearchParams({
      log: username,
      pwd: password,
      'wp-submit': 'Log In',
      redirect_to: `${site}/wp-admin/`,
      testcookie: '1',
    }),
    redirect: 'manual',
  });
  const location = response.headers.get('location') || '';
  if (!location.includes('/wp-admin/')) {
    throw new Error(`the login did not reach wp-admin (HTTP ${response.status})`);
  }
  const cookies = response.headers.getSetCookie().map((c) => c.split(';')[0]);
  return { cookieHeader: [...new Set([...cookies, ...testCookie.split('; ')])].join('; ') };
}

async function fetchWindpressMetadata(site, cookieHeader) {
  const page = await fetch(`${site}/wp-admin/admin.php?page=windpress`, { headers: { cookie: cookieHeader } });
  const html = await page.text();
  const match = METADATA_SCRIPT.exec(html);
  if (!match) throw new Error(`the WindPress admin page carries no metadata script (HTTP ${page.status})`);
  const metadata = JSON.parse(match[1]);
  const entryScript = /<script type="module" id="windpress-admin-js" src="([^"]+)"/.exec(html);
  return { metadata, entryScriptUrl: entryScript ? new URL(entryScript[1], `${site}/`).href : null };
}

/** Downloads the compiler bundle set: entry file, its imports, and the WASM files. */
async function downloadCompilerBundles({ entryScriptUrl, cacheRoot, version, refresh = false }) {
  const discover = async (url) => (await fetchRetry(url)).text();
  // The bundles live next to the admin entry module (…/assets/dist/assets/),
  // one level below the metadata's assets.url.
  const moduleDir = entryScriptUrl ? entryScriptUrl.slice(0, entryScriptUrl.lastIndexOf('/') + 1) : null;
  let entryUrl = null;
  if (moduleDir) {
    const dashboard = await discover(entryScriptUrl);
    const tailwind = [...dashboard.matchAll(/(tailwindcss-[A-Za-z0-9_$.-]+\.js)/g)].map((m) => m[1]);
    if (tailwind.length) {
      entryUrl = new URL(tailwind[0], moduleDir).href;
    } else {
      for (const name of [...dashboard.matchAll(/(worker-[A-Za-z0-9_$.-]+\.js)/g)].map((m) => m[1])) {
        const workerSource = await discover(new URL(name, moduleDir).href);
        const inWorker = [...workerSource.matchAll(/(tailwindcss-[A-Za-z0-9_$.-]+\.js)/g)].map((m) => m[1]);
        if (inWorker.length) { entryUrl = new URL(inWorker[0], moduleDir).href; break; }
      }
    }
  }
  if (!entryUrl) throw new Error('could not find the compiler entry bundle (no tailwindcss-*.js in the dashboard or worker)');

  const dir = path.join(cacheRoot, `windpress-compiler-v${version}`);
  mkdirSync(cacheRoot, { recursive: true });
  // One version dir at a time: older plugin versions' bundles are dead weight.
  for (const sibling of readdirSync(cacheRoot)) {
    if (sibling !== path.basename(dir)) rmSync(path.join(cacheRoot, sibling), { recursive: true, force: true });
  }
  if (!refresh && existsSync(path.join(dir, entryUrl.split('/').pop()))) {
    return { dir, entry: entryUrl.split('/').pop(), files: [], cached: true };
  }
  rmSync(dir, { recursive: true, force: true });
  mkdirSync(dir, { recursive: true });

  const seen = new Set();
  const queue = [entryUrl];
  const files = [];
  while (queue.length) {
    const url = queue.shift();
    const name = url.split('/').pop();
    if (seen.has(name)) continue;
    seen.add(name);
    const response = await fetchRetry(url);
    if (!response.ok) throw new Error(`downloading ${name} answered HTTP ${response.status}`);
    const bytes = Buffer.from(await response.arrayBuffer());
    writeFileSync(path.join(dir, name), bytes);
    files.push({ name, bytes: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex').slice(0, 12) });
    const text = bytes.toString('utf8');
    for (const match of text.matchAll(RELATIVE_IMPORT)) {
      if (match[1].startsWith('.')) queue.push(new URL(match[1], url).href);
    }
    for (const match of text.matchAll(ASSET_NAME)) {
      if (match[0].endsWith('.wasm')) queue.push(new URL(match[0], url).href);
    }
  }
  return { dir, entry: entryUrl.split('/').pop(), files };
}

async function main() {
  if (!siteArg) {
    console.error(`usage: node tools/${scriptName} <site-url> [--credentials <file>] [--cache-dir <dir>] [--refresh-bundles] [--dry-run]`);
    process.exit(2);
  }
  const site = siteArg.replace(/\/+$/, '');
  const dryRun = args.includes('--dry-run');
  const credentialsFile =
    option('credentials') ?? (existsSync(`${process.env.HOME}/Downloads/wp-admin.txt`) ? `${process.env.HOME}/Downloads/wp-admin.txt` : null);
  const fields = { ...parseCredentials(credentialsFile ? readFileSync(credentialsFile, 'utf8') : ''), ...cleanEnv() };
  if (!fields.username || !fields.password) {
    throw new Error('no credentials: pass --credentials <file> or WINDPRESS_COMPILE_USER / WINDPRESS_COMPILE_PASS');
  }
  const startedAt = Date.now();

  const { cookieHeader } = await login(site, fields.username, fields.password);
  const { metadata, entryScriptUrl } = await fetchWindpressMetadata(site, cookieHeader);
  const restUrl = metadata.rest_api.url;
  const nonce = metadata.rest_api.nonce;
  const api = async (route, init = {}) => {
    const response = await fetch(`${restUrl}/${route}`, {
      ...init,
      headers: { 'X-WP-Nonce': nonce, 'content-type': 'application/json', cookie: cookieHeader, ...(init.headers || {}) },
    });
    const body = await response.json().catch(() => null);
    if (!response.ok) throw new Error(`${route} answered HTTP ${response.status}: ${JSON.stringify(body).slice(0, 200)}`);
    return body;
  };

  const providers = (await api('admin/settings/cache/providers')).providers.filter((p) => p.enabled);
  const cacheBefore = (await api('admin/settings/cache/index')).cache;
  const volume = volumeMap((await api('admin/volume/index')).entries);
  const options = (await api('admin/settings/options/index')).options || {};
  const get = (object, dotted, fallback) => dotted.split('.').reduce((acc, key) => (acc && acc[key] !== undefined ? acc[key] : undefined), object) ?? fallback;
  let tailwindVersion = Number(get(options, 'general.tailwindcss.version', 4));
  let sourcemap = Boolean(get(options, 'performance.cache.source_map', false));
  if (tailwindVersion !== 3 && tailwindVersion !== 4) { tailwindVersion = 4; sourcemap = false; }
  if (tailwindVersion !== 4) throw new Error(`this compile path implements Tailwind v4; the site asks for v${tailwindVersion}`);

  // Provider scans: paged POSTs until next_batch is false, exactly like the worker.
  const contents = [];
  for (const provider of providers) {
    let batch = false;
    do {
      const scanned = await api('admin/settings/cache/providers/scan', {
        method: 'POST',
        body: JSON.stringify({ provider_id: provider.id, metadata: { next_batch: batch } }),
      });
      contents.push(...scanned.contents);
      batch = scanned.metadata?.next_batch || false;
    } while (batch !== false);
  }
  const scanned = decodeProviderContents(contents);

  const cacheRoot = option('cache-dir') ?? `${process.env.HOME}/.cache/de-linker`;
  const { dir, entry, files, cached } = await downloadCompilerBundles({
    entryScriptUrl,
    cacheRoot,
    version: metadata._version,
    refresh: args.includes('--refresh-bundles'),
  });

  // The browser loaders fetch their WASM relative to the module URL; from
// disk that is a file:// URL, which Node's fetch refuses — serve it. The
  // compiler also resolves bare CSS imports (`@import "preline/variants.css"`)
  // from the esm.sh CDN exactly like the browser build does, and a dropped
  // socket there fails the whole compile, so GETs retry briefly.
  const realFetch = globalThis.fetch.bind(globalThis);
  globalThis.fetch = async (input, init) => {
    const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input?.url;
    if (url && url.startsWith('file:')) {
      return new Response(readFileSync(fileURLToPath(url)), { headers: { 'content-type': 'application/wasm' } });
    }
    const method = (init?.method || input?.method || 'GET').toUpperCase();
    if (method !== 'GET') return realFetch(input, init);
    let lastError;
    for (let attempt = 0; attempt < 3; attempt++) {
      try {
        const response = await realFetch(input, init);
        if (response.status >= 500 && attempt < 2) continue;
        return response;
      } catch (error) {
        lastError = error;
      }
    }
    throw lastError;
  };
  // loadSource() reads its REST base from window.windpress, like in the
  // browser; the preload helper dispatches onto window on load errors, so the
  // shim is an EventTarget rather than a bare object.
  globalThis.window = Object.assign(Object.create(EventTarget.prototype), {
    windpress: { rest_api: { url: restUrl, nonce } },
  });
  // A volume may pin remote Tailwind plugins (`@plugin "https://esm.sh/…"`),
  // which the compiler loads by dynamic import; Node needs a loader hook to
  // import https: modules the way the browser does.
  const httpsLoader = `
    export async function resolve(specifier, context, next) {
      if (specifier.startsWith('https://')) return { url: specifier, shortCircuit: true };
      return next(specifier, context);
    }
    export async function load(url, context, next) {
      if (url.startsWith('https://')) {
        const response = await fetch(url);
        if (!response.ok) throw new Error('https loader: ' + url + ' answered HTTP ' + response.status);
        return { format: 'module', source: await response.text(), shortCircuit: true };
      }
      return next(url, context);
    }
  `;
  register(`data:text/javascript;base64,${Buffer.from(httpsLoader).toString('base64')}`);

  const compiler = await import(pathToFileURL(path.join(dir, entry)).href);
  const result = await compiler.compile({ entrypoint: '/main.css', volume });
  const extraSources = result.sources?.length ? await compiler.loadSource(result.sources) : [];
  const candidates = await compiler.getCandidates([...scanned, ...extraSources]);
  const css = result.build(candidates);
  const normal = await compiler.optimize(css, { file: 'main.css', map: sourcemap ? result.buildSourceMap() : undefined });
  const minified = await compiler.optimize(css, { file: 'main.css', map: sourcemap ? result.buildSourceMap() : undefined, minify: true });
  const content = sourcemap ? normal.code : minified.code;

  // The store route stamps a generation-time header line onto the file, so
  // the identity check hashes everything after that first line.
  const bodySha256 = (text) => createHash('sha256').update(text.split('\n').slice(1).join('\n')).digest('hex');
  const cachedBefore = cacheBefore.file_url ? await (await realFetch(cacheBefore.file_url)).text() : null;

  if (dryRun) {
    console.log(JSON.stringify({
      compiled: true,
      dry_run: true,
      providers: providers.length,
      volume_files: Object.keys(volume).length,
      scanned_sources: scanned.length,
      candidates: candidates.length,
      css_bytes: Buffer.byteLength(content),
      cache_before: cacheBefore,
      bundles: files.length,
      bundles_cached: cached,
    }));
    return;
  }

  const stored = await api('admin/settings/cache/store', {
    method: 'POST',
    body: JSON.stringify({
      content: Buffer.from(content, 'utf8').toString('base64'),
      sourcemap: sourcemap ? Buffer.from(normal.map ?? '', 'utf8').toString('base64') : null,
      full_build: Date.now(),
    }),
  });
  const cacheAfter = stored.cache;
  if (!Number.isFinite(cacheAfter.last_generated) || cacheAfter.last_generated <= (cacheBefore.last_generated ?? 0)) {
    throw new Error(`the stored cache is not newer (before ${cacheBefore.last_generated}, stored ${cacheAfter?.last_generated})`);
  }
  const cachedAfter = await (await realFetch(cacheAfter.file_url)).text();
  const identical = cachedBefore !== null && bodySha256(cachedBefore) === bodySha256(cachedAfter);

  console.log(JSON.stringify({
    compiled: true,
    plugin: metadata._version,
    providers: providers.length,
    volume_files: Object.keys(volume).length,
    candidates: candidates.length,
    last_generated: cacheAfter.last_generated,
    file_size: cacheAfter.file_size,
    body_identical_to_before: identical,
    before_body_sha256: cachedBefore !== null ? bodySha256(cachedBefore) : null,
    after_body_sha256: bodySha256(cachedAfter),
    bundles: files.length,
    bundles_cached: cached,
    ms: Date.now() - startedAt,
  }));
}

function cleanEnv() {
  const fields = {};
  if (process.env.WINDPRESS_COMPILE_USER) fields.username = process.env.WINDPRESS_COMPILE_USER;
  if (process.env.WINDPRESS_COMPILE_PASS) fields.password = process.env.WINDPRESS_COMPILE_PASS;
  return fields;
}

const invokedDirectly = process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;
if (invokedDirectly) {
  main().catch((error) => {
    const cause = error?.cause ? ` (cause: ${error.cause.message ?? error.cause})` : '';
    console.error(`${scriptName} failed: ${error instanceof Error ? error.message : error}${cause}`);
    if (process.env.WINDPRESS_COMPILE_DEBUG) console.error(error?.stack);
    process.exitCode = 1;
  });
}
