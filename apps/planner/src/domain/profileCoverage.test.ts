import test from "node:test";
import assert from "node:assert/strict";
import { sharedProfileRange } from "./profileCoverage.ts";

test("shared source range keeps microsecond endpoint ordering and refuses an empty intersection", () => {
	const earlier = {
		start_utc: "2024-03-30T23:00:00.000001Z",
		end_utc: "2024-03-31T01:00:00.000002+00:00",
	};
	const later = {
		start_utc: "2024-03-30T23:00:00.000002+00:00",
		end_utc: "2024-03-31T01:00:00.000001Z",
	};
	assert.deepEqual(sharedProfileRange([earlier, later]), {
		start_utc: later.start_utc,
		end_utc: later.end_utc,
	});
	assert.throws(() => sharedProfileRange([]));
	assert.throws(() =>
		sharedProfileRange([
			earlier,
			{ start_utc: earlier.end_utc, end_utc: "2024-03-31T02:00:00Z" },
		]),
	);
	assert.throws(() =>
		sharedProfileRange([
			{ start_utc: "2024-03-30T23:00:00", end_utc: "2024-03-31T01:00:00Z" },
		]),
	);
});
