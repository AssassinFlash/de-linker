import { equipmentFieldMessage } from "./equipmentLabels.ts";
import { useEffect, useMemo, useState } from "react";
import type { Draft } from "../../domain/draft.ts";
import {
	changeEquipment,
	equipmentDraft,
	factoryEquipment,
	PART_USES,
} from "../../domain/equipment.ts";
import type { EquipmentUse, PartUse } from "../../domain/equipment.ts";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import type { JsonObject } from "../../data/protocol.ts";
import { readObject } from "../../data/readProtocol.ts";
import { useEquipmentProducts } from "../../data/equipmentProducts.ts";
import { __, sprintf } from "../../i18n.ts";
import { NumberField } from "../NumberField.tsx";
import { Notice } from "../Notice.tsx";
import { PvStringSetup } from "./PvStringSetup.tsx";

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
	inputErrors = [],
	inputPath = "equipment_setup",
	search,
	check,
	searchEnabled,
	standalone,
	heading = true,
	embedded = false,
	storageOnly: suppliedStorageOnly = false,
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
	onError: (error: unknown, changed?: readonly string[]) => void;
	inputErrors?: readonly string[];
	inputPath?: string;
	search: () => void;
	check: () => void;
	searchEnabled: boolean;
	standalone: boolean;
	heading?: boolean;
	embedded?: boolean;
	storageOnly?: boolean;
}) {
	const storageOnly =
		suppliedStorageOnly ||
		(draft.history.current.brief !== undefined &&
			readObject(draft.history.current.brief).system_scope === "storage_only");
	const catalog = useEquipmentProducts(client, scope, active);
	const [validity, setValidity] = useState<Record<string, boolean>>({});
	const callbacks = useMemo(
		() =>
			Object.fromEntries(
				[...numericFields, "pv_string_plan"].map((key) => [
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
		draft.history.current.brief,
		draft.history.current.equipment_setup,
		draft.history.current.equipment_selection,
		draft.history.current.equipment_requirements,
	]);
	const products = catalog.data?.products ?? [],
		blocked =
			disabled ||
			catalog.isFetching ||
			!!catalog.error ||
			!catalog.data?.prepared;
	const assembly = setup
		? catalog.data?.assemblies[String(setup.battery_product_id)]
		: undefined;
	const fixedCount =
		assembly?.sales_unit_kind === "battery_system"
			? assembly.fixed_modules_per_stack
			: null;
	useEffect(() => {
		if (fixedCount !== null && fixedCount !== undefined)
			callbacks.modules_per_stack!(true);
	}, [fixedCount, callbacks]);
	function change(patch: JsonObject) {
		if (!disabled && client.isCurrentScope(scope)) {
			edit((inputs) => {
				const next = changeEquipment(inputs, patch);
				return changeEquipment(
					next,
					factoryEquipment(
						equipmentDraft(next),
						catalog.data?.assemblies ?? {},
					),
				);
			});
			onError(
				null,
				Object.keys(patch).map((key) => inputPath + "." + key),
			);
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
	const message = (key: string) =>
		equipmentFieldMessage(inputErrors, inputPath + "." + key);
	const fieldProps = (key: string) => ({
		name: inputPath + "." + key,
		"aria-invalid": Boolean(message(key)),
		"aria-describedby": message(key)
			? inputPath + "." + key + "-error"
			: undefined,
	});
	const feedback = (key: string) =>
		message(key) ? (
			<small className="lp-field-error" id={inputPath + "." + key + "-error"}>
				{message(key)}
			</small>
		) : null;
	const selectedAccessories = Array.isArray(setup.accessory_product_ids)
		? (setup.accessory_product_ids as number[])
		: [];
	/** An all-new plan stores as null, the canonical absence of the field. */
	const nextUse = (
		part: "inverter" | "battery",
		value: PartUse,
	): JsonObject | null => {
		const previous = setup.equipment_use as Partial<EquipmentUse> | null;
		const plan: EquipmentUse = {
			inverter: previous?.inverter ?? "new",
			battery: previous?.battery ?? "new",
			[part]: value,
		};
		return plan.inverter === "new" && plan.battery === "new" ? null : plan;
	};
	const choice = (key: string, label: string, options = products) => (
		<label className="lp-field">
			<span>{label}</span>
			<select
				{...fieldProps(key)}
				value={typeof setup[key] === "number" ? String(setup[key]) : ""}
				disabled={blocked}
				onChange={(event) => {
					const id = event.currentTarget.value
						? Number(event.currentTarget.value)
						: null;
					change(
						// Dropping the battery drops any intent declared for it.
						key === "battery_product_id" && id === null
							? { [key]: id, equipment_use: nextUse("battery", "new") }
							: { [key]: id },
					);
				}}
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
			{feedback(key)}
		</label>
	);
	const useChoice = (part: "inverter" | "battery", label: string) => (
		<label className="lp-field">
			<span>{label}</span>
			<select
				value={
					(setup.equipment_use as Partial<EquipmentUse> | null)?.[part] ?? "new"
				}
				disabled={blocked}
				onChange={(event) =>
					change({
						equipment_use: nextUse(part, event.currentTarget.value as PartUse),
					})
				}
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
			name={inputPath + "." + key}
			error={message(key)}
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
	const requirementFields = (
		<fieldset
			disabled={disabled}
			className="lp-scenario-fields lp-scenario-block"
		>
			<div className="lp-geometry-fields">
				{!embedded && (
					<>
						<label className="lp-field">
							<span>{__("Choose an operating mode", "linker-tools")}</span>
							<select
								{...fieldProps("operating_mode")}
								value={
									typeof setup.operating_mode === "string"
										? setup.operating_mode
										: ""
								}
								onChange={(event) =>
									change({
										operating_mode: event.currentTarget.value || null,
									})
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
							{feedback("operating_mode")}
						</label>
						<label className="lp-field">
							<span>{__("Grid connection", "linker-tools")}</span>
							<select
								{...fieldProps("grid_phase")}
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
							{feedback("grid_phase")}
						</label>
					</>
				)}
				<label className="lp-field">
					<span>{__("Application", "linker-tools")}</span>
					<select
						{...fieldProps("application")}
						value={
							typeof setup.application === "string" ? setup.application : ""
						}
						onChange={(event) =>
							change({ application: event.currentTarget.value || null })
						}
					>
						<option value="">{__("Any application", "linker-tools")}</option>
						<option value="residential">
							{__("Residential", "linker-tools")}
						</option>
						<option value="commercial">
							{__("Commercial", "linker-tools")}
						</option>
					</select>
					{feedback("application")}
				</label>
				{!storageOnly &&
					number("pv_dc_kw", __("PV array", "linker-tools"), "kWp")}
			</div>
			<details
				className="lp-comparison"
				open={
					typeof setup.required_usable_kwh === "number" ||
					typeof setup.required_discharge_ac_kw === "number"
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
				<div className="lp-geometry-fields">
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
			</details>
		</fieldset>
	);
	return (
		<>
			{heading &&
				!embedded &&
				(standalone ? (
					<div className="lp-section-heading">
						<span className="lp-index">08</span>
						<h2 id="lp-equipment-title">{__("Equipment", "linker-tools")}</h2>
					</div>
				) : (
					<h3 id="lp-equipment-title">{__("Equipment", "linker-tools")}</h3>
				))}
			{!embedded && (
				<>
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
				</>
			)}
			{!embedded && requirementFields}

			{!embedded && !storageOnly && (
				<PvStringSetup
					draft={draft}
					edit={edit}
					inverterId={
						typeof setup.inverter_product_id === "number"
							? setup.inverter_product_id
							: null
					}
					locale={locale}
					disabled={disabled}
					onValidity={callbacks.pv_string_plan!}
				/>
			)}
			{!embedded && searchEnabled && (
				<>
					<p>
						{__(
							"Compare equipment configurations, then choose one for your project. Known requirements narrow the choices.",
							"linker-tools",
						)}
					</p>
					<div className="lp-energy-submit">
						<button
							className="lp-button"
							type="button"
							disabled={actionsDisabled || blocked || !valid}
							onClick={search}
						>
							{__("Find equipment combinations", "linker-tools")}
						</button>
					</div>
				</>
			)}
			<details
				className="lp-comparison"
				open={embedded || typeof setup.inverter_product_id === "number"}
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
						{useChoice("inverter", __("Inverter", "linker-tools"))}
						{typeof setup.battery_product_id === "number" &&
							useChoice("battery", __("Battery", "linker-tools"))}
						{fixedCount != null ? (
							<div className="lp-field">
								<span>{__("Fixed internal module count", "linker-tools")}</span>
								<p>
									{sprintf(
										__(
											"The manufacturer specifies %d internal battery modules per battery system.",
											"linker-tools",
										),
										fixedCount,
									)}
								</p>
								{assembly?.documents.map((doc) => (
									<a
										className="lp-text-button"
										key={`${doc.url}:${doc.page}`}
										href={`${doc.url}#page=${doc.page}`}
										target="_blank"
										rel="noopener noreferrer"
									>
										{__("Source", "linker-tools")}
									</a>
								))}
							</div>
						) : (
							number(
								"modules_per_stack",
								__("Battery modules per stack", "linker-tools"),
								"",
								true,
							)
						)}
						{number(
							"parallel_stacks",
							assembly?.sales_unit_kind === "battery_system"
								? __(
										"Number of battery systems for this converter",
										"linker-tools",
									)
								: __("Parallel stacks or systems", "linker-tools"),
							"",
							true,
						)}
					</div>
				</fieldset>
				{embedded && requirementFields}
				<details className="lp-comparison">
					<summary>{__("Additional products", "linker-tools")}</summary>
					<label className="lp-field">
						<span>{__("Choose a product", "linker-tools")}</span>
						<select
							{...fieldProps("accessory_product_ids")}
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
						{feedback("accessory_product_ids")}
					</label>
					{selectedAccessories.map((id, index) => (
						<label className="lp-field" key={id}>
							<span>
								<input
									{...fieldProps(`accessory_product_ids[${index}]`)}
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
							{feedback(`accessory_product_ids[${index}]`)}
						</label>
					))}
				</details>
				{!embedded && (
					<div className="lp-energy-submit">
						<button
							type="button"
							className="lp-button"
							disabled={actionsDisabled || blocked || !valid}
							onClick={check}
						>
							{__("Check equipment", "linker-tools")}
						</button>
					</div>
				)}
			</details>
		</>
	);
}
