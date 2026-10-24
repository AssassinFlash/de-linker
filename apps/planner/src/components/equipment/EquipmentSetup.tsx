import { useEffect, useMemo, useState } from "react";
import { compileEquipmentRequirements } from "../../domain/equipmentRequirements.ts";
import type { Draft } from "../../domain/draft.ts";
import { isDirty, sameJson } from "../../domain/draft.ts";
import {
	changeEquipment,
	compileEquipment,
	equipmentDraft,
} from "../../domain/equipment.ts";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import type { JsonObject } from "../../data/protocol.ts";
import { useEquipmentProducts } from "../../data/equipmentProducts.ts";
import { __, sprintf } from "../../i18n.ts";
import { NumberField } from "../NumberField.tsx";
import { Notice } from "../Notice.tsx";

const numericFields = [
	"modules_per_stack",
	"parallel_stacks",
	"pv_dc_kw",
	"required_usable_kwh",
	"required_discharge_ac_kw",
] as const;
type NumericField = (typeof numericFields)[number];
export function EquipmentSetup({
	draft,
	edit,
	client,
	scope,
	active,
	locale,
	disabled,
	actionsDisabled,
	onValidity,
	onError,
	start,
	search,
	searchEnabled,
	standalone,
}: {
	draft: Draft;
	edit: (change: (inputs: JsonObject) => JsonObject) => boolean;
	client: PlannerClient;
	scope: string;
	active: boolean;
	locale: string;
	disabled: boolean;
	actionsDisabled: boolean;
	onValidity: (valid: boolean) => void;
	onError: (error: unknown) => void;
	start: () => void;
	search: () => void;
	searchEnabled: boolean;
	standalone: boolean;
}) {
	const catalog = useEquipmentProducts(client, scope, active);
	const [validity, setValidity] = useState<Record<string, boolean>>({});
	const callbacks = useMemo(
		() =>
			Object.fromEntries(
				numericFields.map((key) => [
					key,
					(valid: boolean) =>
						setValidity((state) =>
							state[key] === valid ? state : { ...state, [key]: valid },
						),
				]),
			),
		[],
	);
	const valid = Object.values(validity).every(Boolean);
	useEffect(() => {
		onValidity(valid);
		return () => onValidity(true);
	}, [valid, onValidity]);
	const setup = useMemo(() => {
		try {
			return equipmentDraft(draft.history.current);
		} catch {
			return null;
		}
	}, [
		draft.history.current.equipment_setup,
		draft.history.current.equipment_selection,
	]);
	const products = catalog.data?.products ?? [],
		blocked =
			disabled ||
			catalog.isFetching ||
			!!catalog.error ||
			!catalog.data?.prepared;
	let prepared = false;
	try {
		prepared =
			!!setup &&
			!blocked &&
			sameJson(
				compileEquipment(setup, products),
				draft.history.current.equipment_selection,
			);
	} catch {
		/* Incomplete selections remain editable. */
	}
	let searchPrepared = false;
	try {
		searchPrepared =
			!!setup &&
			sameJson(
				compileEquipmentRequirements(setup),
				draft.history.current.equipment_requirements,
			);
	} catch {
		/* Missing project demand stays editable. */
	}
	function change(patch: JsonObject) {
		if (!disabled && client.isCurrentScope(scope)) {
			edit((inputs) => changeEquipment(inputs, patch));
			onError(null);
		}
	}
	if (!setup)
		return (
			<Notice error>
				{__(
					"Equipment selection requires a product and valid quantities.",
					"linker-tools",
				)}
			</Notice>
		);
	const selectedAccessories = Array.isArray(setup.accessory_product_ids)
		? (setup.accessory_product_ids as number[])
		: [];
	const choice = (key: string, label: string, options = products) => (
		<label className="lp-field">
			<span>{label}</span>
			<select
				value={typeof setup[key] === "number" ? String(setup[key]) : ""}
				disabled={blocked}
				onChange={(event) =>
					change({
						[key]: event.currentTarget.value
							? Number(event.currentTarget.value)
							: null,
					})
				}
			>
				<option value="">
					{key === "battery_product_id"
						? __("No separate battery", "linker-tools")
						: __("Choose a product", "linker-tools")}
				</option>
				{options.map((p) => (
					<option value={p.id} key={p.id}>
						{p.brand} {p.model}
					</option>
				))}
			</select>
		</label>
	);
	const converters = products.filter(
		(p) =>
			p.device_class === "inverters" ||
			Object.hasOwn(p.figures, "ac_output_kw_nominal"),
	);
	const storage = products.filter((p) =>
		[
			"system_usable_energy_kwh",
			"system_nominal_energy_kwh",
			"module_energy_kwh_nominal",
			"module_energy_kwh_usable",
		].some((key) => Object.hasOwn(p.figures, key)),
	);
	const number = (
		key: NumericField,
		label: string,
		unit: string,
		integer = false,
	) => (
		<NumberField
			key={key}
			label={label}
			unit={unit}
			value={typeof setup[key] === "number" ? (setup[key] as number) : null}
			locale={locale}
			min={integer ? 1 : 0}
			integer={integer}
			onChange={(value) => change({ [key]: value })}
			onValidity={callbacks[key]!}
		/>
	);
	return (
		<>
			{standalone ? (
				<div className="lp-section-heading">
					<span className="lp-index">08</span>
					<h2 id="lp-equipment-title">{__("Equipment", "linker-tools")}</h2>
				</div>
			) : (
				<h3 id="lp-equipment-title">{__("Equipment", "linker-tools")}</h3>
			)}
			<p className="lp-profile-help">
				{__(
					"Product properties come from Linker's product data. Each result records the product data and documents used.",
					"linker-tools",
				)}
			</p>
			{catalog.error && (
				<Notice error>
					{__("Product data could not be loaded.", "linker-tools")}
				</Notice>
			)}
			{(catalog.isFetching || (catalog.data && !catalog.data.prepared)) && (
				<p role="status">
					{__("Current product data is being prepared.", "linker-tools")}
				</p>
			)}
			<button
				className="lp-text-button"
				type="button"
				disabled={catalog.isFetching || disabled}
				onClick={() => void catalog.refetch()}
			>
				{__("Reload product data", "linker-tools")}
			</button>
			<fieldset
				disabled={disabled}
				className="lp-scenario-fields lp-scenario-block"
			>
				<div className="lp-geometry-fields">
					<label className="lp-field">
						<span>{__("Choose an operating mode", "linker-tools")}</span>
						<select
							value={
								typeof setup.operating_mode === "string"
									? setup.operating_mode
									: ""
							}
							onChange={(event) =>
								change({ operating_mode: event.currentTarget.value || null })
							}
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
								typeof setup.grid_phase === "number"
									? String(setup.grid_phase)
									: ""
							}
							onChange={(event) =>
								change({
									grid_phase: event.currentTarget.value
										? Number(event.currentTarget.value)
										: null,
								})
							}
						>
							<option value="">—</option>
							<option value="1">{__("Single-phase", "linker-tools")}</option>
							<option value="3">{__("Three-phase", "linker-tools")}</option>
						</select>
					</label>
					{number("pv_dc_kw", __("PV array", "linker-tools"), "kWp")}
					{number(
						"required_usable_kwh",
						__("Required usable energy", "linker-tools"),
						"kWh",
					)}
					{number(
						"required_discharge_ac_kw",
						__("Required continuous AC discharge power", "linker-tools"),
						"kW",
					)}
				</div>
			</fieldset>

			{searchEnabled && (
				<>
					<p>
						{__(
							"Find combinations using the requirements above. Selecting products is optional.",
							"linker-tools",
						)}
					</p>
					<p>
						{searchPrepared
							? __(
									"The saved requirements are ready for the search.",
									"linker-tools",
								)
							: __(
									"Prepare the search, then save the project.",
									"linker-tools",
								)}
					</p>
					<div className="lp-energy-submit">
						<button
							className="lp-button lp-button-secondary"
							type="button"
							disabled={disabled || !valid}
							onClick={() => {
								if (!setup) return;
								try {
									const requirements = compileEquipmentRequirements(setup);
									if (client.isCurrentScope(scope)) {
										edit((inputs) => ({
											...inputs,
											equipment_requirements: requirements,
										}));
										onError(null);
									}
								} catch (error) {
									onError(error);
								}
							}}
						>
							{__("Prepare equipment search", "linker-tools")}
						</button>
						<button
							className="lp-button"
							type="button"
							disabled={
								!searchPrepared ||
								isDirty(draft) ||
								actionsDisabled ||
								blocked ||
								!valid
							}
							onClick={search}
						>
							{__("Find equipment combinations", "linker-tools")}
						</button>
					</div>
				</>
			)}
			<details
				className="lp-comparison"
				open={typeof setup.inverter_product_id === "number"}
			>
				<summary>{__("Choose equipment manually", "linker-tools")}</summary>
				<p>
					{__(
						"Choose products to check their combination against the requirements entered here.",
						"linker-tools",
					)}
				</p>
				<fieldset
					disabled={disabled}
					className="lp-scenario-fields lp-scenario-block"
				>
					<div className="lp-geometry-fields">
						{choice(
							"inverter_product_id",
							__("Inverter or integrated storage system", "linker-tools"),
							converters,
						)}
						{choice(
							"battery_product_id",
							__("Battery or storage system", "linker-tools"),
							storage,
						)}
						{number(
							"modules_per_stack",
							__("Battery modules per stack", "linker-tools"),
							"",
							true,
						)}
						{number(
							"parallel_stacks",
							__("Parallel stacks or systems", "linker-tools"),
							"",
							true,
						)}
					</div>
				</fieldset>
				<details className="lp-comparison">
					<summary>{__("Additional products", "linker-tools")}</summary>
					<label className="lp-field">
						<span>{__("Choose a product", "linker-tools")}</span>
						<select
							value=""
							disabled={blocked}
							onChange={(event) => {
								const id = Number(event.currentTarget.value);
								if (id)
									change({
										accessory_product_ids: [...selectedAccessories, id],
									});
							}}
						>
							<option value="">{__("Choose a product", "linker-tools")}</option>
							{products
								.filter(
									(p) =>
										p.id !== setup.inverter_product_id &&
										p.id !== setup.battery_product_id &&
										!selectedAccessories.includes(p.id),
								)
								.map((p) => (
									<option key={p.id} value={p.id}>
										{p.brand} {p.model}
									</option>
								))}
						</select>
					</label>
					{selectedAccessories.map((id) => (
						<label className="lp-field" key={id}>
							<span>
								<input
									type="checkbox"
									checked
									disabled={disabled}
									onChange={() =>
										change({
											accessory_product_ids: selectedAccessories.filter(
												(value) => value !== id,
											),
										})
									}
								/>
								{products.find((p) => p.id === id)?.model ??
									__("Use current product data", "linker-tools")}
							</span>
						</label>
					))}
				</details>
				<div className="lp-energy-submit">
					<div>
						<strong>
							{prepared
								? __(
										"Equipment selection prepared in this draft",
										"linker-tools",
									)
								: __(
										"Choose products and prepare the selection before saving the project.",
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
						disabled={
							actionsDisabled ||
							blocked ||
							!valid ||
							!setup.inverter_product_id ||
							!setup.operating_mode
						}
						onClick={() => {
							try {
								const value = compileEquipment(setup, products);
								edit((current) => ({ ...current, equipment_selection: value }));
								onError(null);
							} catch (error) {
								onError(error);
							}
						}}
					>
						{__("Prepare equipment selection", "linker-tools")}
					</button>
					<button
						type="button"
						className="lp-button"
						disabled={
							actionsDisabled ||
							!valid ||
							!prepared ||
							isDirty(draft) ||
							!!draft.pending ||
							!!draft.conflict
						}
						onClick={start}
					>
						{__("Check saved equipment selection", "linker-tools")}
					</button>
				</div>
			</details>
		</>
	);
}
