import { ProductPicker } from "../shared/ProductPicker.tsx";
import { ProductCard } from "../shared/ProductCard.tsx";
import { CatalogStatus } from "../shared/CatalogStatus.tsx";
import { useProductCards } from "../../data/productCards.ts";
import { useState } from "react";
import Ajv2020 from "ajv/dist/2020.js";
import schema from "../../contracts/existing-system.schema.json" with { type: "json" };
import { ApiError } from "../../data/protocol.ts";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import {
	useEquipmentProducts,
	type BatteryAssemblies,
	type EquipmentProduct,
} from "../../data/equipmentProducts.ts";
import type { JsonObject } from "../../data/protocol.ts";
import {
	changeEquipment,
	comparisonModels,
	equipmentDraft,
	factoryEquipment,
	type EquipmentUse,
	type PartUse,
} from "../../domain/equipment.ts";
import {
	applyEquipmentContext,
	beginPlant,
	equipmentContext,
	hasPlant,
	plantIdentity,
	plantInputs,
	readPlantDraft,
	singleSystem,
} from "../../domain/equipmentPlant.ts";
import { invalidateEnergyReplay } from "../../domain/energyScenario.ts";
import { readPvPlantStringPlan } from "../../domain/pvPlantStrings.ts";
import { readBrief } from "../../domain/brief.ts";
import { __, sprintf } from "../../i18n.ts";

interface ExistingSystem extends JsonObject {
	schema_version: 1;
	name: string;
	inverter_power_kw: number | null;
	keep_inverter: boolean;
}

const checkExisting = new Ajv2020({
	strict: true,
	strictNumbers: true,
}).compile<ExistingSystem>(schema);
export function existingSystem(inputs: JsonObject): ExistingSystem | undefined {
	const value = inputs.existing_system;
	if (value === undefined) return undefined;
	if (!checkExisting(value)) throw new ApiError(422, "invalid_input");
	return value;
}

export function changeExistingSystem(
	current: JsonObject,
	patch: Partial<ExistingSystem> | null,
): JsonObject {
	const {
		existing_system: _previous,
		equipment_candidate: _candidate,
		...rest
	} = current;
	return patch === null
		? rest
		: {
				...rest,
				existing_system: {
					schema_version: 1,
					name: "",
					inverter_power_kw: null,
					keep_inverter: false,
					...existingSystem(current),
					...patch,
				},
			};
}

export function retainsUnverifiedInverter(inputs: JsonObject): boolean {
	if (existingSystem(inputs)?.keep_inverter !== true) return false;
	const primary = equipmentDraft(
		hasPlant(inputs)
			? (readPlantDraft(inputs).units[0]?.inputs ?? inputs)
			: inputs,
	);
	const use = primary.equipment_use as EquipmentUse | null | undefined;
	return !(
		typeof primary.inverter_product_id === "number" &&
		primary.inverter_product_id > 0 &&
		use?.inverter === "retain"
	);
}

function EquipmentDeclarations({
	client,
	scope,
	locale,
	source,
	products,
	assemblies,
	disabled,
	solarOnly,
	change,
}: {
	client: PlannerClient;
	scope: string;
	locale: string;
	source: JsonObject;
	products: readonly EquipmentProduct[];
	assemblies: BatteryAssemblies;
	disabled: boolean;
	solarOnly: boolean;
	change: (patch: JsonObject) => void;
}) {
	const setup = equipmentDraft(source);
	const use = (setup.equipment_use as EquipmentUse | null | undefined) ?? {
		inverter: "new",
		battery: "new",
	};
	const partUse = (part: "inverter" | "battery", value: PartUse) => {
		const revised = { ...use, [part]: value };
		return revised.inverter === "new" && revised.battery === "new"
			? null
			: revised;
	};
	const fixedModules =
		assemblies[String(setup.battery_product_id)]?.fixed_modules_per_stack;
	const positiveCount = (
		name: "modules_per_stack" | "parallel_stacks",
		label: string,
	) => (
		<label className="sc-field">
			<span>{label}</span>
			<input
				type="number"
				min={1}
				step={1}
				max={Number.MAX_SAFE_INTEGER}
				disabled={disabled}
				value={String(setup[name] ?? "")}
				onChange={(event) => {
					const count = event.currentTarget.valueAsNumber;
					change({
						[name]: Number.isSafeInteger(count) && count > 0 ? count : null,
					});
				}}
			/>
		</label>
	);
	const choices = (
		part: "inverter" | "battery",
		label: string,
		useLabel: string,
		options: readonly EquipmentProduct[],
	) => {
		const field = `${part}_product_id`;
		const selected =
			use[part] === "retain" ? setup[field] : comparisonModels(setup)[field];
		const current = options.some((product) => product.id === selected);
		const chooseModel = (id: number | null) =>
			change({
				[field]: id,
				...(id === null ? { equipment_use: partUse(part, "new") } : {}),
				...(part === "battery"
					? { modules_per_stack: null, parallel_stacks: null }
					: {}),
			});
		return (
			<>
				<div className="sc-model-field">
					<label className="sc-field">
						<span>{label}</span>
						<select
							value={String(selected ?? "")}
							disabled={disabled}
							onChange={(event) =>
								chooseModel(
									options.find(
										(p) => String(p.id) === event.currentTarget.value,
									)?.id ?? null,
								)
							}
						>
							<option value="">{__("Not specified", "linker-tools")}</option>
							{selected != null && !current && (
								<option value={String(selected)}>
									{__("Saved product unavailable", "linker-tools")}
								</option>
							)}
							{options.map((product) => (
								<option key={product.id} value={product.id}>
									{`${product.brand} ${product.model}`.trim()}
								</option>
							))}
						</select>
					</label>
					<ProductPicker
						options={options}
						client={client}
						scope={scope}
						locale={locale}
						disabled={disabled}
						selected={selected}
						onSelect={chooseModel}
					/>
				</div>
				<label className="sc-field">
					<span>{useLabel}</span>
					<select
						value={use[part]}
						disabled={disabled}
						onChange={(event) => {
							const value = event.currentTarget.value as PartUse;
							if (value !== "retain" || current)
								change({ equipment_use: partUse(part, value) });
						}}
					>
						<option value="new">{__("Buy new", "linker-tools")}</option>
						<option value="retain" disabled={!current}>
							{__("Keep existing", "linker-tools")}
						</option>
						<option value="replace">
							{__("Replace existing", "linker-tools")}
						</option>
					</select>
				</label>
			</>
		);
	};
	return (
		<>
			<div className="sc-fields">
				{choices(
					"inverter",
					__("Inverter or integrated storage system", "linker-tools"),
					__("Inverter use", "linker-tools"),
					products.filter(
						(product) =>
							product.device_class === "inverters" ||
							Object.hasOwn(product.figures, "ac_output_kw_nominal"),
					),
				)}
				{!solarOnly &&
					choices(
						"battery",
						__("Battery or storage system", "linker-tools"),
						__("Battery use", "linker-tools"),
						products.filter((product) =>
							[
								"system_usable_energy_kwh",
								"system_nominal_energy_kwh",
								"module_energy_kwh_nominal",
								"module_energy_kwh_usable",
							].some((figure) => Object.hasOwn(product.figures, figure)),
						),
					)}
				{!solarOnly && use.battery === "retain" && (
					<>
						{fixedModules == null ? (
							positiveCount(
								"modules_per_stack",
								__("Modules per stack", "linker-tools"),
							)
						) : (
							<label className="sc-field">
								<span>{__("Modules per stack", "linker-tools")}</span>
								<input readOnly value={fixedModules} />
							</label>
						)}
						{positiveCount(
							"parallel_stacks",
							__("Parallel stacks", "linker-tools"),
						)}
					</>
				)}
			</div>
			{Array.isArray(setup.accessory_product_ids) &&
				setup.accessory_product_ids.length > 0 && (
					<ul>
						{setup.accessory_product_ids.map((id) => {
							const accessory = products.find((product) => product.id === id);
							return (
								<li key={String(id)}>
									{accessory
										? `${accessory.brand} ${accessory.model}`.trim()
										: __("Saved product unavailable", "linker-tools")}
								</li>
							);
						})}
					</ul>
				)}
		</>
	);
}

export function ProjectEquipment({
	inputs,
	client,
	scope,
	disabled,
	edit,
	intake = false,
	initiallyOpen = false,
}: {
	inputs: JsonObject;
	client: PlannerClient;
	scope: string;
	disabled: boolean;
	edit: (operation: (inputs: JsonObject) => JsonObject) => boolean;
	intake?: boolean;
	initiallyOpen?: boolean;
}) {
	const authorized = client.isCurrentScope(scope);
	const catalog = useEquipmentProducts(client, scope, authorized);
	const [transitionError, setTransitionError] = useState(false);
	const plant = hasPlant(inputs) ? readPlantDraft(inputs) : null;
	const existing = existingSystem(inputs);
	const wiring =
		inputs.pv_plant_string_plan === undefined
			? []
			: readPvPlantStringPlan(inputs.pv_plant_string_plan).units;
	const canReturn =
		plant?.units.length === 1 &&
		!plant.parallel_groups.length &&
		wiring.every(
			(unit) =>
				unit.unit_id === plant.units[0]?.id &&
				unit.inverter_instance_id === null,
		);
	const productData =
		authorized && !catalog.isError && catalog.data?.prepared
			? catalog.data
			: undefined;
	const scopeOfWork =
		inputs.brief === undefined ? null : readBrief(inputs.brief).system_scope;
	const solarOnly = scopeOfWork === "pv_only";
	const productIds = (
		plant ? plant.units.map((unit) => unit.inputs) : [inputs]
	).flatMap((source) => {
		const setup = equipmentDraft(source);
		return [
			setup.inverter_product_id,
			setup.battery_product_id,
			...(setup.accessory_product_ids as number[]),
		].filter((id): id is number => typeof id === "number");
	});
	const locale = document.documentElement.lang || "en";
	const cards = useProductCards(client, scope, locale, productIds);
	const primary = equipmentDraft(plant?.units[0]?.inputs ?? inputs);
	const primaryUse = primary.equipment_use as EquipmentUse | null | undefined;
	const retainedModel =
		typeof primary.inverter_product_id === "number" &&
		primaryUse?.inverter === "retain";
	function changeExisting(patch: Partial<ExistingSystem> | null) {
		if (disabled || !client.isCurrentScope(scope)) return;
		edit((current) => changeExistingSystem(current, patch));
	}

	function update(transform: (current: JsonObject) => JsonObject) {
		if (disabled || !client.isCurrentScope(scope)) return;
		setTransitionError(false);
		edit((current) =>
			invalidateEnergyReplay(
				applyEquipmentContext(current, equipmentContext(transform(current))),
			),
		);
	}
	function unitName(index: number) {
		return sprintf(__("System %d", "linker-tools"), index);
	}
	function newUnit(index: number) {
		return { id: plantIdentity("system"), name: unitName(index) };
	}
	function changeArrangement(multiple: boolean) {
		if (multiple === Boolean(plant)) return;
		if (multiple) {
			const first = newUnit(1),
				second = newUnit(2);
			update((current) => beginPlant(current, first, second));
		} else {
			try {
				update(singleSystem);
			} catch {
				setTransitionError(true);
			}
		}
	}
	function updateUnit(
		id: string,
		patch: { name: string } | { hardware: JsonObject },
	) {
		update((current) => {
			const existing = readPlantDraft(current);
			return plantInputs(current, {
				...existing,
				units: existing.units.map((unit) =>
					unit.id !== id
						? unit
						: "name" in patch
							? { ...unit, name: patch.name }
							: {
									...unit,
									inputs: updateHardware(unit.inputs, patch.hardware),
								},
				),
			});
		});
	}
	function updateHardware(source: JsonObject, patch: JsonObject) {
		const amended = changeEquipment(source, patch);
		return changeEquipment(
			amended,
			factoryEquipment(equipmentDraft(amended), productData!.assemblies),
		);
	}
	const capacityField = (
		label: string,
		setup: JsonObject,
		change: (kw: number | null) => void,
	) =>
		scopeOfWork !== "storage_only" && (
			<label className="sc-field">
				<span>{label} (kWp)</span>
				<input
					type="number"
					min="0"
					step="any"
					disabled={disabled || !productData}
					value={String(setup.pv_dc_kw ?? "")}
					onChange={(event) => {
						const input = event.currentTarget;
						if (input.validity.valid)
							change(input.value === "" ? null : input.valueAsNumber);
					}}
				/>
			</label>
		);
	const declarations = (
		source: JsonObject,
		change: (patch: JsonObject) => void,
	) => (
		<EquipmentDeclarations
			client={client}
			scope={scope}
			locale={locale}
			source={source}
			products={productData?.products ?? []}
			assemblies={productData?.assemblies ?? {}}
			disabled={disabled || !productData}
			solarOnly={solarOnly}
			change={change}
		/>
	);
	return (
		<section
			className="sc-existing-system"
			aria-label={__("System arrangement", "linker-tools")}
		>
			<label className="sc-check">
				<input
					type="checkbox"
					checked={Boolean(existing)}
					disabled={disabled || !authorized}
					onChange={(event) =>
						changeExisting(event.currentTarget.checked ? {} : null)
					}
				/>{" "}
				{__("There is an existing system", "linker-tools")}
			</label>
			{existing && (
				<div className="sc-fields">
					<label className="sc-field">
						<span>{__("Existing system name", "linker-tools")}</span>
						<input
							maxLength={256}
							value={existing.name}
							disabled={disabled || !authorized}
							onChange={(event) =>
								changeExisting({ name: event.currentTarget.value })
							}
						/>
					</label>
					<label className="sc-field">
						<span>{__("Existing inverter power (kW)", "linker-tools")}</span>
						<input
							type="number"
							min="0"
							step="any"
							value={existing.inverter_power_kw ?? ""}
							disabled={disabled || !authorized}
							onChange={(event) => {
								const kw = event.currentTarget.valueAsNumber;
								changeExisting({
									inverter_power_kw: Number.isFinite(kw) && kw > 0 ? kw : null,
								});
							}}
						/>
					</label>
					<label className="sc-check sc-field-wide">
						<input
							type="checkbox"
							checked={existing.keep_inverter}
							disabled={disabled || !authorized}
							onChange={(event) =>
								changeExisting({ keep_inverter: event.currentTarget.checked })
							}
						/>{" "}
						{__("Keep the existing inverter", "linker-tools")}
					</label>
				</div>
			)}
			{existing?.keep_inverter && !retainedModel && (
				<p className="sc-muted">
					{__(
						"You can continue with the existing inverter. Confirm its model to check equipment compatibility.",
						"linker-tools",
					)}
				</p>
			)}
			{productIds.length > 0 && (
				<section className="sc-selected-products" data-selected-equipment>
					<h3>{__("Selected products", "linker-tools")}</h3>
					<CatalogStatus
						pending={cards.isPending}
						failed={cards.isError}
						retry={() => void cards.refetch()}
					/>
					<div className="linker-product-list">
						{[...new Set(productIds)].map((id) => {
							const card = cards.isSuccess ? cards.data.get(id) : undefined;
							const known = productData?.products.find(
								(item) => item.id === id,
							);
							if (!known && !card && !cards.isSuccess) return null;
							const label =
								card?.label ||
								(known
									? [known.brand, known.model].filter(Boolean).join(" ")
									: __("Saved product unavailable", "linker-tools"));
							return (
								<ProductCard key={id} {...card} label={label}>
									{cards.isSuccess && !card && known
										? __("Saved product unavailable", "linker-tools")
										: null}
								</ProductCard>
							);
						})}
					</div>
				</section>
			)}
			<details
				className="sc-project-equipment"
				open={plant || intake || initiallyOpen ? true : undefined}
			>
				<summary>
					{__("Equipment and system arrangement", "linker-tools")}
				</summary>
				{intake ? (
					<label className="sc-field">
						<span>{__("System arrangement", "linker-tools")}</span>
						<select
							name="system_arrangement"
							value={plant ? "multiple" : "single"}
							disabled={disabled || !authorized}
							onChange={(event) =>
								changeArrangement(event.currentTarget.value === "multiple")
							}
						>
							<option value="single" disabled={Boolean(plant && !canReturn)}>
								{__("Single system", "linker-tools")}
							</option>
							<option value="multiple">
								{__("Multiple systems", "linker-tools")}
							</option>
						</select>
					</label>
				) : (
					<div className="sc-actions">
						<button
							type="button"
							className="sc-button"
							aria-pressed={!plant}
							disabled={disabled || !authorized || Boolean(plant && !canReturn)}
							onClick={() => changeArrangement(false)}
						>
							{__("Single system", "linker-tools")}
						</button>
						<button
							type="button"
							className="sc-button"
							aria-pressed={Boolean(plant)}
							disabled={disabled || !authorized}
							onClick={() => changeArrangement(true)}
						>
							{__("Multiple systems", "linker-tools")}
						</button>
					</div>
				)}
				{plant && !canReturn && (
					<p className="sc-muted">
						{__(
							"To switch to a single system, keep one system and resolve its wiring and coordination groups.",
							"linker-tools",
						)}
					</p>
				)}
				{transitionError && (
					<p role="alert">
						{__(
							"This system arrangement could not be changed.",
							"linker-tools",
						)}
					</p>
				)}

				{catalog.isError ? (
					<p role="alert">
						{__("Product data could not be loaded.", "linker-tools")}{" "}
						<button
							type="button"
							className="sc-button"
							disabled={!authorized}
							onClick={() => void catalog.refetch()}
						>
							{__("Try again", "linker-tools")}
						</button>
					</p>
				) : authorized && catalog.isPending ? (
					<p role="status">{__("Loading product data…", "linker-tools")}</p>
				) : authorized && catalog.data && !productData ? (
					<p role="status">
						{__("Current product data is being prepared.", "linker-tools")}
					</p>
				) : null}
				{plant ? (
					<>
						{capacityField(
							__("Total PV nameplate rating", "linker-tools"),
							plant.requirements,
							(pv_dc_kw) =>
								update((current) => {
									const draft = readPlantDraft(current);
									return plantInputs(current, {
										...draft,
										requirements: { ...draft.requirements, pv_dc_kw },
									});
								}),
						)}
						{plant.units.map((unit, index) => (
							<fieldset
								key={unit.id}
								data-project-system={unit.id}
								className="sc-card"
								disabled={disabled || !authorized}
							>
								<legend>{unit.name || unitName(index + 1)}</legend>
								<label className="sc-field">
									<span>{__("System name", "linker-tools")}</span>
									<input
										required
										maxLength={256}
										value={unit.name}
										onChange={(event) =>
											updateUnit(unit.id, { name: event.currentTarget.value })
										}
									/>
								</label>
								{capacityField(
									__("Allocated PV nameplate rating", "linker-tools"),
									equipmentDraft(unit.inputs),
									(pv_dc_kw) => updateUnit(unit.id, { hardware: { pv_dc_kw } }),
								)}
								{declarations(unit.inputs, (hardware) =>
									updateUnit(unit.id, { hardware }),
								)}
								<button
									className="sc-button"
									type="button"
									disabled={
										plant.units.length === 1 ||
										(existing?.keep_inverter && index === 0) ||
										wiring.some((row) => row.unit_id === unit.id) ||
										plant.parallel_groups.some((group) =>
											group.unit_ids.includes(unit.id),
										)
									}
									onClick={() =>
										update((current) => {
											const existing = readPlantDraft(current);
											return plantInputs(current, {
												...existing,
												units: existing.units.filter(
													(item) => item.id !== unit.id,
												),
											});
										})
									}
								>
									{__("Remove system", "linker-tools")}
								</button>
							</fieldset>
						))}
						<button
							className="sc-button"
							type="button"
							disabled={disabled || !authorized}
							onClick={() => {
								const unit = newUnit(plant.units.length + 1);
								update((current) => {
									const existing = readPlantDraft(current);
									return plantInputs(current, {
										...existing,
										units: [
											...existing.units,
											{
												...unit,
												inputs: { equipment_setup: equipmentDraft({}) },
											},
										],
									});
								});
							}}
						>
							{__("Add system", "linker-tools")}
						</button>
					</>
				) : (
					declarations(inputs, (patch) =>
						update((current) => updateHardware(current, patch)),
					)
				)}
			</details>
		</section>
	);
}
