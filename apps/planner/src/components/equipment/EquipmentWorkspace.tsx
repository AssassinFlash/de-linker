import { useEffect, useState } from "react";
import type { ComponentProps } from "react";
import { ApiError } from "../../data/protocol.ts";
import { sameJson } from "../../domain/draft.ts";
import { EquipmentSetup } from "./EquipmentSetup.tsx";
import { PlantSetup } from "./PlantSetup.tsx";
import { DeviceConditionInputs } from "./DeviceConditionInputs.tsx";
import {
	beginPlant,
	hasPlant,
	readPlantDraft,
	singleSystem,
	plantIdentity as newId,
	equipmentContext,
	applyEquipmentContext,
} from "../../domain/equipmentPlant.ts";
import { __, sprintf } from "../../i18n.ts";
type Props = ComponentProps<typeof EquipmentSetup>;

export function EquipmentWorkspace(props: Props) {
	const { draft, disabled, client, scope, edit, onError } = props;
	const [equipmentValid, reportValidity] = useState(true);
	const [conditionValid, reportConditionValidity] = useState(true);
	const valid = equipmentValid && conditionValid;
	useEffect(() => {
		props.onValidity(valid);
		return () => props.onValidity(true);
	}, [valid, props.onValidity]);
	const multi = hasPlant(draft.history.current);
	let canReturn = false;
	try {
		const setup = readPlantDraft(draft.history.current);
		canReturn = setup.units.length === 1 && !setup.parallel_groups.length;
	} catch {
		/* A single-system draft has no plant document. */
	}
	function switchMode(targetMulti: boolean) {
		if (disabled || !valid || !client.isCurrentScope(scope)) return;
		try {
			const first = {
					id: newId("system"),
					name: sprintf(__("System %d", "linker-tools"), 1),
				},
				second = {
					id: newId("system"),
					name: sprintf(__("System %d", "linker-tools"), 2),
				};
			const before = equipmentContext(draft.history.current);
			const next = equipmentContext(
				targetMulti
					? beginPlant(draft.history.current, first, second)
					: singleSystem(draft.history.current),
			);
			if (
				!edit((inputs) => {
					if (!sameJson(equipmentContext(inputs), before))
						throw new ApiError(409, "conflict");
					return applyEquipmentContext(inputs, next);
				})
			)
				throw new ApiError(409, "conflict");
			onError(null);
		} catch (error) {
			onError(error);
		}
	}
	return (
		<>
			{props.standalone ? (
				<div className="lp-section-heading">
					<span className="lp-index">08</span>
					<h2 id="lp-equipment-title">{__("Equipment", "linker-tools")}</h2>
				</div>
			) : (
				<h3 id="lp-equipment-title">{__("Equipment", "linker-tools")}</h3>
			)}
			<div
				className="lp-plant-toolbar"
				role="group"
				aria-label={__("System arrangement", "linker-tools")}
			>
				<button
					type="button"
					className="lp-text-button"
					aria-pressed={!multi}
					disabled={disabled || !valid || (multi && !canReturn)}
					onClick={() => {
						if (multi) switchMode(false);
					}}
				>
					{__("Single system", "linker-tools")}
				</button>
				<button
					type="button"
					className="lp-text-button"
					aria-pressed={multi}
					disabled={disabled || !valid}
					onClick={() => {
						if (!multi) switchMode(true);
					}}
				>
					{__("Multiple systems", "linker-tools")}
				</button>
			</div>
			{multi ? (
				<PlantSetup {...props} onValidity={reportValidity} />
			) : (
				<EquipmentSetup
					{...props}
					heading={false}
					onValidity={reportValidity}
				/>
			)}
			<DeviceConditionInputs
				draft={draft}
				edit={edit}
				client={client}
				scope={scope}
				active={props.active}
				disabled={disabled}
				onValidity={reportConditionValidity}
				onError={onError}
			/>
		</>
	);
}
