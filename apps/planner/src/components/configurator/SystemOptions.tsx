import { CountryRuleResult } from "../equipment/CountryRuleResult.tsx";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { PlanningRun } from "../../data/planningProtocol.ts";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import type { JsonObject } from "../../data/protocol.ts";
import type { EquipmentCandidate } from "../../data/equipmentSearch.ts";
import {
	isPlantCandidate,
	readEquipmentCandidate,
	readRetainedInverter,
} from "../../data/equipmentSearch.ts";
import { readObject } from "../../data/readProtocol.ts";
import type { EquipmentSelection } from "../../domain/equipment.ts";
import { sameJson } from "../../domain/draft.ts";
import {
	equipmentCheckLabel,
	equipmentReason,
	equipmentStatus,
} from "../equipment/equipmentLabels.ts";
import { ProductCard } from "../shared/ProductCard.tsx";
import { CatalogStatus } from "../shared/CatalogStatus.tsx";
import { useProductCards } from "../../data/productCards.ts";
import { AssessmentSources } from "../equipment/AssessmentSources.tsx";
import { Icon } from "../Icon.tsx";
import { __, sprintf } from "../../i18n.ts";

const productName = (product: JsonObject | undefined) =>
	product
		? [product.brand, product.model]
				.filter((value) => typeof value === "string" && value)
				.join(" ") || __("Product identity not recorded", "linker-tools")
		: __("Product identity not recorded", "linker-tools");

function assessmentQuery(
	client: PlannerClient,
	scope: string,
	run: PlanningRun | null,
	candidate?: EquipmentCandidate,
) {
	return {
		queryKey: [
			"configurator-system-option",
			scope,
			run?.id,
			candidate?.id,
			candidate?.assessment_sha256,
		],
		enabled:
			run?.state === "succeeded" && !!candidate && client.isCurrentScope(scope),
		retry: false as const,
		staleTime: Infinity,
		queryFn: async ({ signal }: { signal: AbortSignal }) =>
			readEquipmentCandidate(
				await client.query(
					"equipment/candidates/read",
					{
						schema_version: 1,
						run_id: run!.id,
						candidate_id: candidate!.id,
					},
					scope,
					signal,
				),
				run!.id,
				candidate!,
			),
	};
}

export function useCandidateAssessment(
	client: PlannerClient,
	scope: string,
	run: PlanningRun | null,
	candidate?: EquipmentCandidate,
) {
	return useQuery(assessmentQuery(client, scope, run, candidate));
}

export function CandidateMaterials({
	client,
	scope,
	candidate,
	assessment,
	locale,
}: {
	client: PlannerClient;
	scope: string;
	candidate: EquipmentCandidate;
	assessment: JsonObject;
	locale: string;
}) {
	const format = (value: number) => new Intl.NumberFormat(locale).format(value);
	const selectedProducts = new Map(
		((assessment?.selected_products ?? []) as JsonObject[]).map((product) => [
			product.product_id,
			product,
		]),
	);
	const useLabel = (use: string) =>
		use === "retain"
			? __("Retained on site", "linker-tools")
			: use === "replace"
				? __("Replacement equipment", "linker-tools")
				: __("New equipment", "linker-tools");
	const selection = isPlantCandidate(candidate) ? null : candidate.selection;
	const part = assessment;
	const lines = part.provisional_bill_of_materials as JsonObject[];
	const cards = useProductCards(
		client,
		scope,
		locale,
		lines.map((row) => Number(row.product_id)),
	);
	return (
		<>
			<CatalogStatus
				pending={cards.isPending && lines.length > 0}
				failed={cards.isError}
				retry={() => void cards.refetch()}
			/>
			{lines.map((line, index) => {
				let use = "new";
				if (selection) {
					if (line.product_id === selection.inverter_product_id)
						use = selection.equipment_use?.inverter ?? "new";
					else if (line.product_id === selection.battery_product_id)
						use = selection.equipment_use?.battery ?? "new";
				}
				const controllerGroups =
					candidate && isPlantCandidate(candidate)
						? candidate.plant.parallel_groups.filter(
								(group) => group.controller_product_id === line.product_id,
							)
						: [];
				const allocations =
					!selection && Array.isArray(part.systems)
						? (part.systems as JsonObject[]).flatMap((system) => {
								const unitSelection = readObject(
									system.selection,
								) as EquipmentSelection;
								const unitBill = readObject(system.assessment)
									.provisional_bill_of_materials as JsonObject[];
								return unitBill
									.filter((unitLine) => unitLine.product_id === line.product_id)
									.map((unitLine) => ({
										name: String(system.name),
										quantity: unitLine.quantity,
										use:
											line.product_id === unitSelection.inverter_product_id
												? (unitSelection.equipment_use?.inverter ?? "new")
												: line.product_id === unitSelection.battery_product_id
													? (unitSelection.equipment_use?.battery ?? "new")
													: "new",
									}));
							})
						: [];
				const product = { ...selectedProducts.get(line.product_id), ...line };
				const card = cards.isSuccess
					? cards.data.get(Number(line.product_id))
					: undefined;
				return (
					<div className="sc-equipment sc-material-row" key={index}>
						<ProductCard
							{...card}
							label={productName(product)}
							quantity={
								line.quantity === null
									? __("Quantity to confirm", "linker-tools")
									: `× ${format(Number(line.quantity))}`
							}
						>
							{cards.isSuccess && !card && (
								<small>{__("Saved product unavailable", "linker-tools")}</small>
							)}
							{typeof product.sku === "string" && (
								<p className="sc-muted">{product.sku}</p>
							)}
							{allocations.map((allocation, i) => (
								<p key={i}>
									{allocation.name} · {useLabel(allocation.use)} ·{" "}
									{allocation.quantity === null
										? __("Quantity to confirm", "linker-tools")
										: `× ${format(Number(allocation.quantity))}`}
								</p>
							))}
							{controllerGroups.map((group) => (
								<p key={group.id}>
									{__("Shared controller", "linker-tools")} ·{" "}
									{useLabel(group.controller_use ?? "new")}
								</p>
							))}
							{!allocations.length && !controllerGroups.length && (
								<p>{useLabel(use)}</p>
							)}
						</ProductCard>
					</div>
				);
			})}
		</>
	);
}

export interface SystemComparison {
	run: PlanningRun;
	candidate: EquipmentCandidate;
}

const adjustmentFields = [
	"inverter_product_id",
	"battery_product_id",
	"modules_per_stack",
	"parallel_stacks",
] as const;

const systems = (item: EquipmentCandidate) =>
	isPlantCandidate(item)
		? item.plant.units
		: [{ id: "system", name: "", selection: item.selection }];

type AdjustmentField = (typeof adjustmentFields)[number];

function adjustmentOptions(
	candidates: EquipmentCandidate[],
	current: EquipmentCandidate,
	unitIndex: number,
	field: AdjustmentField,
) {
	const units = systems(current);
	const unit = units[unitIndex]!;
	const options = new Map([[String(unit.selection[field] ?? ""), current]]);
	const fixed =
		field === "inverter_product_id"
			? []
			: field === "battery_product_id"
				? (["inverter_product_id"] as const)
				: adjustmentFields.filter((key) => key !== field);
	for (const candidate of candidates) {
		const alternatives = systems(candidate);
		if (alternatives.length !== units.length) continue;
		const sameOtherUnits = alternatives.every(
			(alternative, index) =>
				alternative.id === units[index]!.id &&
				(index === unitIndex ||
					sameJson(alternative.selection, units[index]!.selection)),
		);
		if (!sameOtherUnits) continue;
		const alternative = alternatives[unitIndex]!.selection;
		if (!fixed.every((key) => alternative[key] === unit.selection[key]))
			continue;
		const value = String(alternative[field] ?? "");
		if (!options.has(value)) options.set(value, candidate);
	}
	return options;
}

function fitRank(item: EquipmentCandidate, backupEnergy: number | null) {
	if (item.status === "violated" || item.demand?.status === "violated")
		return 3;
	if (backupEnergy !== null) {
		if (typeof item.usable_energy_kwh !== "number") return 2;
		if (item.usable_energy_kwh < backupEnergy) return 3;
	}
	return item.status === "satisfied" &&
		(item.demand === undefined || item.demand.status === "satisfied")
		? 0
		: 1;
}

function compareFit(
	left: EquipmentCandidate,
	right: EquipmentCandidate,
	backupEnergy: number | null,
) {
	const rank = fitRank(left, backupEnergy) - fitRank(right, backupEnergy);
	if (rank) return rank;
	const distances = (candidate: EquipmentCandidate) => {
		const targets = isPlantCandidate(candidate)
			? candidate.plant.requirements
			: candidate.selection;
		const pv =
			typeof targets.pv_dc_kw === "number" && targets.pv_dc_kw > 0
				? targets.pv_dc_kw
				: 0;
		const load =
			typeof targets.required_discharge_ac_kw === "number"
				? targets.required_discharge_ac_kw
				: 0;
		const kw = Math.max(pv, load);
		const kwh = Math.max(
			backupEnergy ?? 0,
			typeof targets.required_usable_kwh === "number"
				? targets.required_usable_kwh
				: 0,
		);
		const ac = candidate.nominal_ac_kw,
			energy = candidate.usable_energy_kwh;
		return [
			kw ? (typeof ac === "number" ? Math.abs(ac - kw) : Infinity) : 0,
			kw && typeof ac === "number" && ac < kw ? 1 : 0,
			kwh
				? typeof energy === "number"
					? Math.abs(energy - kwh)
					: Infinity
				: 0,
		];
	};
	const a = distances(left),
		b = distances(right);
	for (const [i, value] of a.entries()) {
		if (value !== b[i]) return value < b[i]! ? -1 : 1;
	}
	return 0;
}

function readCountryReview(assessment: JsonObject): JsonObject | undefined {
	const units = Array.isArray(assessment.systems) ? assessment.systems : [];
	const first = units.length
		? readObject(readObject(units[0]).assessment)
		: assessment;
	const country = first.country_assessment;
	if (!country) return undefined;
	const review = readObject(country).rule_review;
	return review ? readObject(review) : undefined;
}

export function SystemOptions({
	solarOnly,
	guided = false,
	run,
	client,
	scope,
	locale,
	disabled,
	selectedId,
	comparison,
	onSaveComparison,
	onEditEquipment,
	onReview,
	onSelectionPending,
	onSelect,
}: {
	solarOnly: boolean;
	guided?: boolean;
	run: PlanningRun;
	client: PlannerClient;
	scope: string;
	locale: string;
	disabled: boolean;
	selectedId: string | null;
	comparison?: SystemComparison | null;
	onSaveComparison?: (snapshot: SystemComparison) => void;
	onEditEquipment?: () => void;
	onReview?: () => void;
	onSelectionPending?: (pending: boolean) => void;
	onSelect: (
		candidate: EquipmentCandidate,
		source: PlanningRun,
	) => Promise<void>;
}) {
	const search = run.result?.search ? readObject(run.result.search) : null;
	const candidates = (search?.candidates ?? []) as EquipmentCandidate[];
	const demand = search?.demand ? readObject(search.demand) : null;
	const bounded = demand?.model === "profile_physical_bounds_v1";
	const baseline = bounded ? readObject(demand.baseline) : null;
	const backup = search?.backup_demand
		? readObject(search.backup_demand)
		: null;
	const backupEnergy =
		typeof backup?.ac_load_energy_kwh === "number"
			? backup.ac_load_energy_kwh
			: null;
	const products = new Map(
		((search?.products ?? []) as JsonObject[]).map((product) => [
			product.canonical_product_id,
			product,
		]),
	);
	const [preview, setPreview] = useState<{
		runId: string;
		candidateId: string;
	} | null>(null);
	const [filter, setFilter] = useState("all");
	const [term, setTerm] = useState("");
	const [showSources, setShowSources] = useState(false);
	const [page, setPage] = useState(0);
	const [order, setOrder] = useState("fit");
	const cache = useQueryClient();
	const [selecting, setSelecting] = useState(false);
	const [selectionError, setSelectionError] = useState(false);
	const currentScope = client.isCurrentScope(scope);
	const selected = candidates.find((item) => item.id === selectedId);
	const ranked = [...candidates].sort((a, b) => compareFit(a, b, backupEnergy));
	const candidate =
		candidates.find(
			(item) => preview?.runId === run.id && item.id === preview.candidateId,
		) ??
		selected ??
		ranked[0];
	const saved =
		comparison?.run.project_id === run.project_id ? comparison : null;
	const detail = useCandidateAssessment(client, scope, run, candidate);
	const assessment = currentScope ? detail.data : undefined;
	const countryReview = assessment && readCountryReview(assessment);
	const format = (value: number) =>
		new Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(value);
	const capacity = (item: EquipmentCandidate) =>
		typeof item.usable_energy_kwh === "number"
			? `${format(item.usable_energy_kwh)} kWh`
			: __("Usable capacity to confirm", "linker-tools");
	const devices = (selection: EquipmentSelection, catalog = products) => {
		const inverter = productName(catalog.get(selection.inverter_product_id));
		if (!selection.battery_product_id) return inverter;
		const battery = productName(catalog.get(selection.battery_product_id));
		return [inverter, battery].join(" + ");
	};
	const title = (item: EquipmentCandidate, catalog = products) =>
		systems(item)
			.map((unit) =>
				unit.name
					? `${unit.name}: ${devices(unit.selection, catalog)}`
					: devices(unit.selection, catalog),
			)
			.join(" · ");
	const savedProducts = saved
		? new Map(
				(readObject(saved.run.result!.search).products as JsonObject[]).map(
					(product) => [product.canonical_product_id, product],
				),
			)
		: products;
	const measure = (value: unknown, unit: string) =>
		typeof value === "number" ? `${format(value)} ${unit}` : "—";
	function optionMetrics(item: EquipmentCandidate) {
		const metrics = item.demand?.metrics;
		if (!metrics) return null;
		const ratio = metrics.pv_input_self_use;
		const selfUse =
			ratio && typeof ratio === "object" && "value" in ratio
				? ratio.value
				: null;
		const energy = (value: unknown) =>
			typeof value === "number"
				? value >= 1000
					? format(value / 1000) + " MWh"
					: format(value) + " kWh"
				: null;
		const rows = [
			[
				__("PV generation", "linker-tools"),
				energy(metrics.pv_generated_ac_kwh),
			],
			[
				__("Self-use", "linker-tools"),
				typeof selfUse === "number"
					? new Intl.NumberFormat(locale, {
							style: "percent",
							maximumFractionDigits: 1,
						}).format(selfUse)
					: null,
			],
			[__("Grid import", "linker-tools"), energy(metrics.grid_import_kwh)],
		].filter((row) => row[1] !== null);
		return rows.length ? (
			<dl
				className="sc-option-metrics"
				aria-label={__("Calculated for the supplied period", "linker-tools")}
			>
				{rows.map(([label, value]) => (
					<div key={label}>
						<dt>{label}</dt>
						<dd>{value}</dd>
					</div>
				))}
			</dl>
		) : null;
	}
	const bounds = (item: EquipmentCandidate) => {
		if (!bounded || !item.demand) return null;
		const facts = readObject(item.demand);
		return (
			<>
				{typeof facts.additional_pv_use_upper_kwh === "number" && (
					<p>
						{__("Additional solar use, upper bound", "linker-tools")}:{" "}
						<strong>{format(facts.additional_pv_use_upper_kwh)} kWh</strong>
					</p>
				)}
				{typeof facts.peak_import_lower_bound_kw === "number" && (
					<p>
						{__("Grid import peak, lower bound", "linker-tools")}:{" "}
						<strong>{format(facts.peak_import_lower_bound_kw)} kW</strong>
					</p>
				)}
				{facts.status === "violated" && (
					<p>
						{__(
							"The peak target exceeds this configuration's optimistic physical limit.",
							"linker-tools",
						)}
					</p>
				)}
				{facts.status === "unresolved" && (
					<p className="sc-muted">
						{__(
							"Demand bounds could not be established for this configuration.",
							"linker-tools",
						)}
					</p>
				)}
			</>
		);
	};
	const filtered = candidates
		.filter(
			(item) =>
				(filter === "all" || item.status === filter) &&
				title(item)
					.toLocaleLowerCase(locale)
					.includes(term.toLocaleLowerCase(locale).trim()),
		)
		.sort((left, right) => {
			if (order === "fit") return compareFit(left, right, backupEnergy);
			const a = left.usable_energy_kwh;
			const b = right.usable_energy_kwh;
			if (typeof a !== "number") return typeof b === "number" ? 1 : 0;
			if (typeof b !== "number") return -1;
			return order === "capacity-asc" ? a - b : b - a;
		});
	const pageSize = 3;
	const pages = Math.max(1, Math.ceil(filtered.length / pageSize));
	const shownPage = Math.min(page, pages - 1);
	const shown = filtered.slice(
		shownPage * pageSize,
		(shownPage + 1) * pageSize,
	);
	const optionIds = (item: EquipmentCandidate) => [
		...new Set(
			systems(item).flatMap(({ selection }) =>
				[selection.inverter_product_id, selection.battery_product_id].filter(
					(id): id is number => typeof id === "number",
				),
			),
		),
	];
	const shop = useProductCards(client, scope, locale, shown.flatMap(optionIds));
	const checks = (part: JsonObject, key: string) =>
		(part.checks as JsonObject[]).map((check, index) => {
			const documents = [
				...((check.documents ?? []) as JsonObject[]),
				...((check.facts ?? []) as JsonObject[]).flatMap((fact) =>
					fact.source ? [readObject(fact.source)] : [],
				),
			];
			const plantBackup = check.id === "plant:backup_runtime";
			const actual = plantBackup ? readObject(check.actual) : {};
			const required = plantBackup ? readObject(check.required) : {};
			const backupRows = plantBackup
				? ([
						[__("Backup load", "linker-tools"), required.load_kw, "kW"],
						[
							__("Required duration", "linker-tools"),
							required.duration_hours,
							"h",
						],
						[
							__("Backup load energy before losses", "linker-tools"),
							required.ac_load_energy_kwh,
							"kWh",
						],
						[
							__("Backup power upper bound", "linker-tools"),
							actual.discharge_upper_bound_kw,
							"kW",
						],
						[
							__("Usable battery capacity", "linker-tools"),
							actual.usable_energy_kwh,
							"kWh",
						],
					] as const)
				: [];
			return (
				<li key={`${key}-${index}`}>
					<strong>
						{plantBackup
							? __("Whole-site backup", "linker-tools")
							: equipmentCheckLabel(String(check.semantic_id ?? check.id))}
					</strong>
					{(check.semantic_id ?? check.id) === "pv_dc_input" &&
						typeof check.required === "number" && (
							<span>{measure(check.required, "kWp")}</span>
						)}
					<span className="sc-check-status" data-status={String(check.status)}>
						{equipmentStatus(String(check.status))}
					</span>
					{plantBackup ? (
						<>
							<dl className="sc-fields">
								{backupRows.map(([label, value, unit]) =>
									typeof value === "number" ? (
										<div key={label}>
											<dt>{label}</dt>
											<dd>
												{format(value)} {unit}
											</dd>
										</div>
									) : null,
								)}
							</dl>
							{check.status === "unresolved" && (
								<p>
									{__(
										"Confirm shared backup transfer, starting charge and discharge losses.",
										"linker-tools",
									)}
								</p>
							)}
						</>
					) : (
						<p>{equipmentReason(String(check.reason))}</p>
					)}
					{documents.some((source) => source.kind === "user_declared") && (
						<p>
							{__("Panel parameters entered for this project", "linker-tools")}
						</p>
					)}
				</li>
			);
		});
	async function select(item: EquipmentCandidate, source = run) {
		if (
			disabled ||
			selecting ||
			!client.isCurrentScope(scope) ||
			(source.id === run.id && item.id === selectedId)
		)
			return;
		setSelecting(true);
		onSelectionPending?.(true);
		setSelectionError(false);
		setPreview({ runId: source.id, candidateId: item.id });
		try {
			await cache.fetchQuery(assessmentQuery(client, scope, source, item));
			if (client.isCurrentScope(scope)) await onSelect(item, source);
		} catch {
			if (client.isCurrentScope(scope)) {
				setPreview(null);
				setSelectionError(true);
			}
		} finally {
			setSelecting(false);
			onSelectionPending?.(false);
		}
	}
	if (!currentScope)
		return (
			<p className="sc-muted">
				{__(
					"Sign in or refresh your session to view these configurations.",
					"linker-tools",
				)}
			</p>
		);
	if (run.state !== "succeeded")
		return (
			<p role="status" className="sc-muted">
				{run.state === "failed" || run.state === "cancelled"
					? __(
							"The system search did not finish. Review your requirements and try again.",
							"linker-tools",
						)
					: __(
							"Finding equipment configurations for your project…",
							"linker-tools",
						)}
			</p>
		);
	if (run.result?.retained_inverter) {
		const { existing, requirements, units, profile } = readRetainedInverter(
			run.result.retained_inverter,
		);
		const demandRows = (values: JsonObject) =>
			[
				[__("Installed PV power", "linker-tools"), values.pv_dc_kw, "kWp"],
				[
					__("Required usable storage", "linker-tools"),
					values.required_usable_kwh,
					"kWh",
				],
				[
					__("Required discharge power", "linker-tools"),
					values.required_discharge_ac_kw,
					"kW",
				],
			].flatMap(([label, value, unit]) =>
				typeof value === "number"
					? [
							<div key={String(label)}>
								<dt>{String(label)}</dt>
								<dd>
									{format(value)} {String(unit)}
								</dd>
							</div>,
						]
					: [],
			);
		const connectionRows = (values: JsonObject) => (
			<>
				{typeof values.grid_phase === "number" && (
					<div>
						<dt>{__("Grid phases", "linker-tools")}</dt>
						<dd>{values.grid_phase}</dd>
					</div>
				)}
				{values.operating_mode && (
					<div>
						<dt>{__("Operating mode", "linker-tools")}</dt>
						<dd>
							{values.operating_mode === "backup"
								? __("Backup", "linker-tools")
								: __("Grid-connected", "linker-tools")}
						</dd>
					</div>
				)}
			</>
		);
		return (
			<section className="sc-card">
				<h2>{__("Keep the existing inverter", "linker-tools")}</h2>
				<p>
					{String(existing.name)}
					{typeof existing.inverter_power_kw === "number"
						? ` · ${format(existing.inverter_power_kw)} kW`
						: ""}
				</p>
				<h3>{__("Declared project requirements", "linker-tools")}</h3>
				<dl className="sc-equipment">
					{demandRows(requirements)}
					{connectionRows(requirements)}
				</dl>
				{units.map((unit) => (
					<div key={unit.id}>
						<h4>{unit.name}</h4>
						<dl className="sc-equipment">{demandRows(unit.requirements)}</dl>
					</div>
				))}
				{profile && (
					<>
						<h3>{__("Your demand profile", "linker-tools")}</h3>
						<p className="sc-muted">
							{__("Profile period (UTC)", "linker-tools")}:{" "}
							{String(profile.demand.horizon_start_utc)} –{" "}
							{String(profile.demand.horizon_end_utc)}
						</p>
						<dl className="sc-fields">
							{(
								[
									[__("Electricity use", "linker-tools"), "load_kwh", "kWh"],
									[
										__("Direct solar use", "linker-tools"),
										"direct_pv_use_kwh",
										"kWh",
									],
									[
										__("Grid import without storage", "linker-tools"),
										"grid_import_kwh",
										"kWh",
									],
									[
										__("Grid import peak without storage", "linker-tools"),
										"peak_grid_import_kw",
										"kW",
									],
								] as const
							).map(([label, key, unit]) => {
								const value = profile.baseline[key];
								return typeof value === "number" ? (
									<div key={key}>
										<dt>{label}</dt>
										<dd>
											{format(value)} {unit}
										</dd>
									</div>
								) : null;
							})}
						</dl>
					</>
				)}

				<p>
					{__(
						"Confirm the inverter model to check battery, grid and backup compatibility.",
						"linker-tools",
					)}
				</p>
			</section>
		);
	}

	return (
		<section className="sc-system-options">
			<header className="sc-section-head">
				<div>
					<h2>{__("A system for this project", "linker-tools")}</h2>
					<p>
						{guided
							? __(
									"Choose an option to review it and send an inquiry.",
									"linker-tools",
								)
							: __(
									"Compare the equipment, then adjust the configuration.",
									"linker-tools",
								)}
					</p>
				</div>
				{onSaveComparison && (
					<button
						type="button"
						className="sc-button"
						disabled={disabled || selecting || !selected || !assessment}
						onClick={() =>
							selected && onSaveComparison({ run, candidate: selected })
						}
					>
						{__("Save a comparison", "linker-tools")}
					</button>
				)}
			</header>
			{search?.completion === "budget_exhausted" && (
				<p role="status" className="sc-muted">
					{__(
						"Search incomplete: some configurations remain unchecked.",
						"linker-tools",
					)}
				</p>
			)}
			{candidates.length > 0 &&
				!candidates.some((item) => fitRank(item, backupEnergy) === 0) && (
					<p className="sc-note">
						{candidates.every((item) => fitRank(item, backupEnergy) === 3)
							? __(
									"Each option falls short of a project requirement. Review the checks before choosing equipment.",
									"linker-tools",
								)
							: __(
									"Some checks are still open. Review the equipment and local grid requirements for your chosen option.",
									"linker-tools",
								)}
					</p>
				)}
			{backupEnergy !== null &&
				typeof backup?.load_kw === "number" &&
				typeof backup.duration_hours === "number" && (
					<p>
						{__("Backup load energy before losses", "linker-tools")}:{" "}
						{format(backup.load_kw)} kW × {format(backup.duration_hours)} h ={" "}
						{format(backupEnergy)} kWh
					</p>
				)}
			{bounded && baseline && (
				<section className="sc-card">
					<h3>{__("Your demand profile", "linker-tools")}</h3>
					<p className="sc-muted">
						{__("Profile period (UTC)", "linker-tools")}:{" "}
						{String(demand.horizon_start_utc)} –{" "}
						{String(demand.horizon_end_utc)}
					</p>
					<dl className="sc-fields">
						<div>
							<dt>{__("Electricity use", "linker-tools")}</dt>
							<dd>
								{typeof baseline.load_kwh === "number"
									? `${format(baseline.load_kwh)} kWh`
									: "—"}
							</dd>
						</div>
						<div>
							<dt>{__("Direct solar use", "linker-tools")}</dt>
							<dd>
								{typeof baseline.direct_pv_use_kwh === "number"
									? `${format(baseline.direct_pv_use_kwh)} kWh`
									: "—"}
							</dd>
						</div>
						<div>
							<dt>{__("Grid import without storage", "linker-tools")}</dt>
							<dd>
								{typeof baseline.grid_import_kwh === "number"
									? `${format(baseline.grid_import_kwh)} kWh`
									: "—"}
							</dd>
						</div>
						{typeof demand.peak_target_kw === "number" && (
							<div>
								<dt>{__("Target grid import limit", "linker-tools")}</dt>
								<dd>{format(demand.peak_target_kw)} kW</dd>
							</div>
						)}
						<div>
							<dt>{__("Grid import peak without storage", "linker-tools")}</dt>
							<dd>
								{typeof baseline.peak_grid_import_kw === "number"
									? `${format(baseline.peak_grid_import_kw)} kW`
									: "—"}
							</dd>
						</div>
					</dl>
					{candidates.some(
						(candidate) =>
							typeof candidate.demand?.additional_pv_use_upper_kwh === "number",
					) && (
						<p className="sc-muted">
							{__(
								"Only surplus solar energy stored during this period counts towards the upper bound. The calculation assumes lossless storage.",
								"linker-tools",
							)}
						</p>
					)}
					{candidates.some(
						(candidate) =>
							typeof candidate.demand?.peak_import_lower_bound_kw === "number",
					) && (
						<p className="sc-muted">
							{__(
								"The lower bound assumes a full battery at the start and lossless storage.",
								"linker-tools",
							)}
						</p>
					)}
				</section>
			)}
			{candidates.length > 0 && (
				<details className="sc-product-filter">
					<summary>{__("Find a product", "linker-tools")}</summary>
					<div className="sc-fields">
						<label className="sc-field">
							<span>{__("Find a product", "linker-tools")}</span>
							<input
								type="search"
								value={term}
								onChange={(event) => {
									setTerm(event.currentTarget.value);
									setPage(0);
								}}
							/>
						</label>
						<label className="sc-field">
							<span>{__("Assessment status", "linker-tools")}</span>
							<select
								value={filter}
								onChange={(event) => {
									setFilter(event.currentTarget.value);
									setPage(0);
								}}
							>
								<option value="all">
									{__("All configurations", "linker-tools")}
								</option>
								{["satisfied", "unresolved", "violated"].map((status) => (
									<option key={status} value={status}>
										{equipmentStatus(status)} (
										{candidates.filter((item) => item.status === status).length}
										)
									</option>
								))}
							</select>
						</label>
						{!solarOnly && (
							<label className="sc-field">
								<span>{__("Sort configurations", "linker-tools")}</span>
								<select
									value={order}
									onChange={(event) => {
										setOrder(event.currentTarget.value);
										setPage(0);
									}}
								>
									<option value="fit">
										{__("Requirements first", "linker-tools")}
									</option>
									<option value="capacity-asc">
										{__("Lowest usable battery capacity", "linker-tools")}
									</option>
									<option value="capacity-desc">
										{__("Highest usable battery capacity", "linker-tools")}
									</option>
								</select>
							</label>
						)}
					</div>
				</details>
			)}
			<CatalogStatus
				pending={shown.length > 0 && shop.isPending}
				failed={shop.isError}
				retry={() => void shop.refetch()}
			/>
			<div className="sc-comparison">
				{shown.map((item) => (
					<article
						className="sc-package"
						data-selected={item.id === selectedId ? "true" : undefined}
						key={item.id}
					>
						<div className="sc-option-products" aria-label={title(item)}>
							{optionIds(item).map((id) => {
								const card = shop.isSuccess ? shop.data.get(id) : undefined;
								return (
									<ProductCard
										key={id}
										{...card}
										label={productName(products.get(id))}
									>
										{shop.isSuccess && !card && (
											<small>
												{__("Saved product unavailable", "linker-tools")}
											</small>
										)}
									</ProductCard>
								);
							})}
						</div>
						<div className="sc-option-figures">
							{optionMetrics(item)}
							{isPlantCandidate(item) && (
								<p>{item.plant.units.map((unit) => unit.name).join(" · ")}</p>
							)}
							{!solarOnly && (
								<div className="sc-package-capacity">
									<strong
										className={
											typeof item.usable_energy_kwh === "number"
												? undefined
												: "sc-capacity-pending"
										}
									>
										{capacity(item)}
									</strong>
									<span>
										{isPlantCandidate(item)
											? __("Combined usable battery capacity", "linker-tools")
											: __("Usable battery capacity", "linker-tools")}
									</span>
								</div>
							)}
						</div>
						<div className="sc-option-body">
							{systems(item).map(({ id, name, selection }) =>
								selection.modules_per_stack && selection.parallel_stacks ? (
									<p key={id}>
										{name && `${name} · `}
										{sprintf(
											selection.parallel_stacks === 1
												? __("%d stack", "linker-tools")
												: __("%d stacks", "linker-tools"),
											selection.parallel_stacks,
										)}
										{" × "}
										{sprintf(
											selection.modules_per_stack === 1
												? __("%d battery module", "linker-tools")
												: __("%d battery modules", "linker-tools"),
											selection.modules_per_stack,
										)}
									</p>
								) : null,
							)}
							<p className="sc-package-status">
								{equipmentStatus(item.status)}
							</p>
							{backupEnergy !== null &&
								typeof item.usable_energy_kwh === "number" && (
									<p>
										{item.usable_energy_kwh < backupEnergy
											? sprintf(
													__(
														"%s kWh below the backup load energy",
														"linker-tools",
													),
													format(backupEnergy - item.usable_energy_kwh),
												)
											: sprintf(
													__(
														"%s kWh capacity margin before losses",
														"linker-tools",
													),
													format(item.usable_energy_kwh - backupEnergy),
												)}
									</p>
								)}
							{backupEnergy !== null &&
								fitRank(item, backupEnergy) !== 0 &&
								fitRank(item, backupEnergy) !== 3 && (
									<p>{__("Backup duration to confirm", "linker-tools")}</p>
								)}
							{bounds(item)}
							<button
								type="button"
								className="sc-button"
								aria-pressed={item.id === selectedId}
								disabled={
									disabled ||
									selecting ||
									item.id === selectedId ||
									(detail.isError && candidate?.id === item.id)
								}
								onClick={() => void select(item)}
							>
								{item.id === selectedId
									? __("Selected", "linker-tools")
									: __("Use this configuration", "linker-tools")}
							</button>
						</div>
					</article>
				))}
			</div>
			{!shown.length && (
				<p className="sc-muted">
					{candidates.length
						? __("No configurations match these filters.", "linker-tools")
						: __(
								"No configurations were found using the available product data.",
								"linker-tools",
							)}
				</p>
			)}
			{pages > 1 && (
				<nav
					className="sc-actions"
					aria-label={__("Configurations", "linker-tools")}
				>
					<button
						type="button"
						className="sc-button"
						disabled={shownPage === 0}
						onClick={() => setPage(shownPage - 1)}
					>
						{__("Previous", "linker-tools")}
					</button>
					<span>
						{sprintf(
							__("Page %1$d of %2$d", "linker-tools"),
							shownPage + 1,
							pages,
						)}
					</span>
					<button
						type="button"
						className="sc-button"
						disabled={shownPage + 1 === pages}
						onClick={() => setPage(shownPage + 1)}
					>
						{__("More configurations", "linker-tools")}
					</button>
				</nav>
			)}
			{candidate && (
				<section className="sc-card sc-system-overview">
					<header className="sc-section-head">
						<div>
							<h2>
								{candidate.id === selectedId
									? __("Selected equipment", "linker-tools")
									: __("Equipment preview", "linker-tools")}
							</h2>
							<p>{title(candidate)}</p>
						</div>
						<p>{equipmentStatus(candidate.status)}</p>
						{candidate.id === selectedId && onReview && (
							<button
								type="button"
								className="sc-button sc-primary"
								disabled={disabled || selecting}
								onClick={onReview}
							>
								{__("Review the proposal", "linker-tools")}
							</button>
						)}
					</header>
					<div role="group" aria-label={__("System layout", "linker-tools")}>
						{systems(candidate).map(({ id, name, selection }) => (
							<div key={id}>
								{name && <h3>{name}</h3>}
								<dl className="sc-system-diagram">
									{typeof selection.pv_dc_kw === "number" &&
										selection.pv_dc_kw > 0 && (
											<div className="sc-system-node">
												<dt>
													<Icon name="solar" />
													{__("Solar capacity", "linker-tools")}
												</dt>
												<dd>{measure(selection.pv_dc_kw, "kWp")}</dd>
											</div>
										)}
									<div className="sc-system-node">
										<dt>
											<Icon name="system" />
											{__("Inverter model", "linker-tools")}
										</dt>
										<dd>
											{productName(products.get(selection.inverter_product_id))}
										</dd>
									</div>
									{!solarOnly && selection.battery_product_id && (
										<div className="sc-system-node">
											<dt>
												<Icon name="energy" />
												{__("Battery model", "linker-tools")}
											</dt>
											<dd>
												{productName(
													products.get(selection.battery_product_id),
												)}
											</dd>
										</div>
									)}
								</dl>
							</div>
						))}
					</div>
					<div className="sc-system-adjustment">
						<h3>{__("Adjust configuration", "linker-tools")}</h3>
						{systems(candidate).map(({ id, name, selection }, index) => (
							<div className="sc-fields" key={id}>
								{adjustmentFields.map((field) => {
									if (solarOnly && field !== "inverter_product_id") return null;
									const labels = {
										inverter_product_id: __("Inverter model", "linker-tools"),
										battery_product_id: __("Battery model", "linker-tools"),
										modules_per_stack: __(
											"Battery modules per stack",
											"linker-tools",
										),
										parallel_stacks: __("Battery stacks", "linker-tools"),
									};
									const options = adjustmentOptions(
										ranked,
										candidate,
										index,
										field,
									);
									const model =
										field === "inverter_product_id" ||
										field === "battery_product_id";
									return (
										<label className="sc-field" key={field}>
											<span>
												{name ? `${name} · ${labels[field]}` : labels[field]}
											</span>
											<select
												value={String(selection[field] ?? "")}
												disabled={disabled || selecting || options.size === 1}
												onChange={(event) => {
													const option = options.get(event.currentTarget.value);
													if (option) void select(option);
												}}
											>
												{[...options.keys()].map((value) => (
													<option key={value} value={value}>
														{value === ""
															? "—"
															: model
																? productName(products.get(Number(value)))
																: format(Number(value))}
													</option>
												))}
											</select>
										</label>
									);
								})}
							</div>
						))}
						{onEditEquipment && (
							<div className="sc-actions">
								<button
									type="button"
									className="sc-button"
									disabled={disabled || selecting}
									onClick={onEditEquipment}
								>
									{__("Edit equipment and system count", "linker-tools")}
								</button>
							</div>
						)}
					</div>

					{detail.isPending && (
						<p role="status" className="sc-muted">
							{__("Loading equipment and evidence…", "linker-tools")}
						</p>
					)}
					{detail.error && (
						<div role="alert">
							<p>
								{__(
									"The equipment details could not be loaded.",
									"linker-tools",
								)}
							</p>
							<button
								type="button"
								className="sc-button"
								onClick={() => void detail.refetch()}
							>
								{__("Try again", "linker-tools")}
							</button>
						</div>
					)}
					{assessment && (
						<>
							<h3>{__("Bill of materials", "linker-tools")}</h3>
							<div className="sc-system-equipment">
								<CandidateMaterials
									client={client}
									scope={scope}
									candidate={candidate}
									assessment={assessment}
									locale={locale}
								/>
							</div>
							<details
								className="sc-selection-evidence"
								onToggle={(event) => setShowSources(event.currentTarget.open)}
							>
								<summary>
									{__("Selection basis and documents", "linker-tools")}
								</summary>
								<p>{equipmentStatus(String(assessment.overall_status))}</p>
								{bounds(candidate)}
								{typeof candidate.demand?.reason === "string" && !bounded && (
									<p>{equipmentReason(candidate.demand.reason)}</p>
								)}
								<ul className="sc-check-list">
									{checks(assessment, "project")}
								</ul>
								{showSources && (
									<AssessmentSources
										assessment={assessment}
										client={client}
										scope={scope}
									/>
								)}
								{Array.isArray(assessment.systems) &&
									(assessment.systems as JsonObject[]).map((system) => (
										<section key={String(system.id)}>
											<h3>{String(system.name)}</h3>
											<ul className="sc-check-list">
												{checks(
													readObject(system.assessment),
													String(system.id),
												)}
											</ul>
										</section>
									))}
								{countryReview ? (
									<CountryRuleResult review={countryReview} locale={locale} />
								) : (
									<p className="sc-muted">
										{__(
											"Country and grid requirements require separate assessment.",
											"linker-tools",
										)}
									</p>
								)}
							</details>
							{selectionError && (
								<p role="alert">
									{__(
										"This configuration could not be selected. Try again.",
										"linker-tools",
									)}
								</p>
							)}
						</>
					)}
				</section>
			)}
			{saved && selected && (
				<section className="sc-card">
					<h3>{__("Compare with the saved version", "linker-tools")}</h3>
					<div className="sc-table-scroll">
						<table>
							<thead>
								<tr>
									<th scope="col">{__("Configuration", "linker-tools")}</th>
									<th scope="col">{__("Saved version", "linker-tools")}</th>
									<th scope="col">{__("Current", "linker-tools")}</th>
								</tr>
							</thead>
							<tbody>
								<tr>
									<th scope="row">{__("Equipment", "linker-tools")}</th>
									<td>{title(saved.candidate, savedProducts)}</td>
									<td>{title(selected)}</td>
								</tr>
								{!solarOnly && (
									<tr>
										<th scope="row">
											{__("Usable battery capacity", "linker-tools")}
										</th>
										<td>{capacity(saved.candidate)}</td>
										<td>{capacity(selected)}</td>
									</tr>
								)}
								<tr>
									<th scope="row">{__("Assessment status", "linker-tools")}</th>
									<td>{equipmentStatus(saved.candidate.status)}</td>
									<td>{equipmentStatus(selected.status)}</td>
								</tr>
								<tr>
									<th scope="row">{__("Inverters", "linker-tools")}</th>
									<td>{format(systems(saved.candidate).length)}</td>
									<td>{format(systems(selected).length)}</td>
								</tr>
								{(typeof saved.candidate.demand?.additional_pv_use_upper_kwh ===
									"number" ||
									typeof selected.demand?.additional_pv_use_upper_kwh ===
										"number") && (
									<tr>
										<th scope="row">
											{__("Additional solar use, upper bound", "linker-tools")}
										</th>
										<td>
											{measure(
												saved.candidate.demand?.additional_pv_use_upper_kwh,
												"kWh",
											)}
										</td>
										<td>
											{measure(
												selected.demand?.additional_pv_use_upper_kwh,
												"kWh",
											)}
										</td>
									</tr>
								)}
								{(typeof saved.candidate.demand?.peak_import_lower_bound_kw ===
									"number" ||
									typeof selected.demand?.peak_import_lower_bound_kw ===
										"number") && (
									<tr>
										<th scope="row">
											{__("Grid import peak, lower bound", "linker-tools")}
										</th>
										<td>
											{measure(
												saved.candidate.demand?.peak_import_lower_bound_kw,
												"kW",
											)}
										</td>
										<td>
											{measure(
												selected.demand?.peak_import_lower_bound_kw,
												"kW",
											)}
										</td>
									</tr>
								)}
							</tbody>
						</table>
					</div>
					<button
						type="button"
						className="sc-button"
						disabled={
							disabled ||
							selecting ||
							(saved.run.id === run.id && saved.candidate.id === selectedId)
						}
						onClick={() => void select(saved.candidate, saved.run)}
					>
						{__("Use saved version", "linker-tools")}
					</button>
				</section>
			)}
		</section>
	);
}
