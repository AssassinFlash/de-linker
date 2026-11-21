import { useEffect, useMemo, useState } from "react";
import type { JsonObject } from "../../data/protocol.ts";
import { __ } from "../../i18n.ts";
import { NumberField } from "../NumberField.tsx";

export function EquipmentDemandSetup({
	value,
	onChange,
	onValidity,
	locale,
	disabled,
}: {
	value: JsonObject | undefined;
	onChange: (value: JsonObject | null) => void;
	onValidity: (valid: boolean) => void;
	locale: string;
	disabled: boolean;
}) {
	const [validity, setValidity] = useState<Record<string, boolean>>({});
	const callbacks = useMemo(
		() =>
			Object.fromEntries(
				["initial", "unserved"].map((key) => [
					key,
					(valid: boolean) =>
						setValidity((previous) =>
							previous[key] === valid
								? previous
								: { ...previous, [key]: valid },
						),
				]),
			),
		[],
	);
	const fraction = value?.initial_usable_fraction;
	const unserved = value?.max_unserved_load_kwh;
	const complete =
		typeof fraction === "number" &&
		fraction >= 0 &&
		fraction <= 1 &&
		typeof unserved === "number" &&
		unserved >= 0 &&
		typeof value?.source_note === "string" &&
		value.source_note.trim().length > 0;
	const valid =
		value === undefined || (complete && Object.values(validity).every(Boolean));
	useEffect(() => {
		onValidity(valid);
		return () => onValidity(true);
	}, [valid, onValidity]);
	return (
		<fieldset
			className="sc-scenario-fields sc-scenario-block"
			disabled={disabled}
		>
			<label className="sc-field">
				<span>
					<input
						type="checkbox"
						checked={value !== undefined}
						onChange={(event) => {
							setValidity({});
							onChange(
								event.currentTarget.checked
									? {
											schema_version: 1,
											initial_usable_fraction: null,
											max_unserved_load_kwh: null,
											source_note: "",
										}
									: null,
							);
						}}
					/>
					{__("Compare against energy needs", "linker-tools")}
				</span>
			</label>
			{value !== undefined && (
				<>
					<p className="sc-field-help">
						{__(
							"The comparison uses the periods and load in Energy use and the efficiency and power settings in Storage. Usable capacity comes from each equipment combination.",
							"linker-tools",
						)}
					</p>
					<div className="sc-geometry-fields">
						<NumberField
							name="equipment_demand.initial_usable_fraction"
							label={__("Initial usable capacity", "linker-tools")}
							unit="%"
							locale={locale}
							min={0}
							max={100}
							value={typeof fraction === "number" ? fraction * 100 : null}
							onChange={(percent) =>
								onChange({
									...value,
									initial_usable_fraction:
										percent === null ? null : percent / 100,
								})
							}
							onValidity={callbacks.initial!}
						/>
						<NumberField
							name="equipment_demand.max_unserved_load_kwh"
							label={__("Allowed unserved load", "linker-tools")}
							unit="kWh"
							locale={locale}
							min={0}
							value={typeof unserved === "number" ? unserved : null}
							onChange={(amount) =>
								onChange({ ...value, max_unserved_load_kwh: amount })
							}
							onValidity={callbacks.unserved!}
						/>
					</div>
					<label className="sc-field">
						<span>{__("Source note", "linker-tools")}</span>
						<textarea
							name="equipment_demand.source_note"
							value={
								typeof value.source_note === "string" ? value.source_note : ""
							}
							onChange={(event) =>
								onChange({ ...value, source_note: event.currentTarget.value })
							}
						/>
					</label>
					{!complete && (
						<p role="status" className="sc-field-help">
							{__(
								"Enter the initial usable capacity, allowed unserved load and source note to compare energy needs.",
								"linker-tools",
							)}
						</p>
					)}
				</>
			)}
		</fieldset>
	);
}
