import { __ } from "../../i18n.ts";

export type Step = "project" | "solar" | "energy" | "system" | "review";

export function ConfiguratorSteps({
	active,
	storageOnly,
	onSelect,
}: {
	active: Step;
	storageOnly: boolean;
	onSelect?: (step: Step) => void;
}) {
	const steps: [Step, string][] = [
		["project", __("Project", "linker-tools")],
		["solar", __("Solar", "linker-tools")],
		["energy", __("Energy use", "linker-tools")],
		["system", __("System", "linker-tools")],
		["review", __("Review & share", "linker-tools")],
	];
	return (
		<nav
			className="sc-nav"
			aria-label={__("Project navigation", "linker-tools")}
		>
			{steps
				.filter(([step]) => step !== "solar" || !storageOnly)
				.map(([step, label], index) => (
					<button
						type="button"
						key={step}
						aria-current={active === step ? "step" : undefined}
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
