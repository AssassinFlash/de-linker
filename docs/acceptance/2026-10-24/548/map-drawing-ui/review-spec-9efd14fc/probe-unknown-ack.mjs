// Read-only application probe. Run from apps/planner with its existing TSX loader.
// Real React + hook + journal + domain; fault-injected local acknowledgement.
// No map renderer, native provider, account or production acceptance.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const app = process.cwd();
assert.ok(app.endsWith("/apps/planner"), "Run from apps/planner");
const pin = "9efd14fcb79687344d676a8fdb5fbd24c2e9aad8";
for (const name of [
  "src/data/useMapRoofDraft.ts", "src/data/MapRoofDraftStore.ts",
  "src/domain/mapRoofDraft.ts", "tests/dom-fixture.mjs",
]) {
  const pinned = execFileSync("git", ["show", `${pin}:apps/planner/${name}`], { cwd: app });
  assert.equal(Buffer.compare(pinned, readFileSync(resolve(app, name))), 0, `${name} drifted from pin`);
}
const require = createRequire(resolve(app, "package.json"));
const React = require("react");
const { act } = React;
const { IDBFactory } = require("fake-indexeddb");
const moduleAt = (name) => import(pathToFileURL(resolve(app, name)).href);
const { setupDom, until } = await moduleAt("tests/dom-fixture.mjs");
const { MapRoofDraftStore } = await moduleAt("src/data/MapRoofDraftStore.ts");
const { useMapRoofDraft } = await moduleAt("src/data/useMapRoofDraft.ts");
const { appendMapRoofVertex } = await moduleAt("src/domain/mapRoofDraft.ts");
const fixture = JSON.parse(readFileSync(resolve(app, "../../fixtures/planning/geometry-import-asset.json"), "utf8"));
const geometry = fixture.metadata.geometry_import.geometry;
const scope = "a".repeat(64);
const dom = setupDom();
Object.defineProperty(globalThis, "indexedDB", { value: new IDBFactory(), configurable: true });
const store = new MapRoofDraftStore();
const writes = [];
let loseOnePointAcknowledgement = true;
const faultStore = {
  list: (...args) => store.list(...args),
  clear: (...args) => store.clear(...args),
  write: async (...args) => {
    const next = JSON.parse(args[2]);
    const event = { points: next.vertices.length, previous: args[1] === null ? null : JSON.parse(args[1]).vertices.length };
    writes.push(event);
    try {
      await store.write(...args);
      if (next.vertices.length === 1 && loseOnePointAcknowledgement) {
        loseOnePointAcknowledgement = false;
        event.result = "committed_then_unknown_ack";
        throw new Error("injected unknown local acknowledgement");
      }
      event.result = "acknowledged";
    } catch (error) {
      event.result ??= error.message;
      throw error;
    }
  },
};
const { createRoot } = await moduleAt("node_modules/react-dom/client.js");
const root = createRoot(dom.element);
const props = {
  projectId: fixture.project_id, geometry, confirmedGeometry: null,
  locale: "de-DE", session: { query_scope: scope },
  client: { isCurrentScope: (candidate) => candidate === scope },
  recoveryScopes: [scope], store: faultStore,
};
let flow;
function Harness() {
  flow = useMapRoofDraft(props);
  return React.createElement("p", null, flow.drawing?.vertices.length ?? "none");
}
try {
  await act(async () => root.render(React.createElement(Harness)));
  await until(() => !flow.checking);
  await act(async () => flow.begin(null));
  await until(() => !flow.writing);
  const one = appendMapRoofVertex(flow.drawing, [6.96, 50.94]);
  const two = appendMapRoofVertex(one, [6.9601, 50.94]);
  await act(async () => { await flow.update(one).catch(() => undefined); });
  assert.equal(flow.storageFailed, true);
  // Accepted input is still enabled while storageFailed. Preserve the newer
  // buffer before pressing the actual public Retry path.
  await act(async () => { await flow.update(two).catch(() => undefined); });
  await act(async () => { await flow.retry(); });
  const records = await store.list([scope], fixture.project_id);
  const observation = {
    pin, runtime: process.version, library_versions: {
      react: require("react/package.json").version,
      fake_indexeddb: JSON.parse(readFileSync(resolve(app, "node_modules/fake-indexeddb/package.json"), "utf8")).version,
    },
    open_points: flow.drawing.vertices.length,
    durable_points: records[0].drawing.vertices.length,
    storage_failed_after_retry: flow.storageFailed,
    writes,
    boundary: "React/journal/domain fault injection only; no native map or production acceptance",
  };
  assert.equal(observation.open_points, 2);
  assert.equal(observation.durable_points, 1);
  assert.equal(observation.storage_failed_after_retry, true);
  assert.deepEqual(writes.map((event) => event.points), [0, 1, 2, 2]);
  assert.equal(writes[2].result, "map_drawing_recovery_conflict");
  assert.equal(writes[3].result, "map_drawing_recovery_conflict");
  console.log(JSON.stringify(observation, null, 2));
} finally {
  await dom.dispose(root);
  delete globalThis.indexedDB;
}
