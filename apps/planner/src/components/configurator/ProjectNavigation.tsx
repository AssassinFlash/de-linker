import { __ } from "../../i18n.ts";

import { InquiryStages } from "./ProjectHeading.tsx";
import { comparisonPair } from "../../data/energyComparison.ts";

const chapters = ["project", "solar", "energy", "system", "review"] as const;
export type ProjectChapter = (typeof chapters)[number];

export function isRoofLocation(hash: string) {
	return [
		"#sc-roof",
		"#sc-map-roof-properties",
		"#sc-map-ring-properties",
		"#sc-map-feature-properties",
	].includes(hash);
}

export function projectChapter(url: URL): ProjectChapter {
	if (
		(!url.hash || url.hash === "#sc-review") &&
		comparisonPair(url.searchParams.get("compare"))
	)
		return "energy";
	const chapter = chapters.find((value) => url.hash === "#sc-" + value);
	if (chapter) return chapter;
	if (
		isRoofLocation(url.hash) ||
		url.hash === "#sc-roof-plan" ||
		url.searchParams.get("step") === "roof"
	)
		return "solar";
	if (/^[a-f0-9]{32}$/.test(url.searchParams.get("run") ?? "")) return "review";
	return url.searchParams.get("step") === "equipment" ? "system" : "project";
}

export function ProjectNavigation({
	current,
	storageOnly,
	open,
	comparing = false,
}: {
	current: ProjectChapter;
	storageOnly: boolean;
	open: (chapter: ProjectChapter) => void;
	comparing?: boolean;
}) {
	const currentStage =
		current === "review" ? 3 : current === "project" || comparing ? 1 : 2;
	const refinements = [
		{ chapter: "solar", label: __("Roof & PV", "linker-tools") },
		{ chapter: "energy", label: __("Energy profile & CSV", "linker-tools") },
		{ chapter: "system", label: __("Matched equipment", "linker-tools") },
	] as const;
	return (
		<>
			<InquiryStages
				current={currentStage}
				open={(stage) => {
					if (stage === 1) open("project");
					else if (stage === 2) open(storageOnly ? "energy" : "solar");
					else open("review");
				}}
			/>
			{currentStage === 2 && (
				<nav
					className="sc-refinement-tabs"
					aria-label={__("Fine-tune (optional)", "linker-tools")}
				>
					{refinements
						.filter(({ chapter }) => chapter !== "solar" || !storageOnly)
						.map(({ chapter, label }) => (
							<button
								type="button"
								key={chapter}
								aria-current={current === chapter ? "page" : undefined}
								onClick={() => open(chapter)}
							>
								{label}
							</button>
						))}
				</nav>
			)}
		</>
	);
}
