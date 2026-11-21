import type { ModuleDraft } from "../../domain/solarSetup.ts";
import type { ModuleSpec } from "../../domain/geometry.ts";
import {
	resolveModuleParameters,
	samePanelParameters,
} from "../../domain/productModules.ts";
import { panelLabel } from "../../domain/panelParameters.ts";
import { formatDecimal, toPercent } from "../../domain/decimal.ts";
import { __ } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";

export function PvModuleParameters({
	value,
	specification,
	locale,
}: {
	value: ModuleDraft;
	specification: ModuleSpec | undefined;
	locale: string;
}) {
	const expected = resolveModuleParameters(specification);
	return (
		<section className="sc-scenario-block sc-pv-parameters">
			<h4>
				{specification
					? panelLabel(specification, locale)
					: __(
							"Module specification outside the current layout",
							"linker-tools",
						)}
			</h4>
			{expected && !samePanelParameters(value, expected) ? (
				<Notice>
					{__(
						"Update the parameters to use the coefficient recorded for this panel.",
						"linker-tools",
					)}
				</Notice>
			) : !expected ? (
				<Notice>
					{__(
						"Enter the temperature coefficient from the panel data sheet in the roof layout to calculate detailed energy.",
						"linker-tools",
					)}
				</Notice>
			) : (
				<>
					<dl>
						<div>
							<dt>
								{__("Temperature coefficient of maximum power", "linker-tools")}
							</dt>
							<dd>
								{formatDecimal(toPercent(value.gamma_pdc_per_c)!, locale)} %/°C
							</dd>
						</div>
					</dl>
				</>
			)}
		</section>
	);
}
