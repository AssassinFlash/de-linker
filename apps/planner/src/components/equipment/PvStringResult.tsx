import type { JsonObject } from "../../data/protocol.ts";
import { __, sprintf } from "../../i18n.ts";
import { readObject } from "../../data/readProtocol.ts";
import { PvOperatingResult } from "./PvOperatingResult.tsx";

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
	const standby = value.standby ? readObject(value.standby) : null;
	const standbyFact = standby ? readObject(standby.fact) : null;
	const standbySource = standbyFact?.source
		? readObject(standbyFact.source)
		: null;
	const observation = (result: unknown) =>
		result === "in_interval"
			? __("In standby interval · review", "linker-tools")
			: result === "boundary"
				? __("At the lower boundary · review", "linker-tools")
				: result === "outside_interval"
					? __("Outside interval for this point", "linker-tools")
					: __("Estimate unavailable", "linker-tools");
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
			{standby && (
				<section>
					<h4>{__("Manufacturer standby interval", "linker-tools")}</h4>
					<p>
						{__(
							"The manufacturer describes standby in this input-voltage interval. These MPP estimates do not establish actual operation or annual exposure; a single point cannot determine the state or recovery at the lower boundary. The absolute voltage rating and MPPT window are checked separately.",
							"linker-tools",
						)}
					</p>
					<p>
						{(standby.interval_v as number[]).map(format).join(" – ")} V
						{standbySource && typeof standbySource.url === "string" && (
							<>
								{" "}
								·{" "}
								<a href={standbySource.url} target="_blank" rel="noreferrer">
									{__("Source document", "linker-tools")}
								</a>{" "}
								·{" "}
								{sprintf(
									__("Page %d", "linker-tools"),
									Number(standbySource.page),
								)}
							</>
						)}
					</p>
					<div className="lp-table-scroll">
						<table className="lp-data-table">
							<thead>
								<tr>
									<th>{__("String", "linker-tools")}</th>
									<th>{__("Operating point", "linker-tools")}</th>
									<th>{__("MPP estimate", "linker-tools")}</th>
									<th>{__("Observation", "linker-tools")}</th>
								</tr>
							</thead>
							<tbody>
								{(standby.points as JsonObject[]).map((point) => (
									<tr key={`${point.string_id}:${point.case}`}>
										<td>
											{rows.findIndex((r) => r.id === point.string_id) + 1}
										</td>
										<td>
											{point.case === "stc"
												? "STC"
												: point.case === "hot"
													? __("Modeled hot case", "linker-tools")
													: __("Modeled cold case", "linker-tools")}
										</td>
										<td>{format(point.voltage_v)} V</td>
										<td>{observation(point.observation)}</td>
									</tr>
								))}
							</tbody>
						</table>
					</div>
				</section>
			)}
			{value.operating && (
				<PvOperatingResult
					value={readObject(value.operating)}
					strings={rows}
					locale={locale}
				/>
			)}
		</section>
	);
}
