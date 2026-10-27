// Run from apps/planner with its existing tests/tsx-loader.mjs.
// Real React/hook/domain/journal; fake IndexedDB and explicit fault injection.
// This probes persistence semantics, not native map, provider or production UI.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const app = process.cwd();
assert.ok(app.endsWith("/apps/planner"), "Run from apps/planner");
const pin = "b48ffda68aeb2e9f17dd27b84f7449e05b321873";
const digest = (value) => createHash("sha256").update(value).digest("hex");
for (const name of ["src/data/useMapRoofDraft.ts", "src/data/MapRoofDraftStore.ts", "src/domain/mapRoofDraft.ts", "tests/dom-fixture.mjs"]) {
  const frozen = execFileSync("git", ["show", `${pin}:apps/planner/${name}`], { cwd: app });
  assert.equal(Buffer.compare(frozen, readFileSync(resolve(app, name))), 0, `${name} drifted from pin`);
}
const require = createRequire(resolve(app, "package.json"));
const React = require("react");
const { act } = React;
const { IDBFactory } = require("fake-indexeddb");
const moduleAt = (path) => import(pathToFileURL(resolve(app, path)).href);
const { setupDom, until } = await moduleAt("tests/dom-fixture.mjs");
const { MapRoofDraftStore } = await moduleAt("src/data/MapRoofDraftStore.ts");
const { useMapRoofDraft } = await moduleAt("src/data/useMapRoofDraft.ts");
const { appendMapRoofVertex } = await moduleAt("src/domain/mapRoofDraft.ts");
const asset = JSON.parse(readFileSync(resolve(app, "../../fixtures/planning/geometry-import-asset.json"), "utf8"));
const scope = "a".repeat(64), geometry = asset.metadata.geometry_import.geometry;
const dom = setupDom();
Object.defineProperty(globalThis, "indexedDB", { value: new IDBFactory(), configurable: true });
const store = new MapRoofDraftStore(), writes = [];
let loseOnePointAcknowledgements = 2;
const faultStore = {
  list: (...args) => store.list(...args),
  clear: (...args) => store.clear(...args),
  write: async (...args) => {
    const next = JSON.parse(args[2]);
    const entry = {
      points: next.vertices.length,
      previous_points: args[1] === null ? null : JSON.parse(args[1]).vertices.length,
      previous_sha256: args[1] === null ? null : digest(args[1]),
      next_sha256: digest(args[2]),
    };
    writes.push(entry);
    try {
      await store.write(...args);
      if (next.vertices.length === 1 && loseOnePointAcknowledgements-- > 0) {
        entry.result = "committed_then_unknown_ack";
        throw new Error("injected unknown local acknowledgement");
      }
      entry.result = "acknowledged";
    } catch (error) {
      entry.result ??= error.message;
      throw error;
    }
  },
};
const { createRoot } = await moduleAt("node_modules/react-dom/client.js");
const root = createRoot(dom.element);
const props = {
  projectId: asset.project_id, geometry, confirmedGeometry: null,
  locale: "de-DE", session: { query_scope: scope },
  client: { isCurrentScope: (candidate) => candidate === scope },
  recoveryScopes: [scope], store: faultStore,
};
let flow;
function Harness() {
  flow = useMapRoofDraft(props);
  return React.createElement("p", null, flow.drawing?.vertices.length ?? "none");
}
const records = () => store.list([scope], asset.project_id);
try {
  await act(async () => root.render(React.createElement(Harness)));
  await until(() => !flow.checking);
  await act(async () => flow.begin(null));
  await until(() => !flow.writing);
  const one = appendMapRoofVertex(flow.drawing, [6.96, 50.94]);
  const two = appendMapRoofVertex(one, [6.9601, 50.94]);
  const newer = { ...two, fields: { ...two.fields, pitch: "12,,invalid" } };
  await act(async () => { await flow.update(one).catch(() => undefined); });
  await act(async () => { await flow.update(newer).catch(() => undefined); });
  assert.equal(flow.storageFailed, true);
  assert.equal(flow.drawing.vertices.length, 2);
  assert.equal((await records())[0].drawing.vertices.length, 1);
  await act(async () => { await flow.retry(); });
  await until(() => !flow.checking && !flow.writing);
  assert.equal(flow.storageFailed, false);
  assert.equal(flow.drawing.fields.pitch, "12,,invalid");
  const acknowledged = (await records())[0];
  assert.equal(acknowledged.body, JSON.stringify(newer));
  const recoveryWrites = writes.slice();
  assert.deepEqual(recoveryWrites.map((entry) => entry.points), [0, 1, 1, 1, 2]);
  assert.deepEqual(recoveryWrites.map((entry) => entry.previous_points), [null, 0, 0, 0, 1]);
  assert.equal(new Set(recoveryWrites.slice(1, 4).map((entry) => entry.next_sha256)).size, 1);
  assert.equal(new Set(recoveryWrites.slice(1, 4).map((entry) => entry.previous_sha256)).size, 1);

  // A different tab legitimately advances the same record after the successful
  // retry. Neither a new edit, another Retry, nor Discard may erase that version.
  const otherTab = { ...acknowledged.drawing, fields: { ...acknowledged.drawing.fields, name: "Other tab synthetic version" } };
  await store.write(scope, acknowledged.body, JSON.stringify(otherTab));
  await act(async () => {
    await flow.update({ ...flow.drawing, fields: { ...flow.drawing.fields, name: "This tab synthetic copy" } }).catch(() => undefined);
  });
  await act(async () => { await flow.retry(); });
  await until(() => !flow.writing);
  assert.equal(flow.storageFailed, true);
  await act(async () => { await flow.discard(); });
  assert.equal(flow.storageFailed, true);
  assert.ok(flow.drawing);
  assert.equal((await records())[0].body, JSON.stringify(otherTab));
  await act(async () => { flow.fork(); });
  await until(() => !flow.writing);
  assert.deepEqual((await records()).map((record) => record.drawing.fields.name).sort(), ["Other tab synthetic version", "This tab synthetic copy"]);
  await act(async () => { await flow.discard(); });
  await until(() => !flow.checking);
  assert.equal((await records()).length, 1);
  assert.equal((await records())[0].body, JSON.stringify(otherTab));

  // Explicitly discarding another just-committed/unknown drawing first settles
  // its exact write and deletes only that copy, keeping the competing record.
  loseOnePointAcknowledgements = 1;
  await act(async () => { flow.begin(null); });
  await until(() => !flow.writing);
  await act(async () => { await flow.update(appendMapRoofVertex(flow.drawing, [6.96, 50.94])).catch(() => undefined); });
  assert.equal(flow.storageFailed, true);
  assert.equal((await records()).length, 2);
  await act(async () => { await flow.discard(); });
  await until(() => !flow.checking);
  assert.equal(flow.drawing, null);
  assert.equal(flow.storageFailed, false);
  assert.equal(flow.writing, false);
  assert.equal((await records()).length, 1);
  assert.equal((await records())[0].body, JSON.stringify(otherTab));

  console.log(JSON.stringify({
    pin, runtime: process.version,
    original_finding: "closed",
    repeated_unknown_ack_then_public_retry: {
      pass: true, open_points: 2, durable_points: 2,
      raw_invalid_pitch: "12,,invalid", exact_uncertain_bytes_replayed: true,
      writes: recoveryWrites,
    },
    competing_tab_retry_and_discard_refused: true,
    explicit_fork_preserved_both: true,
    explicit_discard_settled_unknown_and_preserved_competing_copy: true,
    boundary: "Real React/hook/domain/journal with fake IndexedDB and fault injection; no native map, provider, account or production acceptance",
  }, null, 2));
} finally {
  await dom.dispose(root);
  delete globalThis.indexedDB;
}
