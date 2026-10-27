import type { ModuleDraft } from "../../domain/solarSetup.ts";
import type { ModuleSpec } from "../../domain/geometry.ts";
import { formatDecimal, toPercent } from "../../domain/decimal.ts";
import { __, sprintf } from "../../i18n.ts";
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
	return (
		<section className="lp-scenario-block lp-pv-parameters">
			<h4>
				{specification?.model ??
					__("Module specification outside the current layout", "linker-tools")}
			</h4>
			{!value.source.woo ? (
				<Notice>
					{__(
						"A new calculation requires an updated module selection.",
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
					<p>
						<a href={value.source.url!} target="_blank" rel="noreferrer">
							{__("Source document", "linker-tools")}
						</a>{" "}
						· {sprintf(__("Page %d", "linker-tools"), value.source.page!)}
					</p>
				</>
			)}
		</section>
	);
}
