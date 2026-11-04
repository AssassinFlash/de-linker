// The headless WindPress compile's input/output contract: the pure transforms
// tools/windpress-node-compile.mjs applies between the WindPress REST answers
// and the compiler entry points. The compile itself talks to a live site (and
// the site's own compiler bundles), so it is exercised by the production run,
// not here. Run: node --test tools/windpress-node-compile.test.mjs
import assert from 'node:assert/strict';
import { test } from 'node:test';

const tool = await import('./windpress-node-compile.mjs');

test('parseCredentials reads the wp-admin.txt key/value format', () => {
  assert.deepEqual(
    tool.parseCredentials('# comment\nusername: alice\npassword: s3cret\n'),
    { username: 'alice', password: 's3cret' }
  );
  assert.deepEqual(tool.parseCredentials(''), {});
});

test('decodeEntities covers the worker bundle entity list and numeric refs', () => {
  assert.equal(tool.decodeEntities('a&amp;b&lt;c&gt;d&quot;e&#39;f&nbsp;'), 'a&b<c>d"e\'f\u00a0');
  assert.equal(tool.decodeEntities('&#8364; &#x20ac;'), '€ €');
  assert.equal(tool.decodeEntities('plain text'), 'plain text');
});

test('toYaml renders JSON data the way the worker stringifies it', () => {
  assert.equal(tool.toYaml({ version: 3, name: 'twentytwentyfive' }), 'version: 3\nname: twentytwentyfive');
  assert.equal(tool.toYaml(['a', 'b']), '- a\n- b');
  assert.equal(tool.toYaml({ nested: { k: 'v' } }), 'nested:\n  k: v');
  assert.equal(tool.toYaml({ empty: [] }), 'empty: []');
  assert.equal(tool.toYaml({ quoted: 'true' }), "quoted: 'true'");
  assert.equal(tool.toYaml(null), 'null');
});

test('decodeProviderContents decodes base64, JSON-typed entries through YAML, then entities', () => {
  const plain = Buffer.from('<div class="p-4">&amp;more</div>').toString('base64');
  const json = Buffer.from('{"palette":{"color":"#fff"}}').toString('base64');
  assert.deepEqual(tool.decodeProviderContents([
    { content: plain },
    { content: json, type: 'json' },
  ]), [
    '<div class="p-4">&more</div>',
    // A leading # opens a YAML comment, so the scalar is single-quoted.
    "palette:\n  color: '#fff'",
  ]);
});

test('volumeMap keeps files only, rooted at / the way compile expects', () => {
  const map = tool.volumeMap([
    { relative_path: 'main.css', content: 'a {}' },
    { relative_path: 'src/nested.css', content: 'b {}' },
    { relative_path: 'src', directory: true, content: '' },
  ]);
  assert.deepEqual(map, { '/main.css': 'a {}', '/src/nested.css': 'b {}' });
});
