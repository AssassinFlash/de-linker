import type { ModuleDraft } from "../../domain/solarSetup.ts";
import type { ModuleSpec } from "../../domain/geometry.ts";
import { DECLARED_REFERENCE_PREFIX } from "../../domain/productModules.ts";
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
	const declaredReference =
		!value.source.woo &&
		value.source.kind === "user_declared" &&
		value.source.note.startsWith(DECLARED_REFERENCE_PREFIX) &&
		value.gamma_pdc_per_c !== null;
	return (
		<section className="lp-scenario-block lp-pv-parameters">
			<h4>
				{specification?.model ??
					__("Module specification outside the current layout", "linker-tools")}
			</h4>
			{!value.source.woo && !declaredReference ? (
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
					{value.source.woo ? (
						<p>
							<a href={value.source.url!} target="_blank" rel="noreferrer">
								{__("Source document", "linker-tools")}
							</a>{" "}
							· {sprintf(__("Page %d", "linker-tools"), value.source.page!)}
						</p>
					) : (
						<p>{value.source.note}</p>
					)}
				</>
			)}
		</section>
	);
}
