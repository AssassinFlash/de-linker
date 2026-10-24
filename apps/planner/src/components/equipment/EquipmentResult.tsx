import type { PlanningRun } from "../../data/planningProtocol.ts";
import type { Json, JsonObject } from "../../data/protocol.ts";
import { readObject } from "../../data/readProtocol.ts";
import { __, sprintf } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";
import { runStateLabel } from "../energy/planningLabels.ts";
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
}: {
	run: PlanningRun;
	locale: string;
	dirty: boolean;
	confirmedRevision: number;
}) {
	const assessment = run.result ? readObject(run.result.assessment) : null;
	const checks = assessment?.checks as JsonObject[] | undefined;
	const lines = assessment?.provisional_bill_of_materials as
		JsonObject[] | undefined;
	const pair =
		assessment?.manufacturer_pair && readObject(assessment.manufacturer_pair);
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
	return (
		<div className="lp-run-result">
			<div
				className="lp-run-heading lp-focus-target"
				data-action-result-context=""
			>
				<div>
					<span className="lp-eyebrow">
						{__("Equipment checks", "linker-tools")}
					</span>
					<h3 className="lp-focus-target" tabIndex={-1}>
						{runStateLabel(run.state, "qualify_woo_equipment_v1")}
					</h3>
				</div>
				<span>
					{sprintf(__("Input revision %d", "linker-tools"), run.revision)}
				</span>
			</div>
			{(!run.is_current || run.revision !== confirmedRevision || dirty) && (
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
			{assessment && (
				<>
					<Notice error={assessment.overall_status === "violated"}>
						<strong>{equipmentStatus(assessment.overall_status)}</strong>
						<p>
							{__(
								"This result records the proposed equipment and the checks covered here. Further assessment of the complete system is required.",
								"linker-tools",
							)}
						</p>
					</Notice>
					{checks?.map((check) => {
						const explanation = equipmentReason(String(check.reason));
						const facts = check.facts as JsonObject[];
						const unit =
							(
								{
									pv_dc_input: "kW",
									usable_energy: "kWh",
									continuous_battery_ac_output: "kW",
									converter_identity: "kW",
								} as Record<string, string>
							)[String(check.id)] ?? "";
						return (
							<details className="lp-comparison" key={String(check.id)}>
								<summary>
									{equipmentCheckLabel(String(check.id))} ·{" "}
									{equipmentStatus(check.status)}
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
												{text(check.actual, locale)} {unit}
											</dd>
										</div>
										<div>
											<dt>{__("Requirement", "linker-tools")}</dt>
											<dd>
												{text(check.required, locale)} {unit}
											</dd>
										</div>
									</dl>
								)}
								{facts.length > 0 && (
									<div>
										<h4>{__("Product data used", "linker-tools")}</h4>
										{facts.map((fact, index) => {
											const source = fact.source
													? readObject(fact.source)
													: null,
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
					})}
					{pair &&
						Array.isArray(pair.conditions) &&
						pair.conditions.length > 0 && (
							<details className="lp-comparison">
								<summary>
									{__("Manufacturer conditions", "linker-tools")}
								</summary>
								{pair.conditions.map((value, i) => (
									<p key={i}>{qualifier(value, locale)}</p>
								))}
							</details>
						)}
					<p>
						{__(
							"Country requirements: not assessed by this calculation.",
							"linker-tools",
						)}
					</p>
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
												<small>{productDetail(line, "sku")}</small>
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
