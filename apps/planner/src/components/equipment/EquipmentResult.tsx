import type { PlanningRun } from "../../data/planningProtocol.ts";
import { runTask } from "../../data/planningProtocol.ts";
import type { ReactNode } from "react";
import type { Json, JsonObject } from "../../data/protocol.ts";
import { readObject } from "../../data/readProtocol.ts";
import { __, sprintf } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";
import { PvStringResult } from "./PvStringResult.tsx";
import { EquipmentConditions } from "./EquipmentConditions.tsx";
import { PlantCheckGroups } from "./PlantCheckGroups.tsx";
import { runStateLabel, taskLabel } from "../energy/planningLabels.ts";
import {
	equipmentCheckLabel,
	equipmentReason,
	equipmentStatus,
} from "./equipmentLabels.ts";

function text(value: Json | undefined, locale: string): string {
	if (typeof value === "number")
		return new Intl.NumberFormat(locale, {
			maximumSignificantDigits: 12,
		}).format(value);
	if (Array.isArray(value))
		return value.map((v) => text(v, locale)).join(" – ");
	return typeof value === "string" ? value : "—";
}
function qualifier(value: Json | undefined, locale: string): string | null {
	if (typeof value === "string") return value;
	if (value && typeof value === "object" && !Array.isArray(value)) {
		const found = readObject(value)[locale.startsWith("de") ? "de" : "en"];
		return typeof found === "string" ? found : null;
	}
	return null;
}
export function EquipmentResult({
	run,
	locale,
	dirty,
	confirmedRevision,
	assessmentOverride,
	embedded = false,
	certificateSources,
	children,
}: {
	run: PlanningRun;
	locale: string;
	dirty: boolean;
	confirmedRevision: number;
	assessmentOverride?: JsonObject | null;
	embedded?: boolean;
	certificateSources?: ReactNode;
	children?: ReactNode;
}) {
	const assessment =
		assessmentOverride !== undefined
			? assessmentOverride
			: run.result
				? readObject(run.result.assessment)
				: null;
	const checks = assessment?.checks as JsonObject[] | undefined;
	const pvWiring = assessment?.pv_electrical
		? readObject(assessment.pv_electrical)
		: null;
	const stringNumbers = new Map(
		((pvWiring?.strings ?? []) as JsonObject[]).map((s, i) => [s.id, i + 1]),
	);
	const lines = assessment?.provisional_bill_of_materials as
		JsonObject[] | undefined;
	const selected = new Map(
		((assessment?.selected_products ?? []) as JsonObject[]).map((product) => [
			product.product_id,
			product,
		]),
	);
	function productDetail(line: JsonObject, key: string): string {
		// Earlier receipts retain these labels in selected_products only.
		const value = line[key] ?? selected.get(line.product_id)?.[key];
		return typeof value === "string" ? value : "";
	}
	function checkValue(
		check: JsonObject,
		field: "actual" | "required",
		semantic: string,
	): string {
		if (
			check.value_kind === "product_identity" ||
			(field === "actual" && semantic.split(":")[0] === "required_accessory")
		) {
			const label = check[`${field}_label`],
				product = selected.get(check[field]);
			return typeof label === "string"
				? label
				: product
					? [product.brand, product.model]
							.filter((v) => typeof v === "string")
							.join(" ")
					: "—";
		}
		if (semantic === "plant_operating_scope") {
			const mode =
				check[field] === "grid_connected"
					? __("Grid-connected", "linker-tools")
					: check[field] === "backup"
						? __("Backup operation", "linker-tools")
						: null;
			return mode
				? `${mode} · ${typeof check.control_network === "string" ? check.control_network.toUpperCase() : __("Not specified", "linker-tools")}`
				: "—";
		}
		if (semantic === "plant_operating_mode")
			return check[field] === "grid_connected"
				? __("Grid-connected", "linker-tools")
				: check[field] === "backup"
					? __("Backup operation", "linker-tools")
					: "—";
		return text(check[field], locale);
	}
	const renderCheck = (check: JsonObject) => {
		const semantic = String(check.semantic_id ?? check.id),
			suffix = semantic.split(":")[1],
			stringNumber = stringNumbers.get(suffix);
		const prefix =
			typeof check.unit_name === "string"
				? `${check.unit_name} · `
				: typeof check.group_name === "string"
					? `${__("Coordination group", "linker-tools")} ${check.group_name} · `
					: stringNumber
						? `${__("String", "linker-tools")} ${stringNumber} · `
						: /^(pv_stc_current|pv_stc_isc|pv_parallel_match|pv_parallel_count|pv_hot_current|pv_cold_current|pv_hot_isc|pv_cold_isc):/.test(
									semantic,
							  )
							? `MPPT ${suffix} · `
							: "";
		const explanation = equipmentReason(String(check.reason));
		const facts = check.facts as JsonObject[];
		const unit =
			(
				{
					pv_dc_input: "kWp",
					usable_energy: "kWh",
					continuous_battery_ac_output: "kW",
					continuous_battery_ac_charge: "kW",
					converter_identity: "kW",
				} as Record<string, string>
			)[semantic] ?? (typeof check.unit === "string" ? check.unit : "");
		return (
			<details className="lp-comparison" key={String(check.id)}>
				<summary>
					{prefix}
					{equipmentCheckLabel(semantic)} · {equipmentStatus(check.status)}
				</summary>
				{explanation && <p>{explanation}</p>}
				{check.status === "unresolved" && !explanation && (
					<p>
						{__(
							"The cited data does not establish whether this requirement is met.",
							"linker-tools",
						)}
					</p>
				)}
				{(check.actual !== null || check.required !== null) && (
					<dl className="lp-field-summary">
						<div>
							<dt>{__("Result", "linker-tools")}</dt>
							<dd>
								{checkValue(check, "actual", semantic)} {unit}
							</dd>
						</div>
						<div>
							<dt>{__("Requirement", "linker-tools")}</dt>
							<dd>
								{checkValue(check, "required", semantic)} {unit}
							</dd>
						</div>
					</dl>
				)}
				{check.derivation && (
					<p>
						{(readObject(check.derivation).factors as number[])
							.map((v) => text(v, locale))
							.join(" × ")}{" "}
						= {text(check.actual, locale)} kWh
					</p>
				)}
				{Array.isArray(check.documents) &&
					check.documents.map((value, i) => {
						const doc = readObject(value);
						return (
							<p key={i}>
								<a href={String(doc.url)} target="_blank" rel="noreferrer">
									{__("Source document", "linker-tools")}
								</a>
								{typeof doc.page === "number"
									? ` · ${sprintf(__("Page %d", "linker-tools"), doc.page)}`
									: ""}
							</p>
						);
					})}
				{facts.length > 0 && (
					<div>
						<h4>{__("Product data used", "linker-tools")}</h4>
						{facts.map((fact, index) => {
							const source = fact.source ? readObject(fact.source) : null,
								note = qualifier(fact.qualifier, locale);
							return (
								<div key={index}>
									{source?.figure_key !== "sales_unit_kind" && (
										<p>
											{text(fact.value, locale)}{" "}
											{typeof fact.unit === "string" ? fact.unit : ""}
										</p>
									)}
									{note && <p>{note}</p>}
									{source && (
										<p>
											<a
												href={String(source.url)}
												target="_blank"
												rel="noreferrer"
											>
												{__("Source document", "linker-tools")}
											</a>{" "}
											·{" "}
											{sprintf(
												__("Page %d", "linker-tools"),
												Number(source.page),
											)}
										</p>
									)}
								</div>
							);
						})}
					</div>
				)}
			</details>
		);
	};
	return (
		<div className="lp-run-result">
			{!embedded && (
				<div
					className="lp-run-heading lp-focus-target"
					data-action-result-context=""
				>
					<div>
						<span className="lp-eyebrow">{taskLabel(runTask(run))}</span>
						<h3 className="lp-focus-target" tabIndex={-1}>
							{runStateLabel(run.state, runTask(run))}
						</h3>
					</div>
					<span>
						{sprintf(__("Input revision %d", "linker-tools"), run.revision)}
					</span>
				</div>
			)}
			{!embedded &&
				(!run.is_current || run.revision !== confirmedRevision || dirty) && (
					<Notice>
						{__(
							"This calculation uses an earlier input snapshot. Open or newer project changes are excluded from its result.",
							"linker-tools",
						)}
					</Notice>
				)}
			{run.state === "failed" && (
				<Notice error>
					{__(
						"The calculation stopped before a result was published. Its original inputs remain saved.",
						"linker-tools",
					)}
				</Notice>
			)}
			{children}
			{assessment && (
				<>
					<Notice error={assessment.overall_status === "violated"}>
						<strong>{equipmentStatus(assessment.overall_status)}</strong>
						<p>
							{assessment.model === "woo_multi_converter_plant_v1"
								? __(
										"The report presents checks for each recorded system and its coordination group. Shared output, backup transfer and country-specific acceptance remain subject to the open checks.",
										"linker-tools",
									)
								: __(
										"This result records the proposed equipment and the checks covered here. Further assessment of the complete system is required.",
										"linker-tools",
									)}
						</p>
					</Notice>
					{certificateSources}
					{pvWiring && <PvStringResult value={pvWiring} locale={locale} />}
					{assessment.model === "woo_multi_converter_plant_v1" ? (
						<PlantCheckGroups
							assessment={assessment}
							renderCheck={renderCheck}
						/>
					) : (
						checks?.map(renderCheck)
					)}

					<p>
						{__(
							"Country requirements: not assessed by this calculation.",
							"linker-tools",
						)}
					</p>
					<EquipmentConditions assessment={assessment} locale={locale} />
					<h4>{__("Provisional bill of materials", "linker-tools")}</h4>
					<p>
						{__(
							"Quantities are shown only when the product's sales unit and selected configuration are established.",
							"linker-tools",
						)}
					</p>
					<div className="lp-table-scroll">
						<table>
							<thead>
								<tr>
									<th>{__("Product", "linker-tools")}</th>
									<th>{__("Quantity", "linker-tools")}</th>
								</tr>
							</thead>
							<tbody>
								{lines?.map((line, i) => (
									<tr key={i}>
										<td>
											{productDetail(line, "brand")}{" "}
											{productDetail(line, "model") || "—"}
											{productDetail(line, "sku") && (
												<div>
													<small>{productDetail(line, "sku")}</small>
												</div>
											)}
										</td>
										<td>
											{line.quantity === null
												? __("Quantity not determined", "linker-tools")
												: text(line.quantity, locale)}
										</td>
									</tr>
								))}
							</tbody>
						</table>
					</div>
				</>
			)}
		</div>
	);
}
