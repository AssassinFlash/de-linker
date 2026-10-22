/** Stable service codes; private cell values never become error messages. */
export const PROFILE_ISSUES = [
	"timestamp_format",
	"timestamp_range",
	"fold_value",
	"offset_and_fold",
	"local_time_range",
	"local_time_nonexistent",
	"fold_mismatch",
	"local_time_ambiguous",
	"number_format",
	"number_nonfinite",
	"encoding",
	"headers",
	"row_width",
	"interval_duration",
	"interval_order",
	"value_sign",
	"energy_range",
	"csv_syntax",
	"empty",
] as const;
export interface ProfileIssue {
	readonly issue: (typeof PROFILE_ISSUES)[number];
	readonly line: number | null;
	readonly field: "timestamp" | "end_timestamp" | "value" | "header" | null;
}
export function readProfileIssue(value: unknown): ProfileIssue | null {
	if (value === null || typeof value !== "object" || Array.isArray(value))
		return null;
	const item = value as Record<string, unknown>;
	if (
		Object.keys(item).sort().join() !== "field,issue,line" ||
		!(PROFILE_ISSUES as readonly unknown[]).includes(item.issue) ||
		(item.line !== null &&
			(typeof item.line !== "number" ||
				!Number.isSafeInteger(item.line) ||
				item.line < 1)) ||
		![null, "timestamp", "end_timestamp", "value", "header"].includes(
			item.field as string | null,
		)
	)
		return null;
	return value as ProfileIssue;
}
