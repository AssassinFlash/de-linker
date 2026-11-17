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
}: {
	value: SolarSettings;
	onChange: (changes: Partial<SolarSettings>) => void;
	hasAuxiliaryProfile: boolean;
	locale: string;
	disabled: boolean;
	onValidity: (valid: boolean) => void;
	useProfileRange: () => void;
	rangeBusy: boolean;
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
		<fieldset disabled={disabled} className="lp-scenario-fields">
			<h3>{__("Solar-only energy flows", "linker-tools")}</h3>
			<p className="lp-profile-help">
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
			<OperatingPeriodsForm
				periods={value.schedule}
				onChange={(schedule) => onChange({ schedule })}
				locale={locale}
				report={report}
				useProfileRange={useProfileRange}
				rangeBusy={rangeBusy}
				hasStorage={false}
			/>
		</fieldset>
	);
}
