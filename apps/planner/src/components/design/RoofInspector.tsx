import { useId, type ReactNode } from "react";
import { __ } from "../../i18n.ts";

export type RoofTab = "geometry" | "modules" | "summary";
const tabs: readonly RoofTab[] = ["geometry", "modules", "summary"];

export function RoofInspector({
	tab,
	foot,
	change,
	locked,
	geometry,
	modules,
	summary,
}: {
	tab: RoofTab;
	foot: ReactNode;
	change: (tab: RoofTab) => void;
	locked: boolean;
	geometry: ReactNode;
	modules: ReactNode;
	summary: ReactNode;
}) {
	const id = useId();
	const labels = {
		geometry: __("Geometry", "linker-tools"),
		modules: __("Modules", "linker-tools"),
		summary: __("Summary", "linker-tools"),
	};
	const panels = { geometry, modules, summary };
	return (
		<aside className="sc-roof-inspector">
			<div
				className="sc-inspector-tabs"
				role="tablist"
				aria-label={__("Roof inspector", "linker-tools")}
			>
				{tabs.map((name, index) => (
					<button
						key={name}
						type="button"
						role="tab"
						id={id + name}
						aria-controls={id + name + "-panel"}
						aria-selected={name === tab}
						tabIndex={name === tab ? 0 : -1}
						disabled={locked && name !== tab}
						onClick={() => change(name)}
						onKeyDown={(event) => {
							if (locked) return;
							const next =
								event.key === "Home"
									? tabs[0]
									: event.key === "End"
										? tabs.at(-1)
										: event.key === "ArrowLeft"
											? tabs[(index + tabs.length - 1) % tabs.length]
											: event.key === "ArrowRight"
												? tabs[(index + 1) % tabs.length]
												: undefined;
							if (!next) return;
							event.preventDefault();
							change(next);
							document.getElementById(id + next)?.focus();
						}}
					>
						{labels[name]}
					</button>
				))}
			</div>
			{tabs.map((name) => (
				<div
					key={name}
					className="sc-roof-props"
					id={id + name + "-panel"}
					role="tabpanel"
					aria-labelledby={id + name}
					hidden={tab !== name}
				>
					{panels[name]}
				</div>
			))}
			{foot}
		</aside>
	);
}
