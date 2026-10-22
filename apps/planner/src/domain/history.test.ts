import assert from "node:assert/strict";
import { test } from "node:test";
import { change, newHistory, redo, undo } from "./history.ts";

test("undo/redo preserve document versions and a divergent edit closes the redo branch", () => {
	const original = { title: "Original", site: { country: "FR" } };
	const renamed = { ...original, title: "Renamed" };
	const moved = { ...renamed, site: { country: "CH" } };
	let history = newHistory(original);
	history = change(history, renamed, 3);
	history = change(history, moved, 3);
	assert.equal(undo(history).current, renamed);
	assert.equal(redo(undo(history)).current, moved);
	history = change(undo(history), { ...renamed, title: "Different option" }, 3);
	assert.equal(redo(history), history);
	assert.equal(history.future.length, 0);
	assert.deepEqual(original, { title: "Original", site: { country: "FR" } });
	assert.equal(history.serial, 4);
});

test("history resource limit bounds retained snapshots without altering the current input", () => {
	let history = newHistory({ annual_kwh: 1000 });
	for (let n = 0; n < 20; n++)
		history = change(history, { annual_kwh: 2000 + n }, 3);
	assert.equal(history.past.length, 3);
	assert.equal(history.current.annual_kwh, 2019);
	history = undo(undo(undo(history)));
	assert.equal(history.current.annual_kwh, 2016);
	assert.equal(undo(history), history);
	assert.equal(redo(redo(redo(history))).current.annual_kwh, 2019);
});
