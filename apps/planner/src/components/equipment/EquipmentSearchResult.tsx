import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { PlanningRun } from "../../data/planningProtocol.ts";
import { ApiError, type JsonObject } from "../../data/protocol.ts";
import type { EquipmentSelection } from "../../domain/equipment.ts";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import type { EquipmentCandidate } from "../../data/equipmentSearch.ts";
import {
	readEquipmentCandidate,
	isPlantCandidate,
} from "../../data/equipmentSearch.ts";
import { readObject } from "../../data/readProtocol.ts";
import { EquipmentResult } from "./EquipmentResult.tsx";
import { CertificateEvidence } from "./CertificateEvidence.tsx";
import { equipmentStatus } from "./equipmentLabels.ts";
import { __ } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";

export function EquipmentSearchResult({
	run,
	locale,
	dirty,
	confirmedRevision,
	client,
	scope,
	disabled,
	apply,
	onError,
	plantActive = false,
	projectCandidate,
}: {
	run: PlanningRun;
	locale: string;
	dirty: boolean;
	confirmedRevision: number;
	client: PlannerClient;
	scope: string;
	disabled: boolean;
	apply: (candidate: EquipmentCandidate) => Promise<void>;
	onError: (cause: unknown) => void;
	plantActive?: boolean;
	projectCandidate?: JsonObject;
}) {
	const search = run.result ? readObject(run.result.search) : null;
	const candidates = (search?.candidates ?? []) as EquipmentCandidate[];
	const products = new Map(
		((search?.products ?? []) as JsonObject[]).map((p) => [
			p.canonical_product_id,
			p,
		]),
	);
	const [selected, setSelected] = useState<string | null>(null),
		[busy, setBusy] = useState(false),
		[demandFilter, setDemandFilter] = useState("all");
	const visibleCandidates = candidates.filter(
		(item) => demandFilter === "all" || item.demand?.status === demandFilter,
	);
	const adoptedId =
		projectCandidate?.run_id === run.id ? projectCandidate.candidate_id : null;
	const candidate =
		visibleCandidates.find((c) => c.id === (selected ?? adoptedId)) ??
		visibleCandidates[0];
	const alreadyAdopted = candidate?.id === adoptedId;
	const plantSearch =
		search &&
		readObject(search.coverage).template ===
			"declared_plant_one_external_assembly_per_converter";
	const differentArrangement = Boolean(plantActive) !== Boolean(plantSearch);
	const detail = useQuery({
		queryKey: ["equipment-candidate", scope, run.id, candidate?.id],
		enabled: !!candidate && client.isCurrentScope(scope),
		retry: (failureCount, error) =>
			failureCount < 1 && error instanceof ApiError && error.status === 503,
		staleTime: Infinity,
		refetchOnWindowFocus: false,
		queryFn: async ({ signal }) =>
			readEquipmentCandidate(
				await client.query(
					"equipment/candidates/read",
					{ schema_version: 1, run_id: run.id, candidate_id: candidate!.id },
					scope,
					signal,
				),
				run.id,
				candidate!,
			),
	});
	const deviceNames = (selection: EquipmentSelection) =>
		[selection.inverter_product_id, selection.battery_product_id]
			.filter((id) => id !== null)
			.map((id) => {
				const p = products.get(id);
				return p ? `${p.brand} ${p.model}` : "—";
			})
			.join(" + ");
	const names = (candidate: EquipmentCandidate) => {
		const devices = isPlantCandidate(candidate)
			? candidate.plant.units
					.map((unit) => `${unit.name}: ${deviceNames(unit.selection)}`)
					.join(" · ")
			: deviceNames(candidate.selection);
		// The assessment accounts for sales units and the converter voltage window.
		// Older results without that figure keep their device names alone.
		if (typeof candidate.usable_energy_kwh !== "number") return devices;
		const capacity = new Intl.NumberFormat(locale, {
			maximumFractionDigits: 1,
		}).format(candidate.usable_energy_kwh);
		return `${devices} · ${__("Usable battery capacity", "linker-tools")}: ${capacity} kWh`;
	};
	const applySelected = async () => {
		if (
			!candidate ||
			busy ||
			disabled ||
			differentArrangement ||
			alreadyAdopted
		)
			return;
		setBusy(true);
		try {
			await apply(candidate);
		} catch (cause) {
			if (client.isCurrentScope(scope)) onError(cause);
		} finally {
			if (client.isCurrentScope(scope)) setBusy(false);
		}
	};
	return (
		<EquipmentResult
			run={run}
			locale={locale}
			dirty={dirty}
			confirmedRevision={confirmedRevision}
			assessmentOverride={detail.data ?? null}
			certificateSources={
				candidate && (
					<CertificateEvidence
						client={client}
						scope={scope}
						run={run}
						candidate={candidate}
					/>
				)
			}
		>
			{search && (
				<section className="sc-work-panel sc-equipment-candidates">
					<header className="sc-work-panel-heading">
						<div>
							<h3>{__("Equipment combination", "linker-tools")}</h3>
							<p className="sc-field-help">
								{search.completion === "budget_exhausted"
									? __(
											"Search incomplete: the search limit was reached. Some configurations remain unchecked.",
											"linker-tools",
										)
									: __(
											"Search complete within the stated scope.",
											"linker-tools",
										)}
							</p>
						</div>
						<p className="sc-equipment-count">
							{__("Combinations assessed", "linker-tools")}:{" "}
							{new Intl.NumberFormat(locale).format(candidates.length)}
						</p>
					</header>
					<div className="sc-work-panel-body">
						{differentArrangement && (
							<Notice>
								{__(
									"This result is for a different system arrangement. Choose the matching arrangement before using a combination.",
									"linker-tools",
								)}
							</Notice>
						)}
						<details className="sc-disclosure">
							<summary>{__("Search scope", "linker-tools")}</summary>
							<p>
								{plantSearch
									? __(
											"The search uses the system count, requirements for each system and coordination groups you have declared. It checks equipment combinations from current product data for each system and the project, counting one shared controller per group. It does not compare alternative system counts or different allocations of project requirements, or simulate joint energy flows. Unresolved conditions remain shown in the results.",
											"linker-tools",
										)
									: __(
											"This search assesses combinations of one inverter and one external battery assembly. Parallel inverter systems, multiple battery ports and integrated storage systems require separate assessment.",
											"linker-tools",
										)}
							</p>
						</details>
						{Object.values(readObject(readObject(search.coverage).gaps)).some(
							(v) => typeof v === "number" && v > 0,
						) && (
							<Notice>
								{__(
									"Some products or combinations lack the supporting data needed for this search.",
									"linker-tools",
								)}
							</Notice>
						)}
						{search.demand !== undefined && (
							<label className="sc-field">
								<span>{__("Demand results", "linker-tools")}</span>
								<select
									value={demandFilter}
									onChange={(event) =>
										setDemandFilter(event.currentTarget.value)
									}
								>
									<option value="all">
										{__("All combinations", "linker-tools")}
									</option>
									<option value="satisfied">
										{__("Meets the declared demand", "linker-tools")}
									</option>
									<option value="violated">
										{__("Does not meet the declared demand", "linker-tools")}
									</option>
									<option value="unresolved">
										{__("Demand not assessed", "linker-tools")}
									</option>
								</select>
							</label>
						)}
						{search.demand !== undefined &&
							readObject(search.demand).completion === "budget_exhausted" && (
								<Notice>
									{__(
										"Demand comparison is incomplete. Some combinations have not been simulated.",
										"linker-tools",
									)}
								</Notice>
							)}
						<div className="sc-work-grid sc-equipment-candidate-picker">
							{visibleCandidates.length === 0 ? (
								<Notice>
									{candidates.length > 0
										? __(
												"No combinations match this demand filter.",
												"linker-tools",
											)
										: __(
												"No combinations were found using the available documented configurations.",
												"linker-tools",
											)}
								</Notice>
							) : (
								<label className="sc-field sc-work-main">
									<span>{__("Equipment combination", "linker-tools")}</span>
									<select
										value={candidate?.id ?? ""}
										onChange={(event) => {
											setSelected(event.currentTarget.value);
										}}
									>
										{["satisfied", "unresolved", "violated"]
											.filter((status) =>
												visibleCandidates.some((c) => c.status === status),
											)
											.map((status) => (
												<optgroup key={status} label={equipmentStatus(status)}>
													{visibleCandidates
														.filter((c) => c.status === status)
														.map((c) => (
															<option key={c.id} value={c.id}>
																{names(c)}
															</option>
														))}
												</optgroup>
											))}
									</select>
								</label>
							)}
							{candidate && (
								<div className="sc-work-aside sc-work-toolbar">
									<button
										className="sc-button sc-primary"
										type="button"
										disabled={
											disabled ||
											busy ||
											!detail.data ||
											detail.isFetching ||
											differentArrangement ||
											alreadyAdopted
										}
										onClick={() => void applySelected()}
									>
										{__("Use this combination in the project", "linker-tools")}
									</button>
								</div>
							)}
						</div>
						{candidate?.demand && (
							<section className="sc-work-panel">
								<h4>{__("Energy demand comparison", "linker-tools")}</h4>
								<p>
									{candidate.demand.status === "satisfied"
										? __("Meets the declared demand", "linker-tools")
										: candidate.demand.status === "violated"
											? __("Does not meet the declared demand", "linker-tools")
											: __("Demand not assessed", "linker-tools")}
								</p>
								{candidate.demand.reason ===
									"usable_energy_not_established" && (
									<p>
										{__(
											"Documented usable capacity is missing for this combination.",
											"linker-tools",
										)}
									</p>
								)}
								{candidate.demand.reason === "work_budget_exhausted" && (
									<p>
										{__(
											"This combination was not simulated because the comparison limit was reached.",
											"linker-tools",
										)}
									</p>
								)}
								{candidate.demand.reason === "scenario_not_feasible" && (
									<p>
										{__(
											"This simulation did not meet the declared storage, reserve or end-state constraints.",
											"linker-tools",
										)}
									</p>
								)}
								{candidate.demand.metrics && (
									<dl className="sc-field-summary">
										<dt>{__("Unserved load", "linker-tools")}</dt>
										<dd>
											{new Intl.NumberFormat(locale, {
												maximumFractionDigits: 3,
											}).format(
												candidate.demand.metrics.unserved_load_kwh as number,
											)}{" "}
											kWh
										</dd>
										<dt>
											{__(
												"Maximum interval-average grid import",
												"linker-tools",
											)}
										</dt>
										<dd>
											{new Intl.NumberFormat(locale, {
												maximumFractionDigits: 3,
											}).format(
												candidate.demand.metrics
													.maximum_interval_average_import_kw as number,
											)}{" "}
											kW
										</dd>
									</dl>
								)}
								{candidate.demand.equipment &&
									readObject(candidate.demand.equipment.assessment)
										.overall_status === "unresolved" && (
										<p>
											{__(
												"Equipment evidence remains unresolved for the simulated operating conditions.",
												"linker-tools",
											)}
										</p>
									)}
								{candidate.demand.equipment &&
									readObject(candidate.demand.equipment.assessment)
										.overall_status === "violated" && (
										<Notice error>
											{__(
												"The simulated operating conditions exceed the equipment evidence. Review the power and capacity assumptions.",
												"linker-tools",
											)}
										</Notice>
									)}
							</section>
						)}
						{detail.error && (
							<Notice error>
								{__(
									"The combination details could not be loaded.",
									"linker-tools",
								)}
							</Notice>
						)}
					</div>
				</section>
			)}
		</EquipmentResult>
	);
}
