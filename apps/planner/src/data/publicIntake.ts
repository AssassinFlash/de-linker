import { readEntryHints } from "../domain/entryHints.ts";
import { hasComparisonDraft } from "./comparisonDraft.ts";

export function canStartPublicIntake(
	config: { nonceUrl: string; hasWorkspaceSession?: boolean },
	url: URL,
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
	const hints = readEntryHints(url.searchParams);
	return (
		!config.nonceUrl &&
		!config.hasWorkspaceSession &&
		!hasComparisonDraft() &&
		!privateKeys.some((key) => url.searchParams.has(key)) &&
		!url.searchParams.has("step") &&
		(!url.hash || url.hash === "#sc-preliminary-options") &&
		(!hints ||
			url.searchParams.get("compare") === "preliminary" ||
			url.searchParams.get("scope") === "storage_addition" ||
			url.searchParams.get("application") === "commercial")
	);
}
