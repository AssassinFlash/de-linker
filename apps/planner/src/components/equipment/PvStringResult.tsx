import type { JsonObject } from "../../data/protocol.ts";
import { __ } from "../../i18n.ts";

export function PvStringResult({
	value,
	locale,
}: {
	value: JsonObject;
	locale: string;
}) {
	const rows = value.strings as JsonObject[],
		format = (v: unknown) =>
			typeof v === "number"
				? new Intl.NumberFormat(locale, { maximumFractionDigits: 3 }).format(v)
				: "—";
	return (
		<section>
			<h4>{__("PV wiring plan", "linker-tools")}</h4>
			<p>
				{__(
					"The wiring plan records the assigned roof modules. Cold open-circuit voltage uses the stated ambient temperature and the module's voltage coefficient. STC operating points do not establish hot or cold MPP performance, design currents or wiring protection.",
					"linker-tools",
				)}
			</p>
			<dl className="lp-field-summary">
				<div>
					<dt>{__("Lowest design ambient temperature", "linker-tools")}</dt>
					<dd>{format(value.minimum_ambient_c)} °C</dd>
				</div>
				<div>
					<dt>{__("Temperature source and location", "linker-tools")}</dt>
					<dd>
						{typeof value.temperature_source === "string"
							? value.temperature_source
							: "—"}
					</dd>
				</div>
			</dl>
			<div className="lp-table-scroll">
				<table className="lp-data-table">
					<caption>{__("PV strings and inputs", "linker-tools")}</caption>
					<thead>
						<tr>
							{[
								__("String", "linker-tools"),
								"MPPT",
								__("Input", "linker-tools"),
								__("Modules", "linker-tools"),
								__("Vmpp at STC", "linker-tools"),
								__("Cold Voc", "linker-tools"),
							].map((s) => (
								<th key={s} scope="col">
									{s}
								</th>
							))}
						</tr>
					</thead>
					<tbody>
						{rows.map((r, i) => (
							<tr key={String(r.id)}>
								<th scope="row">{i + 1}</th>
								<td>{format(r.mppt)}</td>
								<td>{format(r.input)}</td>
								<td>{format(r.module_count)}</td>
								<td>{format(r.stc_vmpp_v)} V</td>
								<td>{format(r.cold_voc_v)} V</td>
							</tr>
						))}
					</tbody>
				</table>
			</div>
		</section>
	);
}
