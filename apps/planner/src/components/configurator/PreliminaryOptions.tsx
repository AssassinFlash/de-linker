import { useEffect, useRef, type ReactNode } from "react";
import type { JsonObject } from "../../data/protocol.ts";
import type { Brief } from "../../domain/brief.ts";
import { __ } from "../../i18n.ts";
import { Icon } from "../Icon.tsx";
import { ProjectFacts, projectFacts } from "./ProjectFacts.tsx";
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
	locale,
	disabled,
	choose,
	action,
}: {
	inputs: JsonObject;
	locale: string;
	disabled: boolean;
	choose: (scope: NonNullable<Brief["system_scope"]>) => void;
	action?: ReactNode;
}) {
	const optionsHeading = useRef<HTMLHeadingElement>(null);
	useEffect(() => {
		optionsHeading.current?.focus({ preventScroll: true });
	}, []);
	const names = systemNames();
	const hasSolarPlan =
		inputs.pv_string_plan != null ||
		inputs.pv_plant_string_plan != null ||
		inputs.shared_dc_energy_run_id != null;
	const comparisons = {
		new_pv_storage: [
			__(
				"Use electricity from new solar panels during the day and store some for later.",
				"linker-tools",
			),
			__("Space for panels and how much electricity you use.", "linker-tools"),
		],
		storage_addition: [
			__(
				"Keep your solar panels and store more of the electricity they produce.",
				"linker-tools",
			),
			__("Which solar equipment you already have.", "linker-tools"),
		],
		pv_only: [
			__(
				"Generate electricity during the day with solar panels.",
				"linker-tools",
			),
			__(
				"Space for panels and how much electricity you use during the day.",
				"linker-tools",
			),
		],
		storage_only: [
			__("Store electricity to use it later.", "linker-tools"),
			__(
				"Where the battery will charge and what it needs to supply.",
				"linker-tools",
			),
		],
	} satisfies Record<NonNullable<Brief["system_scope"]>, [string, string]>;
	const facts = projectFacts(inputs, locale);
	const symbols = {
		new_pv_storage: "system",
		storage_addition: "layers",
		pv_only: "solar",
		storage_only: "energy",
	} as const;
	const options = (Object.keys(names) as (keyof typeof names)[]).filter(
		(scope) =>
			(scope !== "pv_only" || !hasStorageToExclude(inputs)) &&
			(scope !== "storage_only" || !hasSolarPlan),
	);

	return (
		<div
			className={`sc-layout sc-preliminary-layout${facts.length ? "" : " sc-preliminary-layout--comparison"}`}
		>
			<section className="sc-card sc-direction-comparison">
				<header className="sc-section-head">
					<div>
						<h2 ref={optionsHeading} tabIndex={-1}>
							{__("Preliminary options", "linker-tools")}
						</h2>
						<p>
							{__(
								"Choose what you want to do. We can work out the size and equipment later.",
								"linker-tools",
							)}
						</p>
					</div>
				</header>
				<table
					role="table"
					aria-label={__("Compare system options", "linker-tools")}
				>
					<thead role="rowgroup">
						<tr role="row">
							<th scope="col" role="columnheader">
								{__("Planned system", "linker-tools")}
							</th>
							<th scope="col" role="columnheader">
								{__("What it does", "linker-tools")}
							</th>
							<th scope="col" role="columnheader">
								{__("Details to confirm", "linker-tools")}
							</th>
							<td role="cell" />
						</tr>
					</thead>
					<tbody role="rowgroup">
						{options.map((scope) => (
							<tr key={scope} role="row">
								<th scope="row" role="rowheader" id={`sc-direction-${scope}`}>
									<span className="sc-direction-name">
										<span className="sc-direction-symbol">
											<Icon name={symbols[scope]} />
										</span>
										{names[scope]}
									</span>
								</th>
								<td role="cell">{comparisons[scope][0]}</td>
								<td role="cell" className="sc-direction-details">
									<span>{__("Details to confirm", "linker-tools")}</span>
									{comparisons[scope][1]}
								</td>
								<td role="cell" className="sc-direction-action">
									<button
										type="button"
										className="sc-button"
										disabled={disabled}
										aria-describedby={`sc-direction-${scope}`}
										onClick={() => choose(scope)}
									>
										{__("Select", "linker-tools")}
										<Icon name="arrow" />
									</button>
								</td>
							</tr>
						))}
					</tbody>
				</table>
				{action && <footer className="sc-direction-tools">{action}</footer>}
			</section>
			{facts.length > 0 && (
				<aside className="sc-sidebar">
					<section className="sc-card">
						<h2>{__("Project details", "linker-tools")}</h2>
						<ProjectFacts facts={facts} />
					</section>
				</aside>
			)}
		</div>
	);
}
