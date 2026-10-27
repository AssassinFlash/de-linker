import { useCallback, useEffect, useMemo, useState } from "react";
import type { Draft } from "../../domain/draft.ts";
import type { JsonObject } from "../../data/protocol.ts";
import { readGeometry } from "../../domain/validateGeometry.ts";
import geometryPolicy from "../../contracts/geometry-policy.json" with { type: "json" };
import { panelPoses } from "../../domain/panelPoses.ts";
import { readPvStringPlan } from "../../domain/pvStrings.ts";
import type { PvStringPlan } from "../../domain/pvStrings.ts";
import { __, sprintf } from "../../i18n.ts";
import { NumberField } from "../NumberField.tsx";
import { Notice } from "../Notice.tsx";
import { PvOperatingSetup } from "./PvOperatingSetup.tsx";

export function PvStringSetup({
	draft,
	edit,
	inverterId,
	locale,
	disabled,
	onValidity,
}: {
	draft: Draft;
	edit: (change: (inputs: JsonObject) => JsonObject) => boolean;
	inverterId: number | null;
	locale: string;
	disabled: boolean;
	onValidity: (valid: boolean) => void;
}) {
	const geometry = useMemo(() => {
		try {
			return draft.history.current.geometry
				? readGeometry(draft.history.current.geometry, geometryPolicy)
				: null;
		} catch {
			return null;
		}
	}, [draft.history.current.geometry]);
	const plan = useMemo(
		() =>
			draft.history.current.pv_string_plan === undefined
				? null
				: readPvStringPlan(draft.history.current.pv_string_plan),
		[draft.history.current.pv_string_plan],
	);
	const poses = useMemo(
		() => (geometry ? panelPoses(geometry).filter((p) => p.included) : []),
		[geometry],
	);
	const [selected, setSelected] = useState<string[]>([]),
		[mppt, setMppt] = useState<number | null>(null),
		[port, setPort] = useState<number | null>(null);
	const [fields, setFields] = useState<Record<string, boolean>>({});
	const validity = useMemo(
		() =>
			Object.fromEntries(
				["temperature", "mppt", "port", "operating"].map((key) => [
					key,
					(valid: boolean) =>
						setFields((v) => (v[key] === valid ? v : { ...v, [key]: valid })),
				]),
			),
		[],
	);
	const valid =
		!plan ||
		(plan.inverter_product_id === inverterId &&
			Object.values(fields).every(Boolean));
	const assigned = new Set(plan?.strings.flatMap((s) => s.module_ids) ?? []),
		available = new Set(poses.map((p) => p.id));
	const change = useCallback(
		(value: PvStringPlan | null) => {
			if (disabled) return;
			edit((inputs) => {
				const next = { ...inputs };
				delete next.equipment_candidate;
				if (value) next.pv_string_plan = value;
				else delete next.pv_string_plan;
				return next;
			});
		},
		[edit, disabled],
	);
	// Invalid local number syntax cannot permit saving/calculating older values.
	useEffect(() => {
		onValidity(valid);
		return () => onValidity(true);
	}, [valid, onValidity]);
	if (!geometry || !poses.length)
		return plan ? (
			<section>
				<Notice error>
					{__(
						"The roof has changed. Remove strings containing missing modules and assign the current modules.",
						"linker-tools",
					)}
				</Notice>
				<button
					type="button"
					className="lp-text-button"
					disabled={disabled}
					onClick={() => change(null)}
				>
					{__("Remove wiring plan", "linker-tools")}
				</button>
			</section>
		) : null;
	return (
		<details className="lp-comparison">
			<summary>{__("PV strings and inputs", "linker-tools")}</summary>
			<p>
				{__(
					"Assign the roof modules to strings and inverter inputs. The equipment check uses the saved wiring plan and product data.",
					"linker-tools",
				)}
			</p>
			{!plan ? (
				<button
					type="button"
					className="lp-button lp-button-secondary"
					disabled={disabled || !inverterId}
					onClick={() => {
						if (inverterId)
							change({
								schema_version: 1,
								inverter_product_id: inverterId,
								minimum_ambient_c: null,
								temperature_source: null,
								strings: [],
							});
					}}
				>
					{__("Set up PV strings", "linker-tools")}
				</button>
			) : (
				<fieldset disabled={disabled}>
					{plan.inverter_product_id !== inverterId && (
						<Notice error>
							{__(
								"These strings belong to another inverter. Select that inverter or start a new wiring plan.",
								"linker-tools",
							)}
						</Notice>
					)}
					<div className="lp-scenario-fields">
						<NumberField
							label={__("Lowest design ambient temperature", "linker-tools")}
							unit="°C"
							locale={locale}
							min={-273.15}
							value={plan.minimum_ambient_c}
							onChange={(v) => change({ ...plan, minimum_ambient_c: v })}
							onValidity={validity.temperature!}
						/>
						<label className="lp-field">
							<span>
								{__("Temperature source and location", "linker-tools")}
							</span>
							<textarea
								maxLength={4096}
								value={plan.temperature_source ?? ""}
								onChange={(e) =>
									change({
										...plan,
										temperature_source: e.currentTarget.value.trim()
											? e.currentTarget.value
											: null,
									})
								}
							/>
						</label>
					</div>
					<p className="lp-profile-help">
						{__(
							"Use a documented local design minimum. A typical weather year's lowest temperature is not a design extreme.",
							"linker-tools",
						)}
					</p>
					<p role="status">
						{sprintf(
							__("%1$d of %2$d roof modules assigned", "linker-tools"),
							[...assigned].filter((id) => available.has(id)).length,
							poses.length,
						)}
					</p>
					{plan.strings.some((s) =>
						s.module_ids.some((id) => !available.has(id)),
					) && (
						<Notice error>
							{__(
								"The roof has changed. Remove strings containing missing modules and assign the current modules.",
								"linker-tools",
							)}
						</Notice>
					)}
					{plan.strings.map((s, i) => (
						<div className="lp-comparison" key={s.id}>
							<strong>{sprintf(__("String %d", "linker-tools"), i + 1)}</strong>
							<p>
								{sprintf(
									__("MPPT %1$d · input %2$d · %3$d modules", "linker-tools"),
									s.mppt,
									s.input,
									s.module_ids.length,
								)}
							</p>
							<details>
								<summary>{__("Assigned modules", "linker-tools")}</summary>
								<ul>
									{s.module_ids.map((id) => {
										const p = poses.find((p) => p.id === id);
										return (
											<li key={id}>
												{p
													? sprintf(
															__(
																"%1$s · row %2$d · module %3$d",
																"linker-tools",
															),
															geometry.arrays.find((a) => a.id === p.array_id)
																?.name ?? p.array_id,
															p.row + 1,
															p.column + 1,
														)
													: id}
											</li>
										);
									})}
								</ul>
							</details>
							<button
								type="button"
								className="lp-text-button"
								onClick={() =>
									change({
										...plan,
										strings: plan.strings.filter((row) => row.id !== s.id),
									})
								}
							>
								{__("Remove string", "linker-tools")}
							</button>
						</div>
					))}
					<PvOperatingSetup
						plan={plan}
						change={change}
						locale={locale}
						disabled={disabled}
						onValidity={validity.operating!}
					/>
					<h4>{__("Add a string", "linker-tools")}</h4>
					<div className="lp-scenario-fields">
						<NumberField
							label="MPPT"
							unit=""
							integer
							min={1}
							value={mppt}
							locale={locale}
							onChange={setMppt}
							onValidity={validity.mppt!}
						/>
						<NumberField
							label={__("Inverter input", "linker-tools")}
							unit=""
							integer
							min={1}
							value={port}
							locale={locale}
							onChange={setPort}
							onValidity={validity.port!}
						/>
					</div>
					{geometry.arrays.map((a) => (
						<details key={a.id}>
							<summary>{a.name}</summary>
							<div className="lp-scenario-fields">
								{poses
									.filter((p) => p.array_id === a.id)
									.map((p) => (
										<label className="lp-field" key={p.id}>
											<span>
												<input
													type="checkbox"
													disabled={assigned.has(p.id)}
													checked={
														selected.includes(p.id) && !assigned.has(p.id)
													}
													onChange={(e) => {
														const checked = e.currentTarget.checked;
														setSelected((old) =>
															checked
																? [...old, p.id]
																: old.filter((id) => id !== p.id),
														);
													}}
												/>
												{sprintf(
													__("Row %1$d · module %2$d", "linker-tools"),
													p.row + 1,
													p.column + 1,
												)}
											</span>
										</label>
									))}
							</div>
						</details>
					))}
					<div className="lp-energy-submit">
						<button
							type="button"
							className="lp-button lp-button-secondary"
							disabled={
								!valid ||
								mppt === null ||
								port === null ||
								!selected.some(
									(id) => available.has(id) && !assigned.has(id),
								) ||
								plan.strings.some((s) => s.mppt === mppt && s.input === port)
							}
							onClick={() => {
								if (mppt === null || port === null) return;
								change({
									...plan,
									strings: [
										...plan.strings,
										{
											id: `s-${crypto.randomUUID()}`,
											mppt,
											input: port,
											module_ids: selected.filter(
												(id) => available.has(id) && !assigned.has(id),
											),
										},
									],
								});
								setSelected([]);
							}}
						>
							{__("Add selected modules to string", "linker-tools")}
						</button>
						<button
							type="button"
							className="lp-text-button"
							onClick={() => {
								change(null);
								setSelected([]);
								setFields({});
							}}
						>
							{__("Remove wiring plan", "linker-tools")}
						</button>
					</div>
					<p className="lp-profile-help">
						{__(
							"Save the project, then check the equipment selection. Cold open-circuit voltage and STC checks are shown separately from outstanding design checks.",
							"linker-tools",
						)}
					</p>
				</fieldset>
			)}
		</details>
	);
}
