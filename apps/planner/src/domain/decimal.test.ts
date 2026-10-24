import assert from "node:assert/strict";
import { test } from "node:test";
import {
	formatDecimal,
	parseDecimal,
	toPercent,
	fromPercent,
} from "./decimal.ts";

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

test("percent boundaries shift declared decimal digits without binary multiplication artifacts or hidden rounding", () => {
	assert.equal(toPercent(0.57), 57);
	assert.equal(toPercent(0.56), 56);
	assert.equal(fromPercent(57), 0.57);
	assert.equal(fromPercent(96.37), 0.9637);
	assert.equal(toPercent(-0.0029), -0.29);
	assert.equal(toPercent(1e-9), 1e-7);
	assert.equal(toPercent(0.5700000000000001), 57.00000000000001);
	assert.equal(toPercent(null), null);
	assert.equal(fromPercent(null), null);
	assert.ok(Object.is(toPercent(-0), -0));
	assert.ok(Object.is(fromPercent(-0), -0));
});
