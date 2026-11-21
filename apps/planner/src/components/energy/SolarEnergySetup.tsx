import { useCallback, useEffect, useState } from "react";
import type { ScenarioDraft } from "../../domain/energyScenario.ts";
import { __ } from "../../i18n.ts";
import { OperatingPeriodsForm } from "./OperatingPeriodsForm.tsx";
import { ScenarioNumber } from "./ScenarioNumber.tsx";

type SolarSettings = Pick<ScenarioDraft, "schedule" | "aux_ac_kw">;

export function SolarEnergySetup({
	value,
	onChange,
	hasAuxiliaryProfile,
	locale,
	disabled,
	onValidity,
	useProfileRange,
	rangeBusy,
	inputErrors,
	inputPath,
	section = "operation",
}: {
	value: SolarSettings;
	onChange: (changes: Partial<SolarSettings>) => void;
	hasAuxiliaryProfile: boolean;
	locale: string;
	disabled: boolean;
	onValidity: (valid: boolean) => void;
	useProfileRange: () => void;
	rangeBusy: boolean;
	inputErrors?: readonly string[];
	inputPath?: string;
	section?: "storage" | "operation";
}) {
	const [validity, setValidity] = useState<Record<string, boolean>>({});
	const report = useCallback((field: string, valid: boolean) => {
		setValidity((previous) =>
			previous[field] === valid ? previous : { ...previous, [field]: valid },
		);
	}, []);
	useEffect(() => {
		onValidity(Object.values(validity).every(Boolean));
		return () => onValidity(true);
	}, [validity, onValidity]);
	return (
		<fieldset disabled={disabled} className="sc-scenario-fields sc-work-main">
			<section className="sc-work-panel" hidden={section !== "storage"}>
				<h3 className="sc-work-panel-heading">
					{__("Solar-only energy flows", "linker-tools")}
				</h3>
				<p className="sc-field-help">
					{__(
						"Use available AC PV generation and load at the common metering point. This project has no battery storage.",
						"linker-tools",
					)}
				</p>
				{(!hasAuxiliaryProfile || value.aux_ac_kw != null) && (
					<ScenarioNumber
						field="aux"
						label={__("Constant AC auxiliary demand", "linker-tools")}
						unit="kW"
						locale={locale}
						value={value.aux_ac_kw ?? null}
						report={report}
						onChange={(aux_ac_kw) => onChange({ aux_ac_kw })}
					/>
				)}
			</section>
			<div hidden={section !== "operation"}>
				<OperatingPeriodsForm
					periods={value.schedule}
					inputErrors={inputErrors}
					inputPath={inputPath}
					onChange={(schedule) => onChange({ schedule })}
					locale={locale}
					report={report}
					useProfileRange={useProfileRange}
					rangeBusy={rangeBusy}
					hasStorage={false}
				/>
			</div>
		</fieldset>
	);
}
