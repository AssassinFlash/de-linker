import { __ } from "../../i18n.ts";

type Stage = "project" | "system" | "review";
export type Step = Stage | "solar" | "energy";

export function ConfiguratorSteps({
	active,
	onSelect,
}: {
	active: Step;
	onSelect?: (step: Stage) => void;
}) {
	const stage = active === "solar" || active === "energy" ? "project" : active;
	const stages: [Stage, string][] = [
		["project", __("Project", "linker-tools")],
		["system", __("Choose a solution", "linker-tools")],
		["review", __("Review & inquire", "linker-tools")],
	];
	return (
		<nav
			className="sc-nav"
			aria-label={__("Project navigation", "linker-tools")}
		>
			{stages.map(([step, label], index) => (
				<button
					type="button"
					key={step}
					aria-current={stage === step ? "step" : undefined}
					disabled={!onSelect}
					onClick={() => onSelect?.(step)}
				>
					<span className="sc-step-number">{index + 1}</span>
					{label}
				</button>
			))}
		</nav>
	);
}
