import { ApiError } from "../data/protocol.ts";

/** Compare pinned UTC endpoints at their actual microsecond precision. */
function instant(value: string): bigint {
	const match =
		/^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,6}))?(?:Z|\+00:00)$/.exec(
			value,
		);
	if (!match) throw new ApiError(502, "invalid_profile_range");
	const seconds = Date.parse(match[1] + "Z");
	if (!Number.isFinite(seconds))
		throw new ApiError(502, "invalid_profile_range");
	return BigInt(seconds) * 1000n + BigInt((match[2] ?? "").padEnd(6, "0"));
}
export function sharedProfileRange(
	ranges: readonly { readonly start_utc: string; readonly end_utc: string }[],
): { start_utc: string; end_utc: string } {
	if (!ranges.length) throw new ApiError(422, "scenario_profiles_required");
	let start = ranges[0]!.start_utc,
		end = ranges[0]!.end_utc;
	for (const range of ranges) {
		if (instant(range.start_utc) >= instant(range.end_utc))
			throw new ApiError(502, "invalid_profile_range");
		if (instant(range.start_utc) > instant(start)) start = range.start_utc;
		if (instant(range.end_utc) < instant(end)) end = range.end_utc;
	}
	if (instant(start) >= instant(end))
		throw new ApiError(422, "no_shared_profile_range");
	return { start_utc: start, end_utc: end };
}
