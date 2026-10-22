import assert from "node:assert/strict";
import { test } from "node:test";
import { formatDecimal, parseDecimal } from "./decimal.ts";

test("EN/DE numeric input rejects grouping instead of silently changing magnitude", () => {
	assert.equal(parseDecimal("1.5", "en-GB"), 1.5);
	assert.equal(parseDecimal("1,5", "de-DE"), 1.5);
	assert.equal(parseDecimal("", "de-DE"), null);
	assert.equal(parseDecimal("0", "de-DE"), 0);
	assert.throws(() => parseDecimal("1,000", "en-GB"));
	assert.throws(() => parseDecimal("1.000", "de-DE"));
	assert.throws(() => parseDecimal("1 000", "de-DE"));
	assert.throws(() => parseDecimal("1e100", "en-GB"));
	assert.equal(formatDecimal(1234.5, "de-DE"), "1234,5");
	assert.equal(formatDecimal(1234.5, "en-GB"), "1234.5");
});
