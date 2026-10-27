import { useEffect, useMemo } from "react";
import type { Draft } from "../../domain/draft.ts";
import type { JsonObject } from "../../data/protocol.ts";
import { ApiError } from "../../data/protocol.ts";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import { useEquipmentProducts } from "../../data/equipmentProducts.ts";
import {
	changeDeviceCondition,
	conditionBindingMatches,
	conditionDeviceKey,
	equipmentConditionTargets,
	readEquipmentConditionInputs,
	removeDeviceCondition,
} from "../../domain/equipmentConditionInputs.ts";
import type {
	ConditionTarget,
	DeviceConditionInput,
	DeviceRole,
	EquipmentSelectionRef,
} from "../../domain/equipmentConditionInputs.ts";
import { __, sprintf } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";

export function deviceRoleLabel(role: DeviceRole): string {
	return {
		inverter: __("Inverter", "linker-tools"),
		battery: __("Battery", "linker-tools"),
		accessory: __("Accessory", "linker-tools"),
	}[role];
}
function referenceLabel(ref: EquipmentSelectionRef): string {
	if (ref.kind === "plant_controller")
		return sprintf(
			__("Coordination group %s · Shared controller", "linker-tools"),
			ref.group_id,
		);
	return [
		ref.kind === "plant_unit"
			? sprintf(__("System %s", "linker-tools"), ref.unit_id)
			: null,
		deviceRoleLabel(ref.role),
	]
		.filter(Boolean)
		.join(" · ");
}
function targetLabel(target: ConditionTarget): string {
	return target.selection_ref.kind === "plant_controller"
		? sprintf(
				__("Coordination group %d · Shared controller", "linker-tools"),
				target.group_index!,
			)
		: [target.unit_name, deviceRoleLabel(target.selection_ref.role)]
				.filter(Boolean)
				.join(" · ");
}

/** Optional private project observations use the existing Draft/save/recovery path. */
export function DeviceConditionInputs({
	draft,
	edit,
	client,
	scope,
	active,
	disabled,
	onValidity,
	onError,
}: {
	draft: Draft;
	edit: (operation: (inputs: JsonObject) => JsonObject) => boolean;
	client: PlannerClient;
	scope: string;
	active: boolean;
	disabled: boolean;
	onValidity: (valid: boolean) => void;
	onError: (error: unknown) => void;
}) {
	const catalog = useEquipmentProducts(client, scope, active);
	const products = catalog.data?.products ?? [];
	const inputs = draft.history.current;
	const enabled = inputs.equipment_condition_inputs !== undefined;
	const state = useMemo(() => {
		try {
			const observations =
				inputs.equipment_condition_inputs === undefined
					? null
					: readEquipmentConditionInputs(inputs.equipment_condition_inputs);
			const targets = equipmentConditionTargets(inputs, products);
			return { observations, targets, invalid: false };
		} catch {
			return { observations: null, targets: [], invalid: true };
		}
	}, [inputs, products]);
	const stale =
		state.observations?.devices.filter(
			(device) =>
				!state.targets.some((target) =>
					conditionBindingMatches(device, target),
				),
		) ?? [];
	const valid = !enabled || (!state.invalid && stale.length === 0);
	useEffect(() => {
		onValidity(valid);
		return () => onValidity(true);
	}, [valid, onValidity]);
	function change(operation: (current: JsonObject) => JsonObject) {
		if (disabled || !client.isCurrentScope(scope)) return;
		try {
			if (!edit(operation)) throw new ApiError(409, "conflict");
			onError(null);
		} catch (error) {
			onError(error);
		}
	}
	const remove = (device: DeviceConditionInput) =>
		change((current) => removeDeviceCondition(current, device));
	return (
		<details className="lp-comparison" open={enabled}>
			<summary>{__("Device model and firmware", "linker-tools")}</summary>
			<p>
				{__(
					"Optional project entries describe the model and firmware or software planned for or observed on each device. Blank fields mean unknown. Product data remains the reference; these entries do not change it.",
					"linker-tools",
				)}
			</p>
			<label className="lp-field">
				<span>
					<input
						type="checkbox"
						checked={enabled}
						disabled={disabled}
						onChange={(event) => {
							const checked = event.currentTarget.checked;
							change((current) => {
								if (checked)
									return current.equipment_condition_inputs === undefined
										? {
												...current,
												equipment_condition_inputs: {
													schema_version: 1,
													devices: [],
												},
											}
										: current;
								const { equipment_condition_inputs: _removed, ...rest } =
									current;
								return rest;
							});
						}}
					/>{" "}
					{__(
						"Include a review of device details against linked files",
						"linker-tools",
					)}
				</span>
			</label>
			{enabled && (
				<>
					<p className="lp-profile-help">
						{__(
							"Save project records these entries. A new equipment check or report compares them with labelled fields in each linked certificate file. Version strings are kept exactly, including leading zeros. Removing this option removes the entries from this draft; Undo can restore them.",
							"linker-tools",
						)}
					</p>
					{state.invalid && (
						<Notice error>
							{__(
								"The device entries could not be read. Undo the last edit, or remove this optional review and enter the details again.",
								"linker-tools",
							)}
						</Notice>
					)}
					{stale.length > 0 && (
						<Notice error>
							<p>
								{__(
									"Some entries belong to a different device, system or product revision. Their original values are shown below. Remove those entries before saving, then enter any details that apply to the current selection.",
									"linker-tools",
								)}
							</p>
						</Notice>
					)}
					{stale.map((device) => (
						<section
							className="lp-result-section"
							key={conditionDeviceKey(device)}
						>
							<h4>
								{__("Entry needs a current device reference", "linker-tools")}
							</h4>
							<dl className="lp-run-records">
								<div>
									<dt>{__("Device reference", "linker-tools")}</dt>
									<dd>{referenceLabel(device.selection_ref)}</dd>
								</div>
								<div>
									<dt>{__("Recorded product revision", "linker-tools")}</dt>
									<dd>
										<code>{device.product_revision}</code>
									</dd>
								</div>
								<div>
									<dt>{__("Declared model", "linker-tools")}</dt>
									<dd>
										{device.declared_model ?? __("Unknown", "linker-tools")}
									</dd>
								</div>
								<div>
									<dt>{__("Declared firmware or software", "linker-tools")}</dt>
									<dd>
										{device.declared_firmware ?? __("Unknown", "linker-tools")}
									</dd>
								</div>
								<div>
									<dt>{__("Source note", "linker-tools")}</dt>
									<dd>{device.source_note ?? __("Unknown", "linker-tools")}</dd>
								</div>
							</dl>
							<button
								type="button"
								className="lp-text-button"
								disabled={disabled}
								onClick={() => remove(device)}
							>
								{__("Remove entry", "linker-tools")}
							</button>
						</section>
					))}
					{state.targets.length === 0 && !state.invalid && (
						<p>
							{__(
								"Device fields appear after products are selected. Unknown details can remain blank and the project can be saved.",
								"linker-tools",
							)}
						</p>
					)}
					{state.targets.map((target) => {
						const existing = state.observations?.devices.find(
							(device) =>
								conditionDeviceKey(device) === conditionDeviceKey(target),
						);
						const bound =
							existing && conditionBindingMatches(existing, target)
								? existing
								: null;
						const blocked =
							disabled ||
							!target.product_revision ||
							!!catalog.error ||
							catalog.isFetching ||
							(!!existing && !bound);
						return (
							<fieldset
								className="lp-scenario-fields lp-scenario-block"
								key={conditionDeviceKey(target)}
								disabled={blocked}
							>
								<legend>{targetLabel(target)}</legend>
								<p>
									{__("Product model reference", "linker-tools")}:{" "}
									{target.model ??
										__("Current product data unavailable", "linker-tools")}
								</p>
								<div className="lp-geometry-fields">
									{(
										[
											["declared_model", __("Declared model", "linker-tools")],
											[
												"declared_firmware",
												__("Declared firmware or software", "linker-tools"),
											],
											["source_note", __("Source note", "linker-tools")],
										] as const
									).map(([field, label]) => (
										<label className="lp-field" key={field}>
											<span>{label}</span>
											{field === "source_note" ? (
												<textarea
													value={bound?.[field] ?? ""}
													maxLength={4096}
													placeholder={__("Unknown", "linker-tools")}
													onChange={(event) => {
														const value = event.currentTarget.value;
														change((current) =>
															changeDeviceCondition(
																current,
																target,
																{ [field]: value },
																products,
															),
														);
													}}
												/>
											) : (
												<input
													type="text"
													value={bound?.[field] ?? ""}
													maxLength={4096}
													placeholder={__("Unknown", "linker-tools")}
													autoComplete="off"
													spellCheck={false}
													onChange={(event) => {
														const value = event.currentTarget.value;
														change((current) =>
															changeDeviceCondition(
																current,
																target,
																{ [field]: value },
																products,
															),
														);
													}}
												/>
											)}
										</label>
									))}
								</div>
								<p className="lp-profile-help">
									{__(
										"The source note can name a device label, commissioning record or planned configuration. It is saved with this device entry.",
										"linker-tools",
									)}
								</p>
								{bound && (
									<button
										type="button"
										className="lp-text-button"
										onClick={() => remove(bound)}
									>
										{__("Remove entry", "linker-tools")}
									</button>
								)}
							</fieldset>
						);
					})}
				</>
			)}
		</details>
	);
}
