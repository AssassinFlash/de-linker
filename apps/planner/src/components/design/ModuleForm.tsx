import { useState } from "react";
import type { ModuleSpec } from "../../domain/geometry.ts";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import {
	DEFAULT_MODULE_TIER,
	MODULE_TIERS,
	moduleSpecFromTier,
	tierFor,
} from "../../domain/moduleTiers.ts";
import type { GeometryFormProps } from "./RoofForm.tsx";
import { GeometryForm } from "./GeometryForm.tsx";
import { formatDecimal, toPercent } from "../../domain/decimal.ts";
import { __ } from "../../i18n.ts";

const millimetres = (value: number) => String(Math.round(value * 1000));

export function ModuleForm({
	locale,
	commit,
	cancel,
	onValidity,
	module,
}: GeometryFormProps & {
	module: ModuleSpec | null;
	/** Shared design-form contract; the tier list needs no product catalog. */
	client: PlannerClient;
	scope: string;
}) {
	const [selection, setSelection] = useState(
		(module ? tierFor(module.stc_power_w) : DEFAULT_MODULE_TIER).id,
	);
	const tier =
		MODULE_TIERS.find((item) => item.id === selection) ?? DEFAULT_MODULE_TIER;
	return (
		<GeometryForm
			title={__("Module specification", "linker-tools")}
			locale={locale}
			cancel={cancel}
			onValidity={onValidity}
			measurementHelp={false}
			submit={() =>
				commit({
					type: "put_module",
					before: module,
					value: moduleSpecFromTier(
						tier,
						module?.id ?? "module_" + crypto.randomUUID().replaceAll("-", ""),
					),
				})
			}
		>
			<p>
				{__(
					"Planning reference module specification (customer-supplied, not a Linker sales product); dimensions and power are generic reference values, and the customer's actual modules govern.",
					"linker-tools",
				)}
			</p>
			<label className="lp-field">
				<span>{__("Choose a module", "linker-tools")}</span>
				<select
					required
					value={tier.id}
					onChange={(event) => setSelection(event.currentTarget.value)}
				>
					{MODULE_TIERS.map((item) => (
						<option key={item.id} value={item.id}>
							{`${item.stc_power_w} Wp · ${millimetres(item.length_m)} × ${millimetres(item.width_m)} mm`}
						</option>
					))}
				</select>
			</label>
			<dl className="lp-design-quantities">
				{(
					[
						[__("Module length", "linker-tools"), tier.length_m, "m"],
						[__("Module width", "linker-tools"), tier.width_m, "m"],
						[__("Module thickness", "linker-tools"), tier.thickness_m, "m"],
						[__("Rated power at STC", "linker-tools"), tier.stc_power_w, "W"],
						[
							__("Temperature coefficient of maximum power", "linker-tools"),
							toPercent(tier.gamma_pdc_per_c),
							"%/°C",
						],
						[
							__("Open-circuit voltage at STC", "linker-tools"),
							tier.voc_v,
							"V",
						],
						[__("MPP voltage at STC", "linker-tools"), tier.vmp_v, "V"],
						[
							__("Short-circuit current at STC", "linker-tools"),
							tier.isc_a,
							"A",
						],
						[__("MPP current at STC", "linker-tools"), tier.imp_a, "A"],
					] as const
				).map(([label, value, unit]) => (
					<div key={label}>
						<dt>{label}</dt>
						<dd>
							{formatDecimal(value, locale)} <small>{unit}</small>
						</dd>
					</div>
				))}
			</dl>
			<p>
				{__(
					"“Apply properties” updates the module values in this draft. “Save project” saves the changes.",
					"linker-tools",
				)}
			</p>
		</GeometryForm>
	);
}
