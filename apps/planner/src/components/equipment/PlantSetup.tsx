import { useEffect, useMemo, useState } from "react";
import type { ComponentProps } from "react";
import { EquipmentSetup } from "./EquipmentSetup.tsx";
import { useEquipmentProducts } from "../../data/equipmentProducts.ts";
import { isDirty, sameJson } from "../../domain/draft.ts";
import { equipmentDraft } from "../../domain/equipment.ts";
import {
	compilePlant,
	factoryPlant,
	plantInputs,
	readPlantDraft,
	plantIdentity as newId,
} from "../../domain/equipmentPlant.ts";
import type { PlantDraft } from "../../domain/equipmentPlant.ts";
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
		start,
	} = props;
	const catalog = useEquipmentProducts(client, scope, active);
	const setup = useMemo(() => {
		try {
			return readPlantDraft(draft.history.current);
		} catch {
			return null;
		}
	}, [
		draft.history.current.equipment_plant,
		draft.history.current.equipment_plant_setup,
	]);
	const [selectedId, select] = useState<string | null>(null);
	const [validity, setValidity] = useState<Record<string, boolean>>({});
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
	const valid = Object.entries(validity).every(
		([key, ok]) =>
			ok || (key.startsWith("unit:") && !ids.split(",").includes(key.slice(5))),
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
	let prepared = false;
	try {
		prepared =
			!!setup &&
			!blocked &&
			sameJson(
				compilePlant(
					factoryPlant(setup, catalog.data?.assemblies ?? {}),
					products,
				),
				draft.history.current.equipment_plant,
			);
	} catch {
		/* Incomplete inputs remain editable and saveable. */
	}
	function change(operation: (current: PlantDraft) => PlantDraft): boolean {
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
			onError(null);
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
	const requirementNumber = (key: string, label: string, unit: string) => (
		<NumberField
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
				change((current) => ({
					...current,
					requirements: { ...current.requirements, [key]: value },
				}))
			}
		/>
	);
	return (
		<>
			<p className="lp-profile-help">
				{__(
					"Each system has its own equipment selection. Battery equipment may be separate, integrated or absent. Coordination groups record systems planned to share a controller.",
					"linker-tools",
				)}
			</p>
			<p className="lp-profile-help">
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
			<button
				type="button"
				className="lp-text-button"
				disabled={catalog.isFetching || disabled}
				onClick={() => void catalog.refetch()}
			>
				{__("Reload product data", "linker-tools")}
			</button>
			<fieldset
				disabled={disabled}
				className="lp-scenario-fields lp-scenario-block"
			>
				<legend>{__("Project requirements", "linker-tools")}</legend>
				<div className="lp-geometry-fields">
					<label className="lp-field">
						<span>{__("Choose an operating mode", "linker-tools")}</span>
						<select
							value={
								typeof setup.requirements.operating_mode === "string"
									? setup.requirements.operating_mode
									: ""
							}
							onChange={(event) => {
								const mode = event.currentTarget.value || null;
								change((current) => ({
									...current,
									requirements: {
										...current.requirements,
										operating_mode: mode,
									},
								}));
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
					</label>
					<label className="lp-field">
						<span>{__("Grid connection", "linker-tools")}</span>
						<select
							value={
								typeof setup.requirements.grid_phase === "number"
									? String(setup.requirements.grid_phase)
									: ""
							}
							onChange={(event) => {
								const phase = event.currentTarget.value
									? Number(event.currentTarget.value)
									: null;
								change((current) => ({
									...current,
									requirements: {
										...current.requirements,
										grid_phase: phase,
									},
								}));
							}}
						>
							<option value="">—</option>
							<option value="1">{__("Single-phase", "linker-tools")}</option>
							<option value="3">{__("Three-phase", "linker-tools")}</option>
						</select>
					</label>
					{requirementNumber(
						"pv_dc_kw",
						__("Total PV nameplate rating", "linker-tools"),
						"kWp",
					)}
					{requirementNumber(
						"required_usable_kwh",
						__("Total required usable energy", "linker-tools"),
						"kWh",
					)}
					{requirementNumber(
						"required_discharge_ac_kw",
						__("Total required continuous AC discharge power", "linker-tools"),
						"kW",
					)}
				</div>
			</fieldset>
			<div className="lp-plant-toolbar">
				<h3>{__("Systems in this project", "linker-tools")}</h3>
				<button
					type="button"
					className="lp-button lp-button-secondary"
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
			<nav
				className="lp-plant-switcher"
				aria-label={__("Systems in this project", "linker-tools")}
			>
				{setup.units.map((unit, index) => (
					<button
						key={unit.id}
						type="button"
						className="lp-text-button"
						aria-pressed={unit.id === selected}
						onClick={() => select(unit.id)}
					>
						{unit.name.trim() ||
							sprintf(__("System %d", "linker-tools"), index + 1)}
						{(validity[`unit:${unit.id}`] === false || !unit.name.trim()) && (
							<small> · {__("Needs attention", "linker-tools")}</small>
						)}
					</button>
				))}
			</nav>
			{setup.units.map((unit) => {
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
						<div className="lp-plant-toolbar">
							<label className="lp-field">
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
								className="lp-text-button"
								disabled={disabled || setup.units.length === 1}
								onClick={() =>
									change((current) => {
										const units = current.units.filter((u) => u.id !== unit.id);
										return {
											...current,
											units,
											parallel_groups: current.parallel_groups
												.map((g) => ({
													...g,
													unit_ids: g.unit_ids.filter((id) => id !== unit.id),
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
					</section>
				);
			})}
			<div className="lp-plant-toolbar">
				<h3>{__("Coordination groups", "linker-tools")}</h3>
				<button
					type="button"
					className="lp-button lp-button-secondary"
					disabled={
						disabled ||
						setup.units.filter(
							(u) =>
								!setup.parallel_groups.some((g) => g.unit_ids.includes(u.id)),
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
					className="lp-scenario-fields lp-scenario-block"
				>
					<legend>
						{sprintf(__("Coordination group %d", "linker-tools"), index + 1)}
					</legend>
					<p>
						{__(
							"Choose at least two systems planned to share a controller.",
							"linker-tools",
						)}
					</p>
					<div className="lp-geometry-fields">
						{setup.units.map((unit) => (
							<label className="lp-field" key={unit.id}>
								<span>
									<input
										type="checkbox"
										checked={group.unit_ids.includes(unit.id)}
										disabled={
											!group.unit_ids.includes(unit.id) &&
											setup.parallel_groups.some(
												(g) =>
													g.id !== group.id && g.unit_ids.includes(unit.id),
											)
										}
										onChange={(event) => {
											const checked = event.currentTarget.checked;
											change((current) => ({
												...current,
												parallel_groups: current.parallel_groups.map((g) =>
													g.id === group.id
														? {
																...g,
																unit_ids: checked
																	? [...g.unit_ids, unit.id]
																	: g.unit_ids.filter((id) => id !== unit.id),
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
					<label className="lp-field">
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
									parallel_groups: current.parallel_groups.map((g) =>
										g.id === group.id ? { ...g, controller_product_id: id } : g,
									),
								}));
							}}
						>
							<option value="">
								{__("No controller selected", "linker-tools")}
							</option>
							{group.controller_product_id !== null &&
								!products.some((p) => p.id === group.controller_product_id) && (
									<option value={group.controller_product_id} disabled>
										{__("Select a current controller", "linker-tools")}
									</option>
								)}
							{products
								.filter(
									(p) =>
										catalog.data?.controllers.some((c) => c.id === p.id) ||
										p.id === group.controller_product_id,
								)
								.map((p) => (
									<option key={p.id} value={p.id}>
										{p.brand} {p.model}
									</option>
								))}
						</select>
					</label>
					<button
						type="button"
						className="lp-text-button"
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
			<div className="lp-energy-submit">
				<div>
					<strong>
						{prepared
							? __("The multi-system plan is prepared.", "linker-tools")
							: __(
									"Complete the project requirements and choose equipment for every system.",
									"linker-tools",
								)}
					</strong>
					<p>
						{isDirty(draft) || draft.pending
							? __(
									"Save project records these inputs before a new calculation can start.",
									"linker-tools",
								)
							: sprintf(
									__(
										"A new calculation uses saved input revision %d.",
										"linker-tools",
									),
									draft.baseline.revision,
								)}
					</p>
				</div>
				<button
					type="button"
					className="lp-button lp-button-secondary"
					disabled={blocked || actionsDisabled || !valid}
					onClick={() => {
						if (!client.isCurrentScope(scope)) return;
						try {
							const before = readPlantDraft(draft.history.current);
							const preparedSetup = factoryPlant(
								before,
								catalog.data?.assemblies ?? {},
							);
							const compiled = compilePlant(preparedSetup, products);
							if (
								!edit((inputs) => {
									if (!sameJson(readPlantDraft(inputs), before))
										throw new ApiError(409, "conflict");
									return {
										...plantInputs(inputs, preparedSetup),
										equipment_plant: compiled,
									};
								})
							)
								throw new ApiError(409, "conflict");
							onError(null);
						} catch (error) {
							onError(error);
						}
					}}
				>
					{__("Prepare multi-system plan", "linker-tools")}
				</button>
				<button
					type="button"
					className="lp-button"
					disabled={
						blocked ||
						actionsDisabled ||
						!valid ||
						!prepared ||
						isDirty(draft) ||
						!!draft.pending ||
						!!draft.conflict
					}
					onClick={start}
				>
					{__("Check saved multi-system plan", "linker-tools")}
				</button>
			</div>
		</>
	);
}
