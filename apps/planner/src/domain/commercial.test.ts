import assert from "node:assert/strict";
import { test } from "node:test";
import {
	MINIMUM_PROFILE_INTERVALS,
	profileCsv,
	profileRefusal,
	profileRows,
	readSizing,
} from "./commercial.ts";

/** One year of a plausible commercial load at 15-minute resolution. */
function profile(
	days = 30,
	stamp: (day: number, quarter: number) => string | null = () => null,
): string {
	const lines: string[] = [];
	for (let day = 0; day < days; day += 1) {
		for (let quarter = 0; quarter < 96; quarter += 1) {
			const hour = (quarter * 15) / 60;
			const value = hour >= 7 && hour < 18 ? 95 + (quarter % 8) * 3 : 18;
			const time = stamp(day, quarter);
			lines.push(time === null ? String(value) : `${time};${value}`);
		}
	}
	return lines.join("\n");
}

const iso = (day: number, quarter: number): string => {
	const start = Date.UTC(2026, 0, 1) + day * 86_400_000 + quarter * 900_000;
	return new Date(start).toISOString().replace(".000Z", "Z");
};

test("the last numeric cell of each line counts, as the engine reads it", () => {
	const rows = profileRows(
		"time;power\n2026-01-01T00:00Z;18,5\n2026-01-01T00:15Z;-4\n\n",
	);
	assert.deepEqual(
		rows.map((row) => row.value),
		[18.5, -4],
	);
	assert.equal(rows[0]!.timestamp, "2026-01-01T00:00Z");
});

test("the German export shape keeps its magnitude, as the engine reads it", () => {
	// A timestamp column beside a decimal-comma value is the ordinary German
	// export; the engine's delimiter sniff sees one semicolon for one comma and
	// reads the last cell as 18.5. Measured on the review engine: a
	// `;`-separated file of `18,5` sized at a 18.5 kW peak.
	assert.deepEqual(
		profileRows("2026-01-01T00:00Z;18,5").map((row) => row.value),
		[18.5],
	);
	// Without any other text the sniff cannot tell a decimal comma from a
	// column separator; the engine reads 25 here (measured), and this parser
	// follows the engine rather than inventing a second opinion.
	assert.deepEqual(
		profileRows("18,5;19,25").map((row) => row.value),
		[25],
	);
});

test("a one-week profile is the engine's own minimum, in the interface", () => {
	assert.equal(profileRefusal(profileRows(profile(6))), "profile_too_short");
	assert.equal(profileRefusal(profileRows(profile(30))), null);
	assert.equal(profileRows(profile(7)).length, MINIMUM_PROFILE_INTERVALS);
});

test("an empty or negative profile is named before it is sent", () => {
	assert.equal(profileRefusal(profileRows("time;power\n")), "profile_empty");
	assert.equal(
		profileRefusal(profileRows(profile(30).replace("95", "-95"))),
		"profile_negative",
	);
});

test("timestamped rows that step exactly 15 minutes are accepted", () => {
	assert.equal(profileRefusal(profileRows(profile(30, iso))), null);
});

test("a timestamped profile without a UTC offset is refused, because a local hour repeats or is skipped at a clock change", () => {
	const local = (day: number, quarter: number): string =>
		iso(day, quarter).replace("Z", "").replace("T", " ");
	assert.equal(
		profileRefusal(profileRows(profile(30, local))),
		"profile_timestamps_need_offset",
	);
});

test("an explicit offset is accepted and keeps the series unambiguous", () => {
	const offset = (day: number, quarter: number): string => {
		const start = Date.UTC(2026, 0, 1) + day * 86_400_000 + quarter * 900_000;
		return new Date(start + 3_600_000).toISOString().replace(".000Z", "+01:00");
	};
	assert.equal(profileRefusal(profileRows(profile(30, offset))), null);
});

test("a profile whose timestamps skip or repeat at a clock change is refused", () => {
	// The hour after a spring change: every row after it is one hour earlier
	// than its own position says, so one step is not 15 minutes.
	const text = profile(30, (day, quarter) =>
		day === 10 && quarter > 40
			? iso(day, quarter)
					.replace("T", "T")
					.replace(/T\d{2}/, "T00")
			: iso(day, quarter),
	);
	assert.equal(
		profileRefusal(profileRows(text)),
		"profile_irregular_intervals",
	);
});

test("the engine receives one value per line, without the timestamps", () => {
	const rows = profileRows(profile(30, iso));
	const csv = profileCsv(rows);
	assert.equal(csv.split("\n").length, rows.length);
	assert.ok(csv.split("\n").every((line) => /^\d+(?:\.\d+)?$/.test(line)));
});

test("the request keeps the engine's own field vocabulary", () => {
	const sizing = readSizing({
		plz: "80331",
		grid_connection_kva: 150,
		annual_kwh: 380000,
		goals: ["peak_shaving"],
		target_peak_kw: 70,
		load_profile_unit: "kW",
		locale: "de",
	});
	assert.equal(sizing.plz, "80331");
	assert.equal(sizing.target_peak_kw, 70);
	assert.equal(sizing.peak_kw, null);
	assert.equal(sizing.locale, "de");
});

test("a request outside the engine's contract is refused", () => {
	for (const value of [
		{
			plz: "SW1A",
			grid_connection_kva: 1,
			annual_kwh: 1,
			goals: ["peak_shaving"],
		},
		{ plz: "80331", grid_connection_kva: 1, annual_kwh: 1, goals: [] },
		{
			plz: "80331",
			grid_connection_kva: 1,
			annual_kwh: 1,
			goals: ["teleport"],
		},
	])
		assert.throws(() => readSizing(value), /invalid_commercial_sizing/);
});
