import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Draft } from "../../domain/draft.ts";
import type { JsonObject } from "../../data/protocol.ts";
import { readGeometry } from "../../domain/validateGeometry.ts";
import geometryPolicy from "../../contracts/geometry-policy.json" with { type: "json" };
import { panelPoses } from "../../domain/panelPoses.ts";
import { readPvStringPlan } from "../../domain/pvStrings.ts";
import type { PvString, PvStringPlan } from "../../domain/pvStrings.ts";
import { __, sprintf } from "../../i18n.ts";
import { NumberField } from "../NumberField.tsx";
import { Notice } from "../Notice.tsx";
import { PvOperatingSetup } from "./PvOperatingSetup.tsx";
import { PvModuleSelection } from "./PvModuleSelection.tsx";

export function PvStringSetup({
	draft,
	edit,
	inverterId,
	locale,
	disabled,
	onValidity,
	controlled,
}: {
	draft: Draft;
	edit: (change: (inputs: JsonObject) => JsonObject) => boolean;
	inverterId: number | null;
	locale: string;
	disabled: boolean;
	onValidity: (valid: boolean) => void;
	controlled?: {
		plan: PvStringPlan | null;
		change: (plan: PvStringPlan | null) => boolean;
		unavailableModuleIds: string[];
		unavailableModuleLabels?: Record<string, string>;
		scopeLabel?: string;
	};
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
	const savedPlan = useMemo(
		() =>
			controlled || draft.history.current.pv_string_plan === undefined
				? null
				: readPvStringPlan(draft.history.current.pv_string_plan),
		[draft.history.current.pv_string_plan, controlled],
	);
	const plan = controlled ? controlled.plan : savedPlan;
	const poses = useMemo(
		() => (geometry ? panelPoses(geometry).filter((p) => p.included) : []),
		[geometry],
	);
	const [selected, setSelected] = useState<string[]>([]),
		[mppt, setMppt] = useState<number | null>(null),
		[port, setPort] = useState<number | null>(null),
		[batchSize, setBatchSize] = useState<number | null>(null),
		[editing, setEditing] = useState<PvString | null>(null),
		[applyFailed, setApplyFailed] = useState(false);
	const backup = useRef<{
		selected: string[];
		mppt: number | null;
		port: number | null;
		batchSize: number | null;
	} | null>(null);
	const editor = useRef<HTMLHeadingElement>(null);
	const labels = useMemo(
		() =>
			new Map(
				poses.map((pose) => {
					const index = geometry!.arrays.findIndex(
						(a) => a.id === pose.array_id,
					);
					return [
						pose.id,
						sprintf(
							__("Array %1$d · %2$s · row %3$d · module %4$d", "linker-tools"),
							index + 1,
							geometry!.arrays[index]!.name,
							pose.row + 1,
							pose.column + 1,
						),
					];
				}),
			),
		[geometry, poses, locale],
	);
	useEffect(() => {
		if (editing) editor.current?.focus();
	}, [editing]);
	const [fields, setFields] = useState<Record<string, boolean>>({});
	const validity = useMemo(
		() =>
			Object.fromEntries(
				["temperature", "mppt", "port", "operating", "selectionSize"].map(
					(key) => [
						key,
						(valid: boolean) =>
							setFields((v) => (v[key] === valid ? v : { ...v, [key]: valid })),
					],
				),
			),
		[],
	);
	const valid =
		!plan ||
		(plan.inverter_product_id === inverterId &&
			Object.values(fields).every(Boolean));
	const assigned = new Map<string, string>();
	plan?.strings.forEach((string, index) => {
		if (string.id !== editing?.id)
			for (const id of string.module_ids)
				assigned.set(
					id,
					sprintf(
						__(
							"Assigned to string %1$d · MPPT %2$d · input %3$d",
							"linker-tools",
						),
						index + 1,
						string.mppt,
						string.input,
					),
				);
	});
	for (const id of controlled?.unavailableModuleIds ?? [])
		assigned.set(
			id,
			controlled?.unavailableModuleLabels?.[id] ??
				__("Assigned to another system", "linker-tools"),
		);
	const available = new Set(poses.map((pose) => pose.id));
	const currentString = plan?.strings.find(
		(string) => string.id === editing?.id,
	);
	const staleEdit =
		!!editing &&
		(!currentString ||
			currentString.mppt !== editing.mppt ||
			currentString.input !== editing.input ||
			JSON.stringify(currentString.module_ids) !==
				JSON.stringify(editing.module_ids));
	const conflictingInput = plan?.strings.find(
		(string) =>
			string.id !== editing?.id &&
			string.mppt === mppt &&
			string.input === port,
	);
	const unavailableSelection = selected.filter(
		(id) => !available.has(id) || assigned.has(id),
	);
	const count = editing ? selected.length : (batchSize ?? selected.length);
	const canApply =
		valid &&
		!staleEdit &&
		mppt !== null &&
		port !== null &&
		!conflictingInput &&
		count > 0 &&
		count <= selected.length &&
		!unavailableSelection.length;
	const resetEditor = () => {
		const previous = backup.current;
		setEditing(null);
		setApplyFailed(false);
		backup.current = null;
		setSelected(previous?.selected ?? []);
		setMppt(previous?.mppt ?? null);
		setPort(previous?.port ?? null);
		setBatchSize(previous?.batchSize ?? null);
	};
	const change = useCallback(
		(value: PvStringPlan | null) => {
			if (disabled) return false;
			if (controlled) return controlled.change(value);
			return edit((inputs) => {
				const next = { ...inputs };
				delete next.equipment_candidate;
				if (value) next.pv_string_plan = value;
				else delete next.pv_string_plan;
				return next;
			});
		},
		[edit, disabled, controlled],
	);
	const removePlan = () => {
		if (!change(null)) return;
		setEditing(null);
		backup.current = null;
		setApplyFailed(false);
		setSelected([]);
		setFields({});
		setMppt(null);
		setPort(null);
		setBatchSize(null);
	};
	// Invalid local number syntax cannot permit saving/calculating older values.
	useEffect(() => {
		onValidity(controlled ? Object.values(fields).every(Boolean) : valid);
		return () => onValidity(true);
	}, [valid, onValidity, !!controlled, fields]);
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
					onClick={removePlan}
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
							(plan?.strings.flatMap((s) => s.module_ids) ?? []).filter((id) =>
								available.has(id),
							).length,
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
								<ol>
									{s.module_ids.map((id) => (
										<li key={id}>{labels.get(id) ?? id}</li>
									))}
								</ol>
							</details>
							<button
								type="button"
								className="lp-text-button"
								disabled={
									disabled ||
									editing !== null ||
									!Object.values(fields).every(Boolean)
								}
								onClick={() => {
									backup.current = { selected, mppt, port, batchSize };
									setEditing({ ...s, module_ids: [...s.module_ids] });
									setSelected([...s.module_ids]);
									setMppt(s.mppt);
									setPort(s.input);
									setApplyFailed(false);
									setFields((value) => ({ ...value, selectionSize: true }));
								}}
							>
								{__("Edit string", "linker-tools")}
							</button>
							<button
								type="button"
								className="lp-text-button"
								onClick={() => {
									if (
										change({
											...plan,
											strings: plan.strings.filter((row) => row.id !== s.id),
										}) &&
										editing?.id === s.id
									)
										resetEditor();
								}}
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
					<h4 ref={editor} tabIndex={-1}>
						{editing && currentString
							? sprintf(
									__("Edit string %d", "linker-tools"),
									plan.strings.findIndex((string) => string.id === editing.id) +
										1,
								)
							: editing
								? __("Edit string", "linker-tools")
								: __("Add a string", "linker-tools")}
					</h4>
					{controlled?.scopeLabel && (
						<p>
							{sprintf(__("System: %s", "linker-tools"), controlled.scopeLabel)}
						</p>
					)}
					{staleEdit && (
						<Notice error>
							{__(
								"This string changed while you were editing. Cancel this edit and reopen the current string.",
								"linker-tools",
							)}
						</Notice>
					)}
					{applyFailed && (
						<Notice error>
							{__(
								"The change was not applied. Your module selection is still available.",
								"linker-tools",
							)}
						</Notice>
					)}
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
					{conflictingInput && (
						<Notice error>
							{__(
								"This MPPT and inverter input already has a string. Choose another input or edit its existing string.",
								"linker-tools",
							)}
						</Notice>
					)}
					<PvModuleSelection
						geometry={geometry}
						poses={poses}
						labels={labels}
						selected={selected}
						assigned={assigned}
						disabled={disabled}
						change={(ids) => {
							setSelected(ids);
							setApplyFailed(false);
						}}
					/>
					{!editing && (
						<>
							<NumberField
								label={__("Modules to add to this string", "linker-tools")}
								unit=""
								integer
								min={1}
								value={batchSize}
								locale={locale}
								onChange={setBatchSize}
								onValidity={validity.selectionSize!}
							/>
							<p className="lp-profile-help">
								{__(
									"Leave this blank to use the complete selection. A smaller group uses the first modules in the displayed order; the remainder stays selected for the next string.",
									"linker-tools",
								)}
							</p>
						</>
					)}
					{selected.length > 0 && count <= selected.length && (
						<p role="status">
							{sprintf(
								__(
									"The first %d selected modules will be saved in this order.",
									"linker-tools",
								),
								count,
							)}
						</p>
					)}
					{selected.length > 0 && count > selected.length && (
						<Notice error>
							{__(
								"Select more modules or reduce the number for this string.",
								"linker-tools",
							)}
						</Notice>
					)}
					{unavailableSelection.length > 0 && (
						<Notice error>
							<p>
								{__(
									"Some selected modules are missing or already assigned. Review the selection before applying it.",
									"linker-tools",
								)}
							</p>
							<button
								type="button"
								className="lp-text-button"
								onClick={() =>
									setSelected(
										selected.filter(
											(id) => available.has(id) && !assigned.has(id),
										),
									)
								}
							>
								{__(
									"Remove unavailable modules from selection",
									"linker-tools",
								)}
							</button>
						</Notice>
					)}
					<div className="lp-energy-submit">
						<button
							type="button"
							className="lp-button lp-button-secondary"
							disabled={!canApply}
							onClick={() => {
								if (!canApply || mppt === null || port === null) return;
								const string: PvString = {
									id: editing?.id ?? `s-${crypto.randomUUID()}`,
									mppt,
									input: port,
									module_ids: selected.slice(0, count),
								};
								const strings = editing
									? plan.strings.map((value) =>
											value.id === editing.id ? string : value,
										)
									: [...plan.strings, string];
								if (!change({ ...plan, strings })) {
									setApplyFailed(true);
									return;
								}
								if (editing) resetEditor();
								else {
									setSelected(selected.slice(count));
									setApplyFailed(false);
								}
							}}
						>
							{editing
								? __("Save string changes", "linker-tools")
								: __("Add selected modules to string", "linker-tools")}
						</button>
						{editing && (
							<button
								type="button"
								className="lp-text-button"
								onClick={resetEditor}
							>
								{__("Cancel editing", "linker-tools")}
							</button>
						)}
						<button
							type="button"
							className="lp-text-button"
							onClick={removePlan}
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
