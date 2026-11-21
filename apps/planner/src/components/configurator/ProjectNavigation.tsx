import { __ } from "../../i18n.ts";

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
}: {
	current: ProjectChapter;
	storageOnly: boolean;
	open: (chapter: ProjectChapter) => void;
}) {
	const labels = {
		project: __("Project", "linker-tools"),
		solar: __("Solar", "linker-tools"),
		energy: __("Energy use", "linker-tools"),
		system: __("System", "linker-tools"),
		review: __("Report & inquiry", "linker-tools"),
	};
	return (
		<nav
			className="sc-nav sc-project-navigation"
			aria-label={__("Project navigation", "linker-tools")}
		>
			{chapters
				.filter((chapter) => chapter !== "solar" || !storageOnly)
				.map((chapter, i) => (
					<button
						type="button"
						key={chapter}
						aria-current={current === chapter ? "step" : undefined}
						onClick={() => open(chapter)}
					>
						<span aria-hidden="true" className="sc-step-number">
							{i + 1}
						</span>
						{labels[chapter]}
					</button>
				))}
		</nav>
	);
}
