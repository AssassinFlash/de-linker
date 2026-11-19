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
	back,
}: {
	inputs: JsonObject;
	disabled: boolean;
	choose: (scope: NonNullable<Brief["system_scope"]>) => void;
	back: () => void;
}) {
	const optionsHeading = useRef<HTMLHeadingElement>(null);
	useEffect(() => {
		optionsHeading.current?.focus();
	}, []);
	const names = systemNames();
	const systemDescriptions = {
		new_pv_storage: __(
			"Plan panels and a battery together to use solar power after sunset. Panel area and electricity use will help size both.",
			"linker-tools",
		),
		storage_addition: __(
			"Store surplus power from an existing solar array. The existing inverter determines how a battery can be connected.",
			"linker-tools",
		),
		pv_only: __(
			"Generate electricity with solar panels alone. Available panel area and daytime electricity use guide the array size.",
			"linker-tools",
		),
		storage_only: __(
			"Plan a battery without adding solar panels. Electricity use and the charging source guide battery sizing.",
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
							"Choose the direction you want to discuss. System size, grid connection and equipment compatibility still need to be confirmed.",
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
							(scope !== "storage_only" ||
								(!inputs.pv_string_plan && !inputs.pv_plant_string_plan)),
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
			<footer className="sc-footer">
				<button
					type="button"
					className="sc-button"
					disabled={disabled}
					onClick={back}
				>
					{__("Back to project", "linker-tools")}
				</button>
			</footer>
		</section>
	);
}
