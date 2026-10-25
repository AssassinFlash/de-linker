import { useEffect, useMemo, useState } from "react";
import type { JsonObject } from "../../data/protocol.ts";
import { readObject } from "../../data/readProtocol.ts";
import type { PvStringPlan } from "../../domain/pvStrings.ts";
import { __ } from "../../i18n.ts";
import { NumberField } from "../NumberField.tsx";
import { Notice } from "../Notice.tsx";

export function PvOperatingSetup({
	plan,
	change,
	locale,
	disabled,
	onValidity,
}: {
	plan: PvStringPlan;
	change: (next: PvStringPlan) => void;
	locale: string;
	disabled: boolean;
	onValidity: (valid: boolean) => void;
}) {
	const conditions = plan.operating_conditions
		? readObject(plan.operating_conditions)
		: null;
	const [validity, setValidity] = useState<Record<string, boolean>>({});
	const [nonPositiveIrradiance, setNonPositiveIrradiance] = useState(false);
	const callbacks = useMemo(
		() =>
			Object.fromEntries(
				["irradiance_w_m2", "hot_cell_c", "cold_cell_c"].map((key) => [
					key,
					(valid: boolean) => {
						if (key === "irradiance_w_m2") setNonPositiveIrradiance(false);
						setValidity((v) => (v[key] === valid ? v : { ...v, [key]: valid }));
					},
				]),
			),
		[],
	);
	const invalidIrradiance = nonPositiveIrradiance;
	const valid =
		!conditions ||
		(Object.values(validity).every(Boolean) && !invalidIrradiance);
	useEffect(() => {
		onValidity(valid);
		return () => onValidity(true);
	}, [valid, onValidity]);
	const update = (patch: JsonObject) => {
		if (conditions && !disabled)
			change({ ...plan, operating_conditions: { ...conditions, ...patch } });
	};
	return (
		<details className="lp-comparison">
			<summary>{__("Electrical operating conditions", "linker-tools")}</summary>
			<p>
				{__(
					"The single-diode model estimates operating points from the saved module data. Effective irradiance is the irradiance available to the cells for electrical generation. Enter cell temperatures for the hot and cold operating cases; these can differ from ambient air temperature.",
					"linker-tools",
				)}
			</p>
			{!conditions ? (
				<button
					type="button"
					className="lp-button lp-button-secondary"
					disabled={disabled}
					onClick={() =>
						change({
							...plan,
							operating_conditions: {
								irradiance_w_m2: null,
								hot_cell_c: null,
								cold_cell_c: null,
								source_note: null,
							},
						})
					}
				>
					{__("Add operating conditions", "linker-tools")}
				</button>
			) : (
				<fieldset disabled={disabled}>
					{invalidIrradiance && (
						<Notice error>
							{__(
								"Effective irradiance must be greater than zero.",
								"linker-tools",
							)}
						</Notice>
					)}
					<NumberField
						label={__("Effective irradiance at the modules", "linker-tools")}
						unit="W/m²"
						value={
							typeof conditions.irradiance_w_m2 === "number"
								? conditions.irradiance_w_m2
								: null
						}
						locale={locale}
						min={0}
						onChange={(v) => {
							const invalid = v !== null && v <= 0;
							setNonPositiveIrradiance(invalid);
							// Keep unfinished input (including the "0" in "0.5") local.
							// The saved plan requires strictly positive irradiance.
							if (!invalid) update({ irradiance_w_m2: v });
						}}
						onValidity={callbacks.irradiance_w_m2!}
					/>
					<NumberField
						label={__("Hot operating cell temperature", "linker-tools")}
						unit="°C"
						value={
							typeof conditions.hot_cell_c === "number"
								? conditions.hot_cell_c
								: null
						}
						locale={locale}
						min={-273.15}
						onChange={(v) => update({ hot_cell_c: v })}
						onValidity={callbacks.hot_cell_c!}
					/>
					<NumberField
						label={__("Cold operating cell temperature", "linker-tools")}
						unit="°C"
						value={
							typeof conditions.cold_cell_c === "number"
								? conditions.cold_cell_c
								: null
						}
						locale={locale}
						min={-273.15}
						onChange={(v) => update({ cold_cell_c: v })}
						onValidity={callbacks.cold_cell_c!}
					/>
					<label className="lp-field">
						<span>
							{__(
								"Operating-condition source and mounting basis",
								"linker-tools",
							)}
						</span>
						<textarea
							maxLength={4096}
							value={
								typeof conditions.source_note === "string"
									? conditions.source_note
									: ""
							}
							onChange={(e) =>
								update({
									source_note: e.currentTarget.value.trim()
										? e.currentTarget.value
										: null,
								})
							}
						/>
					</label>
					<p className="lp-profile-help">
						{__(
							"These values need a project-specific basis, including mounting and ventilation. No local design extremes are filled in automatically. Model estimates do not establish manufacturer performance or the complete design current.",
							"linker-tools",
						)}
					</p>
					<button
						type="button"
						className="lp-text-button"
						onClick={() => change({ ...plan, operating_conditions: null })}
					>
						{__("Remove operating conditions", "linker-tools")}
					</button>
				</fieldset>
			)}
		</details>
	);
}
