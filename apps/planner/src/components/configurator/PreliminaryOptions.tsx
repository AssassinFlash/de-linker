import { useEffect, useRef, type ReactNode, type RefObject } from "react";
import type { JsonObject } from "../../data/protocol.ts";
import { readBrief, type Brief } from "../../domain/brief.ts";
import { __ } from "../../i18n.ts";
import { energyGoal } from "../../domain/energyGoal.ts";
import { equipmentDraft } from "../../domain/equipment.ts";
import { hasPlant } from "../../domain/equipmentPlant.ts";
import { Icon } from "../Icon.tsx";
import { ProjectSummary, projectFacts } from "./ProjectFacts.tsx";
import { hasStorageToExclude } from "../../domain/storageScope.ts";

export function systemNames() {
	return {
		new_pv_storage: __("Solar and storage", "linker-tools"),
		storage_addition: __("Storage for existing PV", "linker-tools"),
		pv_only: __("Solar", "linker-tools"),
		storage_only: __("Storage", "linker-tools"),
	};
}

export function retrofitOptions(inputs: JsonObject) {
	const goal = energyGoal(inputs);
	if (
		!inputs.brief ||
		readBrief(inputs.brief).system_scope !== "storage_addition" ||
		hasPlant(inputs) ||
		equipmentDraft(inputs).inverter_product_id !== null
	)
		return null;
	const options = {
		self: {
			keep: {
				benefit: __(
					"Keep the PV inverter in service and add storage for surplus solar power.",
					"linker-tools",
				),
				check: __(
					"Check the inverter model and whether storage can connect to it or needs a separate battery inverter.",
					"linker-tools",
				),
			},
			replace: {
				benefit: __(
					"A hybrid inverter can connect the existing panels and a battery. This option includes replacing the PV inverter.",
					"linker-tools",
				),
				check: __(
					"Check the panel strings, battery compatibility and grid connection before choosing a model.",
					"linker-tools",
				),
			},
		},
		peak: {
			keep: {
				benefit: __(
					"Keep the PV inverter and add storage that can discharge when site demand approaches the grid import limit.",
					"linker-tools",
				),
				check: __(
					"Use the measured load profile to check how much power the battery inverter would need during demand peaks.",
					"linker-tools",
				),
			},
			replace: {
				benefit: __(
					"A replacement hybrid inverter can coordinate solar generation and battery discharge to limit grid import at peak times.",
					"linker-tools",
				),
				check: __(
					"Check the panel strings and whether the inverter and battery can cover the measured peaks above the import limit.",
					"linker-tools",
				),
			},
		},
		backup: {
			keep: {
				benefit: __(
					"Keep the PV inverter and add a battery backup supply for selected circuits.",
					"linker-tools",
				),
				check: __(
					"Check how the backup supply isolates from the grid and whether it can power those circuits for the requested duration.",
					"linker-tools",
				),
			},
			replace: {
				benefit: __(
					"A hybrid inverter with a backup output could supply selected circuits from the battery during an outage.",
					"linker-tools",
				),
				check: __(
					"Check backup output power, changeover equipment and the battery capacity needed for the requested duration.",
					"linker-tools",
				),
			},
		},
	}[goal || "self"];
	return [
		{
			keep: true,
			title: __("Keep the existing inverter", "linker-tools"),
			...options.keep,
			...(!goal && {
				benefit: __(
					"Add a battery while keeping your existing PV inverter.",
					"linker-tools",
				),
			}),
		},
		{
			keep: false,
			title: __("Consider a replacement inverter", "linker-tools"),
			...options.replace,
		},
	];
}

export function PreliminaryOptions({
	inputs,
	locale,
	disabled,
	choose,
	chooseRetrofit,
	projectTitle,
	headingRef,
	action,
}: {
	inputs: JsonObject;
	locale: string;
	disabled: boolean;
	choose: (scope: NonNullable<Brief["system_scope"]>) => void;
	projectTitle?: string;
	headingRef?: RefObject<HTMLHeadingElement | null>;
	chooseRetrofit?: (keep: boolean) => void;
	action?: ReactNode;
}) {
	const optionsHeading = useRef<HTMLHeadingElement>(null);
	useEffect(() => {
		if (!headingRef) optionsHeading.current?.focus({ preventScroll: true });
	}, [headingRef]);
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

	const retrofit = chooseRetrofit && retrofitOptions(inputs);
	const rows =
		retrofit && chooseRetrofit
			? retrofit.map((item) => ({
					id: item.keep ? "keep" : "replace",
					title: item.title,
					symbol: "layers" as const,
					benefit: item.benefit,
					check: item.check,
					select: () => chooseRetrofit(item.keep),
				}))
			: options.map((scope) => ({
					id: scope,
					title: names[scope],
					symbol: symbols[scope],
					benefit: comparisons[scope][0],
					check: comparisons[scope][1],
					select: () => choose(scope),
				}));

	return (
		<div
			className={`sc-layout sc-preliminary-layout${facts.length ? "" : " sc-preliminary-layout--comparison"}`}
		>
			<section className="sc-card sc-direction-comparison">
				<header className="sc-section-head">
					<div>
						<h2 ref={headingRef ?? optionsHeading} tabIndex={-1}>
							{__("Preliminary options", "linker-tools")}
						</h2>
						<p>
							{retrofit
								? __(
										"Both options keep your existing panels. The inverter determines how the battery connects.",
										"linker-tools",
									)
								: __(
										"Choose what you want to do. We can work out the size and equipment later.",
										"linker-tools",
									)}
						</p>
					</div>
				</header>
				{action && <div className="sc-direction-tools">{action}</div>}
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
						{rows.map((row) => (
							<tr key={row.id} role="row">
								<th scope="row" role="rowheader" id={`sc-direction-${row.id}`}>
									<span className="sc-direction-name">
										<span className="sc-direction-symbol">
											<Icon name={row.symbol} />
										</span>
										{row.title}
									</span>
								</th>
								<td role="cell">{row.benefit}</td>
								<td role="cell" className="sc-direction-details">
									<span>{__("Details to confirm", "linker-tools")}</span>
									{row.check}
								</td>
								<td role="cell" className="sc-direction-action">
									<button
										type="button"
										className="sc-button"
										disabled={disabled}
										aria-describedby={`sc-direction-${row.id}`}
										onClick={row.select}
									>
										{__("Select", "linker-tools")}
										<Icon name="arrow" />
									</button>
								</td>
							</tr>
						))}
					</tbody>
				</table>
			</section>
			{facts.length > 0 && (
				<ProjectSummary
					title={projectTitle || __("Project details", "linker-tools")}
					facts={facts}
				/>
			)}
		</div>
	);
}
