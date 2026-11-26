import { readEntryHints } from "../domain/entryHints.ts";
import { hasComparisonDraft } from "./comparisonDraft.ts";

export function isPublicIntakeLocation(
	url: URL,
	hints = readEntryHints(url.searchParams),
): boolean {
	const privateKeys = [
		"project",
		"projects",
		"saved_solution",
		"brief",
		"run",
		"retry_revision",
		"linker_inquiry_retry",
		"view",
		"energy_view",
		"product_id",
	];
	return (
		!hints?.invalid &&
		!privateKeys.some((key) => url.searchParams.has(key)) &&
		!url.searchParams.has("step") &&
		(!url.hash || url.hash === "#sc-preliminary-options")
	);
}

export function canStartPublicIntake(
	config: { nonceUrl: string; hasWorkspaceSession?: boolean },
	url: URL,
): boolean {
	return (
		!config.nonceUrl &&
		!config.hasWorkspaceSession &&
		!hasComparisonDraft() &&
		isPublicIntakeLocation(url)
	);
}
