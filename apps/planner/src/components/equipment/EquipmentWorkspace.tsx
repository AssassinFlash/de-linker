import { useEffect, useRef, useState } from "react";
import type { ComponentProps } from "react";
import { ApiError } from "../../data/protocol.ts";
import type { Session } from "../../data/protocol.ts";
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
type Props = ComponentProps<typeof EquipmentSetup> & {
	/** The verified session carries the wire limits the design command uses. */
	readonly session: Session;
};

export function EquipmentWorkspace(props: Props) {
	const { draft, disabled, client, scope, edit, onError } = props;
	const target = useRef<HTMLDivElement>(null);
	useEffect(() => {
		if (!props.inputErrors?.length || !props.active || disabled) return;
		const frame = window.requestAnimationFrame(() => {
			const field = [
				...(target.current?.querySelectorAll<HTMLElement>("[name]") ?? []),
			].find(
				(node) =>
					props.inputErrors!.includes(node.getAttribute("name") ?? "") &&
					!node.closest("[hidden]"),
			);
			if (!field) return;
			let ancestor = field.parentElement;
			while (ancestor && ancestor !== target.current) {
				if (ancestor.tagName === "DETAILS")
					(ancestor as HTMLDetailsElement).open = true;
				ancestor = ancestor.parentElement;
			}
			field.focus();
			field.scrollIntoView({ block: "center" });
		});
		return () => window.cancelAnimationFrame(frame);
	}, [props.inputErrors, props.active, disabled]);
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
		<div ref={target} className="sc-equipment-workspace">
			<div className="sc-work-toolbar sc-equipment-heading">
				{props.standalone ? (
					<div className="sc-section-heading">
						<span className="sc-index">08</span>
						<h2 id="sc-equipment-title">{__("Equipment", "linker-tools")}</h2>
					</div>
				) : (
					<h3 id="sc-equipment-title">{__("Equipment", "linker-tools")}</h3>
				)}
				<div
					className="sc-plant-toolbar"
					role="group"
					aria-label={__("System arrangement", "linker-tools")}
				>
					<button
						type="button"
						className="sc-text-button"
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
						className="sc-text-button"
						aria-pressed={multi}
						disabled={disabled || !valid}
						onClick={() => {
							if (!multi) switchMode(true);
						}}
					>
						{__("Multiple systems", "linker-tools")}
					</button>
				</div>
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
		</div>
	);
}
