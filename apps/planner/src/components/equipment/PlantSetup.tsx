import { equipmentFieldMessage } from "./equipmentLabels.ts";
import { useEffect, useMemo, useState } from "react";
import type { ComponentProps } from "react";
import { PlantPvStringSetup } from "./PlantPvStringSetup.tsx";
import {
	readPvPlantStringPlan,
	changePvPlantStringUnit,
} from "../../domain/pvPlantStrings.ts";
import { EquipmentSetup } from "./EquipmentSetup.tsx";
import { useEquipmentProducts } from "../../data/equipmentProducts.ts";
import { sameJson } from "../../domain/draft.ts";
import { equipmentDraft, PART_USES } from "../../domain/equipment.ts";
import type { PartUse } from "../../domain/equipment.ts";
import {
	plantInputs,
	readPlantDraft,
	plantIdentity as newId,
} from "../../domain/equipmentPlant.ts";
import type { PlantDraft } from "../../domain/equipmentPlant.ts";
import { readObject } from "../../data/readProtocol.ts";
import { ApiError } from "../../data/protocol.ts";
import { __, sprintf } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";
import { NumberField } from "../NumberField.tsx";
type Props = ComponentProps<typeof EquipmentSetup>;

export function PlantSetup(props: Props) {
	const {
		draft,
		edit,
		client,
		scope,
		active,
		locale,
		disabled,
		actionsDisabled,
		onError,
		onValidity,
	} = props;
	const storageOnly =
		draft.history.current.brief !== undefined &&
		readObject(draft.history.current.brief).system_scope === "storage_only";
	const catalog = useEquipmentProducts(client, scope, active);
	const setup = useMemo(() => {
		try {
			return readPlantDraft(draft.history.current);
		} catch {
			return null;
		}
	}, [
		draft.history.current.brief,
		draft.history.current.equipment_plant,
		draft.history.current.equipment_plant_setup,
	]);
	const [selectedId, select] = useState<string | null>(null);
	useEffect(() => {
		const index = props.inputErrors
			?.map((path) => /^equipment_plant_setup\.units\[(\d+)\]/.exec(path)?.[1])
			.find((value) => value !== undefined);
		if (index !== undefined && setup?.units[Number(index)])
			select(setup.units[Number(index)]!.id);
	}, [props.inputErrors, setup]);
	const [validity, setValidity] = useState<Record<string, boolean>>({});
	const [stringValidity, setStringValidity] = useState<Record<string, boolean>>(
		{},
	);
	const ids = setup?.units.map((u) => u.id).join(",") ?? "";
	const unitCallbacks = useMemo(
		() =>
			Object.fromEntries(
				ids
					.split(",")
					.filter(Boolean)
					.map((id) => [
						id,
						(valid: boolean) =>
							setValidity((state) =>
								state[`unit:${id}`] === valid
									? state
									: { ...state, [`unit:${id}`]: valid },
							),
					]),
			),
		[ids],
	);
	const stringCallbacks = useMemo(
		() =>
			Object.fromEntries(
				ids
					.split(",")
					.filter(Boolean)
					.map((id) => [
						id,
						(valid: boolean) =>
							setStringValidity((state) =>
								state[id] === valid ? state : { ...state, [id]: valid },
							),
					]),
			),
		[ids],
	);
	const wiring =
		draft.history.current.pv_plant_string_plan === undefined
			? null
			: readPvPlantStringPlan(draft.history.current.pv_plant_string_plan);
	const stale =
		wiring?.units.filter(
			(u) => !setup?.units.some((s) => s.id === u.unit_id),
		) ?? [];
	const fieldCallbacks = useMemo(
		() =>
			Object.fromEntries(
				["pv_dc_kw", "required_usable_kwh", "required_discharge_ac_kw"].map(
					(id) => [
						id,
						(valid: boolean) =>
							setValidity((state) =>
								state[`field:${id}`] === valid
									? state
									: { ...state, [`field:${id}`]: valid },
							),
					],
				),
			),
		[],
	);
	const valid =
		Object.entries(stringValidity).every(
			([id, ok]) => ok || !ids.split(",").includes(id),
		) &&
		Object.entries(validity).every(
			([key, ok]) =>
				ok ||
				(key.startsWith("unit:") && !ids.split(",").includes(key.slice(5))),
		);
	useEffect(() => {
		onValidity(valid);
		return () => onValidity(true);
	}, [valid, onValidity]);
	const blocked =
		disabled ||
		catalog.isFetching ||
		!!catalog.error ||
		!catalog.data?.prepared;
	const products = catalog.data?.products ?? [];
	function change(
		operation: (current: PlantDraft) => PlantDraft,
		changed: readonly string[] = [],
	): boolean {
		if (disabled || !client.isCurrentScope(scope)) return false;
		try {
			const before = readPlantDraft(draft.history.current);
			const next = operation(before);
			if (
				!edit((inputs) => {
					if (!sameJson(readPlantDraft(inputs), before))
						throw new ApiError(409, "conflict");
					return plantInputs(inputs, next);
				})
			)
				throw new ApiError(409, "conflict");
			onError(null, changed);
			return true;
		} catch (error) {
			onError(error);
			return false;
		}
	}
	if (!setup)
		return (
			<Notice error>
				{__(
					"This multi-system draft cannot be edited here. Its saved inputs and results remain available.",
					"linker-tools",
				)}
			</Notice>
		);
	const selected =
		setup.units.find((u) => u.id === selectedId)?.id ?? setup.units[0]!.id;
	const pathFor = (key: string) => "equipment_plant_setup.requirements." + key;
	const message = (key: string) =>
		equipmentFieldMessage(props.inputErrors ?? [], pathFor(key));
	const fieldProps = (key: string) => ({
		name: pathFor(key),
		"aria-invalid": Boolean(message(key)),
		"aria-describedby": message(key) ? pathFor(key) + "-error" : undefined,
	});
	const feedback = (key: string) =>
		message(key) ? (
			<small className="sc-field-error" id={pathFor(key) + "-error"}>
				{message(key)}
			</small>
		) : null;
	const requirementNumber = (key: string, label: string, unit: string) => (
		<NumberField
			name={pathFor(key)}
			error={message(key)}
			label={label}
			unit={unit}
			locale={locale}
			min={0}
			value={
				typeof setup.requirements[key] === "number"
					? (setup.requirements[key] as number)
					: null
			}
			onValidity={fieldCallbacks[key]!}
			onChange={(value) =>
				change(
					(current) => ({
						...current,
						requirements: { ...current.requirements, [key]: value },
					}),
					[pathFor(key)],
				)
			}
		/>
	);
	return (
		<>
			<p className="sc-field-help">
				{__(
					"Each system has its own equipment selection. Battery equipment may be separate, integrated or absent. Coordination groups record systems planned to share a controller.",
					"linker-tools",
				)}
			</p>
			<p className="sc-field-help">
				{__(
					"To return to single-system planning, keep one system, remove coordination groups, then choose Single system. Undo can reverse changes still available in the current editing history.",
					"linker-tools",
				)}
			</p>
			{catalog.error && (
				<Notice error>
					{__("Product data could not be loaded.", "linker-tools")}
				</Notice>
			)}
			{catalog.isFetching && (
				<p role="status">
					{__("Current product data is being prepared.", "linker-tools")}
				</p>
			)}
			<div className="sc-work-toolbar sc-equipment-data">
				<button
					type="button"
					className="sc-text-button"
					disabled={catalog.isFetching || disabled}
					onClick={() => void catalog.refetch()}
				>
					{__("Reload product data", "linker-tools")}
				</button>
			</div>
			<div className="sc-work-grid sc-equipment-plant-layout">
				<div className="sc-work-aside">
					<fieldset
						disabled={disabled}
						className="sc-scenario-fields sc-scenario-block sc-work-panel sc-equipment-requirements"
					>
						<legend className="sc-work-panel-heading">
							{__("Project requirements", "linker-tools")}
						</legend>
						<div className="sc-geometry-fields">
							<label className="sc-field">
								<span>{__("Choose an operating mode", "linker-tools")}</span>
								<select
									{...fieldProps("operating_mode")}
									value={
										typeof setup.requirements.operating_mode === "string"
											? setup.requirements.operating_mode
											: ""
									}
									onChange={(event) => {
										const mode = event.currentTarget.value || null;
										change(
											(current) => ({
												...current,
												requirements: {
													...current.requirements,
													operating_mode: mode,
												},
											}),
											[pathFor("operating_mode")],
										);
									}}
								>
									<option value="">
										{__("Choose an operating mode", "linker-tools")}
									</option>
									<option value="grid_connected">
										{__("Grid-connected", "linker-tools")}
									</option>
									<option value="backup">
										{__("Backup operation", "linker-tools")}
									</option>
								</select>
								{feedback("operating_mode")}
							</label>
							<label className="sc-field">
								<span>{__("Grid connection", "linker-tools")}</span>
								<select
									{...fieldProps("grid_phase")}
									value={
										typeof setup.requirements.grid_phase === "number"
											? String(setup.requirements.grid_phase)
											: ""
									}
									onChange={(event) => {
										const phase = event.currentTarget.value
											? Number(event.currentTarget.value)
											: null;
										change(
											(current) => ({
												...current,
												requirements: {
													...current.requirements,
													grid_phase: phase,
												},
											}),
											[pathFor("grid_phase")],
										);
									}}
								>
									<option value="">—</option>
									<option value="1">
										{__("Single-phase", "linker-tools")}
									</option>
									<option value="3">{__("Three-phase", "linker-tools")}</option>
								</select>
								{feedback("grid_phase")}
							</label>
							{!storageOnly &&
								requirementNumber(
									"pv_dc_kw",
									__("Total PV nameplate rating", "linker-tools"),
									"kWp",
								)}
						</div>
						<details
							className="sc-disclosure"
							open={
								typeof setup.requirements.required_usable_kwh === "number" ||
								typeof setup.requirements.required_discharge_ac_kw === "number"
							}
						>
							<summary>
								{__("Known power and capacity (optional)", "linker-tools")}
							</summary>
							<p>
								{__(
									"Leave these blank to compare equipment configurations. Add a requirement when your project already specifies it.",
									"linker-tools",
								)}
							</p>
							<div className="sc-geometry-fields">
								{requirementNumber(
									"required_usable_kwh",
									__("Total required usable energy", "linker-tools"),
									"kWh",
								)}
								{requirementNumber(
									"required_discharge_ac_kw",
									__(
										"Total required continuous AC discharge power",
										"linker-tools",
									),
									"kW",
								)}
							</div>
						</details>
					</fieldset>
					{props.searchEnabled && (
						<div className="sc-work-panel sc-equipment-search">
							<div className="sc-work-panel-heading">
								<h3>{__("Multi-system combination", "linker-tools")}</h3>
							</div>
							<p>
								{__(
									"Choose the systems in your project. Add known requirements to narrow the equipment combinations.",
									"linker-tools",
								)}
							</p>
							<details className="sc-disclosure">
								<summary>{__("Search scope", "linker-tools")}</summary>
								<p>
									{__(
										"The search uses the system count, requirements for each system and coordination groups you have declared. It checks equipment combinations from current product data for each system and the project, counting one shared controller per group. It does not compare alternative system counts or different allocations of project requirements, or simulate joint energy flows. Unresolved conditions remain shown in the results.",
										"linker-tools",
									)}
								</p>
							</details>
							<div className="sc-work-toolbar">
								<button
									type="button"
									className="sc-button sc-primary"
									disabled={
										blocked ||
										actionsDisabled ||
										!valid ||
										!!draft.pending ||
										!!draft.conflict
									}
									onClick={props.search}
								>
									{__("Find equipment for these systems", "linker-tools")}
								</button>
							</div>
						</div>
					)}
					<section className="sc-work-panel sc-equipment-coordination">
						<div className="sc-plant-toolbar sc-work-panel-heading">
							<h3>{__("Coordination groups", "linker-tools")}</h3>
							<button
								type="button"
								className="sc-button"
								disabled={
									disabled ||
									setup.units.filter(
										(u) =>
											!setup.parallel_groups.some((g) =>
												g.unit_ids.includes(u.id),
											),
									).length < 2
								}
								onClick={() => {
									const id = newId("group");
									change((current) => ({
										...current,
										parallel_groups: [
											...current.parallel_groups,
											{
												id,
												unit_ids: current.units
													.filter(
														(u) =>
															!current.parallel_groups.some((g) =>
																g.unit_ids.includes(u.id),
															),
													)
													.map((u) => u.id),
												controller_product_id: null,
											},
										],
									}));
								}}
							>
								{__("Add coordination group", "linker-tools")}
							</button>
						</div>
						{setup.parallel_groups.map((group, index) => (
							<fieldset
								key={group.id}
								disabled={disabled}
								className="sc-scenario-fields sc-scenario-block"
							>
								<legend>
									{sprintf(
										__("Coordination group %d", "linker-tools"),
										index + 1,
									)}
								</legend>
								<p>
									{__(
										"Choose at least two systems planned to share a controller.",
										"linker-tools",
									)}
								</p>
								<div className="sc-geometry-fields">
									{setup.units.map((unit) => (
										<label className="sc-field" key={unit.id}>
											<span>
												<input
													type="checkbox"
													checked={group.unit_ids.includes(unit.id)}
													disabled={
														!group.unit_ids.includes(unit.id) &&
														setup.parallel_groups.some(
															(g) =>
																g.id !== group.id &&
																g.unit_ids.includes(unit.id),
														)
													}
													onChange={(event) => {
														const checked = event.currentTarget.checked;
														change((current) => ({
															...current,
															parallel_groups: current.parallel_groups.map(
																(g) =>
																	g.id === group.id
																		? {
																				...g,
																				unit_ids: checked
																					? [...g.unit_ids, unit.id]
																					: g.unit_ids.filter(
																							(id) => id !== unit.id,
																						),
																			}
																		: g,
															),
														}));
													}}
												/>
												{unit.name}
											</span>
										</label>
									))}
								</div>
								<label className="sc-field">
									<span>{__("Controller communication", "linker-tools")}</span>
									<select
										value={group.control_network ?? ""}
										disabled={blocked}
										onChange={(event) => {
											const network = event.currentTarget.value;
											change((current) => ({
												...current,
												parallel_groups: current.parallel_groups.map((g) => {
													if (g.id !== group.id) return g;
													const { control_network: _previous, ...rest } = g;
													return network === "lan" || network === "rs485"
														? { ...rest, control_network: network }
														: rest;
												}),
											}));
										}}
									>
										<option value="">
											{__("Not specified", "linker-tools")}
										</option>
										<option value="lan">LAN</option>
										<option value="rs485">RS485</option>
									</select>
								</label>
								<label className="sc-field">
									<span>{__("Shared controller", "linker-tools")}</span>
									<select
										value={group.controller_product_id ?? ""}
										disabled={blocked}
										onChange={(event) => {
											const id = event.currentTarget.value
												? Number(event.currentTarget.value)
												: null;
											change((current) => ({
												...current,
												parallel_groups: current.parallel_groups.map((g) => {
													if (g.id !== group.id) return g;
													// Clearing the controller drops any intent
													// declared for it; picking one keeps it.
													const {
														controller_use: _declared,
														comparison_controller_product_id: _filter,
														...rest
													} = g;
													return id === null
														? { ...rest, controller_product_id: null }
														: {
																...g,
																controller_product_id: id,
																comparison_controller_product_id: id,
															};
												}),
											}));
										}}
									>
										<option value="">
											{__("No controller selected", "linker-tools")}
										</option>
										{group.controller_product_id !== null &&
											!products.some(
												(p) => p.id === group.controller_product_id,
											) && (
												<option value={group.controller_product_id} disabled>
													{__("Select a current controller", "linker-tools")}
												</option>
											)}
										{products
											.filter(
												(p) =>
													catalog.data?.controllers.some(
														(c) => c.id === p.id,
													) || p.id === group.controller_product_id,
											)
											.map((p) => (
												<option key={p.id} value={p.id}>
													{p.brand} {p.model}
												</option>
											))}
									</select>
								</label>
								{group.controller_product_id !== null && (
									<label className="sc-field">
										<span>{__("Controller", "linker-tools")}</span>
										<select
											value={group.controller_use ?? "new"}
											disabled={blocked}
											onChange={(event) => {
												const use = event.currentTarget.value as PartUse;
												change((current) => ({
													...current,
													parallel_groups: current.parallel_groups.map((g) => {
														if (g.id !== group.id) return g;
														const { controller_use: _previous, ...rest } = g;
														return use === "new"
															? rest
															: { ...rest, controller_use: use };
													}),
												}));
											}}
										>
											{PART_USES.map((value) => (
												<option value={value} key={value}>
													{value === "new"
														? __("Buy new", "linker-tools")
														: value === "retain"
															? __("Keep existing", "linker-tools")
															: __("Replace existing", "linker-tools")}
												</option>
											))}
										</select>
									</label>
								)}
								<button
									type="button"
									className="sc-text-button"
									onClick={() =>
										change((current) => ({
											...current,
											parallel_groups: current.parallel_groups.filter(
												(g) => g.id !== group.id,
											),
										}))
									}
								>
									{__("Remove group", "linker-tools")}
								</button>
							</fieldset>
						))}
						<div className="sc-work-toolbar">
							<button
								type="button"
								className="sc-button sc-primary"
								disabled={actionsDisabled || blocked || !valid}
								onClick={props.check}
							>
								{__("Check equipment", "linker-tools")}
							</button>
						</div>
					</section>
				</div>
				<section className="sc-work-panel sc-work-main sc-equipment-systems">
					<div className="sc-plant-toolbar sc-work-panel-heading">
						<h3>{__("Systems in this project", "linker-tools")}</h3>
						<button
							type="button"
							className="sc-button"
							disabled={disabled}
							onClick={() => {
								const id = newId("system");
								change((current) => ({
									...current,
									units: [
										...current.units,
										{
											id,
											name: sprintf(
												__("System %d", "linker-tools"),
												current.units.length + 1,
											),
											inputs: { equipment_setup: equipmentDraft({}) },
										},
									],
								}));
								select(id);
							}}
						>
							{__("Add system", "linker-tools")}
						</button>
					</div>
					{stale.map((unit) => (
						<Notice error key={unit.unit_id}>
							{__(
								"This wiring plan belongs to a removed system. Its strings remain saved until you remove the plan or restore the system.",
								"linker-tools",
							)}{" "}
							{unit.unit_id}
							<button
								type="button"
								className="sc-text-button"
								disabled={disabled}
								onClick={() =>
									edit((inputs) =>
										changePvPlantStringUnit(inputs, unit.unit_id, null),
									)
								}
							>
								{__("Remove wiring plan", "linker-tools")}
							</button>
						</Notice>
					))}
					<nav
						className="sc-plant-switcher"
						aria-label={__("Systems in this project", "linker-tools")}
					>
						{setup.units.map((unit, index) => (
							<button
								key={unit.id}
								type="button"
								className="sc-text-button"
								aria-pressed={unit.id === selected}
								onClick={() => select(unit.id)}
							>
								{unit.name.trim() ||
									sprintf(__("System %d", "linker-tools"), index + 1)}
								{(validity[`unit:${unit.id}`] === false ||
									!unit.name.trim()) && (
									<small> · {__("Needs attention", "linker-tools")}</small>
								)}
							</button>
						))}
					</nav>
					{setup.units.map((unit, unitIndex) => {
						const unitDraft = {
							...draft,
							baseline: { ...draft.baseline, inputs: unit.inputs },
							history: { ...draft.history, current: unit.inputs },
						};
						return (
							<section
								key={unit.id}
								hidden={unit.id !== selected}
								aria-label={unit.name.trim() || __("System", "linker-tools")}
							>
								<div className="sc-plant-toolbar">
									<label className="sc-field">
										<span>{__("System name", "linker-tools")}</span>
										<input
											value={unit.name}
											aria-invalid={!unit.name.trim()}
											maxLength={256}
											disabled={disabled}
											onChange={(event) => {
												const name = event.currentTarget.value;
												change((current) => ({
													...current,
													units: current.units.map((u) =>
														u.id === unit.id ? { ...u, name } : u,
													),
												}));
											}}
										/>
									</label>
									<button
										type="button"
										className="sc-text-button"
										disabled={disabled || setup.units.length === 1}
										onClick={() =>
											change((current) => {
												const units = current.units.filter(
													(u) => u.id !== unit.id,
												);
												return {
													...current,
													units,
													parallel_groups: current.parallel_groups
														.map((g) => ({
															...g,
															unit_ids: g.unit_ids.filter(
																(id) => id !== unit.id,
															),
														}))
														.filter((g) => g.unit_ids.length >= 2),
												};
											})
										}
									>
										{__("Remove system", "linker-tools")}
									</button>
								</div>
								<EquipmentSetup
									{...props}
									draft={unitDraft}
									inputPath={`equipment_plant_setup.units[${unitIndex}].inputs.equipment_setup`}
									storageOnly={storageOnly}
									heading={false}
									embedded
									standalone={false}
									searchEnabled={false}
									active={active && unit.id === selected}
									onValidity={unitCallbacks[unit.id]!}
									edit={(operation) => {
										return change((current) => ({
											...current,
											units: current.units.map((u) => {
												if (u.id !== unit.id) return u;
												return { ...u, inputs: operation(u.inputs) };
											}),
										}));
									}}
								/>
								{!storageOnly && (
									<PlantPvStringSetup
										draft={draft}
										unit={unit}
										units={setup.units}
										edit={edit}
										locale={locale}
										disabled={disabled}
										onValidity={stringCallbacks[unit.id]!}
									/>
								)}
							</section>
						);
					})}
				</section>
			</div>
		</>
	);
}
