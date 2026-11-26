import assert from "node:assert/strict";
import test from "node:test";
import { blankBrief, emptyBrief, readBrief } from "./brief.ts";

test("the immutable blank intake matches the external brief contract and editable copies are independent", () => {
	assert.equal(readBrief(blankBrief), blankBrief);
	assert.deepEqual(
		readBrief(JSON.parse(JSON.stringify(blankBrief))),
		blankBrief,
	);
	assert.ok(
		Object.isFrozen(blankBrief.site) && Object.isFrozen(blankBrief.annual_load),
	);
	const input = emptyBrief();
	assert.notEqual(input.site, blankBrief.site);
	assert.notEqual(input.annual_load, blankBrief.annual_load);
	assert.equal(Object.isFrozen(input.site), false);
	assert.equal(blankBrief.site.country_code, null);
	assert.throws(() => readBrief({ ...input, schema_version: 2 }));
});
