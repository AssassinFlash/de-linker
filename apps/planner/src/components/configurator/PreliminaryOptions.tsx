import { useEffect, useRef } from "react";
import type { JsonObject } from "../../data/protocol.ts";
import type { Brief } from "../../domain/brief.ts";
import { __ } from "../../i18n.ts";
import { hasStorageToExclude } from "./ProjectDetails.tsx";

export function systemNames() {
	return {
		new_pv_storage: __("Solar and storage", "linker-tools"),
		storage_addition: __("Storage for existing PV", "linker-tools"),
		pv_only: __("Solar", "linker-tools"),
		storage_only: __("Storage", "linker-tools"),
	};
}

export function PreliminaryOptions({
	inputs,
	disabled,
	choose,
}: {
	inputs: JsonObject;
	disabled: boolean;
	choose: (scope: NonNullable<Brief["system_scope"]>) => void;
}) {
	const optionsHeading = useRef<HTMLHeadingElement>(null);
	useEffect(() => {
		optionsHeading.current?.focus();
	}, []);
	const names = systemNames();
	const hasSolarPlan =
		inputs.pv_string_plan != null ||
		inputs.pv_plant_string_plan != null ||
		inputs.shared_dc_energy_run_id != null;
	const systemDescriptions = {
		new_pv_storage: __(
			"New solar panels and a battery let you use solar power after sunset. Panel space and electricity use help size both.",
			"linker-tools",
		),
		storage_addition: __(
			"A battery stores extra power from the solar panels you already have. Your current equipment determines how the battery can be connected.",
			"linker-tools",
		),
		pv_only: __(
			"Solar panels supply electricity during the day. Available space and daytime electricity use help work out how many panels fit your project.",
			"linker-tools",
		),
		storage_only: __(
			"A battery saves electricity for when you need it. Its size depends on how you use electricity and where the battery gets its charge.",
			"linker-tools",
		),
	};

	return (
		<section className="sc-card">
			<header className="sc-section-head">
				<div>
					<h2 ref={optionsHeading} tabIndex={-1}>
						{__("Preliminary options", "linker-tools")}
					</h2>
					<p>
						{__(
							"Choose the option that sounds right for your project. We can work out the size and equipment with you.",
							"linker-tools",
						)}
					</p>
				</div>
			</header>
			<div className="sc-fields">
				{(Object.keys(names) as (keyof typeof names)[])
					.filter(
						(scope) =>
							(scope !== "pv_only" || !hasStorageToExclude(inputs)) &&
							(scope !== "storage_only" || !hasSolarPlan),
					)
					.map((scope) => (
						<article key={scope} className="sc-package">
							<h3 id={`sc-direction-${scope}`}>{names[scope]}</h3>
							<p>{systemDescriptions[scope]}</p>
							<button
								type="button"
								className="sc-button sc-primary"
								disabled={disabled}
								aria-describedby={`sc-direction-${scope}`}
								onClick={() => choose(scope)}
							>
								{__("Choose this option", "linker-tools")}
							</button>
						</article>
					))}
			</div>
		</section>
	);
}
