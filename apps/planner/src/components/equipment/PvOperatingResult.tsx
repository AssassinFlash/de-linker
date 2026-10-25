import type { JsonObject } from "../../data/protocol.ts";
import { readObject } from "../../data/readProtocol.ts";
import { __ } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";

export function PvOperatingResult({
	value,
	strings,
	locale,
}: {
	value: JsonObject;
	strings: JsonObject[];
	locale: string;
}) {
	const model = readObject(value.model),
		conditions = readObject(value.conditions),
		points = value.points as JsonObject[],
		numbers = new Map(strings.map((s, i) => [s.id, i + 1]));
	const format = (v: unknown) =>
		typeof v === "number"
			? new Intl.NumberFormat(locale, {
					maximumSignificantDigits: 6,
					...(v !== 0 && Math.abs(v) < 0.001
						? { notation: "scientific" as const }
						: {}),
				}).format(v)
			: "—";
	const row = (label: string, value: unknown, unit = "") => (
		<div key={label}>
			<dt>{label}</dt>
			<dd>
				{format(value)} {unit}
			</dd>
		</div>
	);
	return (
		<section>
			<h4>{__("Modeled electrical operating points", "linker-tools")}</h4>
			<p>
				{__(
					"These estimates use a fitted single-diode model at the stated uniform module conditions. They do not include shading or establish manufacturer performance, design extremes, protection ratings or country approval.",
					"linker-tools",
				)}
			</p>
			<p>
				{typeof conditions.source_note === "string"
					? conditions.source_note
					: __(
							"Operating conditions and their source are incomplete.",
							"linker-tools",
						)}
			</p>
			{model.status !== "available" && (
				<Notice>
					{__(
						"The maintained module data did not produce an admissible I–V model. The cold-Voc and STC checks remain available.",
						"linker-tools",
					)}
				</Notice>
			)}
			{points.length > 0 && (
				<div className="lp-table-scroll">
					<table className="lp-data-table">
						<caption>
							{__("Operating points by string", "linker-tools")}
						</caption>
						<thead>
							<tr>
								{[
									__("String", "linker-tools"),
									__("Case", "linker-tools"),
									__("Cell temperature", "linker-tools"),
									__("Effective irradiance", "linker-tools"),
									"Vmpp",
									"Impp",
									"Isc",
								].map((v) => (
									<th scope="col" key={v}>
										{v}
									</th>
								))}
							</tr>
						</thead>
						<tbody>
							{points.map((p) => (
								<tr key={String(p.string_id) + String(p.case)}>
									<th scope="row">{numbers.get(p.string_id)}</th>
									<td>
										{p.case === "hot"
											? __("Hot operating case", "linker-tools")
											: __("Cold operating case", "linker-tools")}
									</td>
									<td>{format(p.cell_c)} °C</td>
									<td>{format(p.irradiance_w_m2)} W/m²</td>
									<td>{format(p.v_mp_v)} V</td>
									<td>{format(p.i_mp_a)} A</td>
									<td>{format(p.i_sc_a)} A</td>
								</tr>
							))}
						</tbody>
					</table>
				</div>
			)}
			{model.status === "available" &&
				(() => {
					const p = readObject(model.parameters),
						d = readObject(model.diagnostics),
						n = d.noct ? readObject(d.noct) : null;
					return (
						<details className="lp-comparison">
							<summary>
								{__("Model, inputs and datasheet comparisons", "linker-tools")}
							</summary>
							<p>
								{__(
									"Batzelis initialization and De Soto fitting use the saved STC points and temperature coefficients. The fitted compound parameters do not identify the physical cell-series count. Numerical fit precision is separate from physical accuracy.",
									"linker-tools",
								)}
							</p>
							<p>pvlib {String(model.pvlib_version)}</p>
							<p>
								<a
									href="https://pvlib-python.readthedocs.io/en/v0.16.1/reference/generated/pvlib.ivtools.sdm.fit_desoto_batzelis.html"
									target="_blank"
									rel="noreferrer"
								>
									{__("Fitting method", "linker-tools")}
								</a>{" "}
								·{" "}
								<a
									href="https://pvlib-python.readthedocs.io/en/v0.16.1/reference/generated/pvlib.ivtools.sdm.fit_desoto.html"
									target="_blank"
									rel="noreferrer"
								>
									{__("Numerical refinement", "linker-tools")}
								</a>{" "}
								·{" "}
								<a
									href="https://pvlib-python.readthedocs.io/en/v0.16.1/reference/generated/pvlib.pvsystem.calcparams_desoto.html"
									target="_blank"
									rel="noreferrer"
								>
									{__("Temperature translation", "linker-tools")}
								</a>
							</p>
							<dl className="lp-field-summary">
								{row("a,ref", p.a_ref, "V")}
								{row("IL,ref", p.I_L_ref, "A")}
								{row("I0,ref", p.I_o_ref, "A")}
								{row("Rs", p.R_s, "Ω")}
								{row("Rsh,ref", p.R_sh_ref, "Ω")}
								{row("αIsc", p.alpha_sc, "A/K")}
								{row(
									__("Silicon bandgap assumption", "linker-tools"),
									p.EgRef,
									"eV",
								)}
								{row(
									__("Bandgap temperature assumption", "linker-tools"),
									p.dEgdT,
									"1/K",
								)}
								{row(
									__("Numerical fit tolerance", "linker-tools"),
									model.numerical_tolerance_relative,
								)}
								{row(
									__("Relative numerical residual", "linker-tools"),
									model.numerical_residual_relative,
								)}
								{row(
									__("Declared power temperature coefficient", "linker-tools"),
									typeof d.gamma_pmax_per_c_declared === "number"
										? d.gamma_pmax_per_c_declared * 100
										: null,
									"%/°C",
								)}
								{row(
									__("Model power temperature coefficient", "linker-tools"),
									typeof d.gamma_pmax_per_c_model === "number"
										? d.gamma_pmax_per_c_model * 100
										: null,
									"%/°C",
								)}
							</dl>
							<p>
								{__(
									"The power coefficient and NOCT values were not fitting targets. These comparisons show differences; they do not certify extrapolation accuracy.",
									"linker-tools",
								)}
							</p>
							{n && (
								<dl className="lp-field-summary">
									{row(
										__("NOCT reference irradiance", "linker-tools"),
										n.reference_irradiance_w_m2,
										"W/m²",
									)}
									<div>
										<dt>
											{__("NOCT cell-temperature interval", "linker-tools")}
										</dt>
										<dd>
											{(n.cell_c_interval as number[]).map(format).join(" – ")}{" "}
											°C
										</dd>
									</div>
									{row(
										__("Declared NOCT cell temperature", "linker-tools"),
										n.cell_c,
										"°C",
									)}
									{row(
										__("Declared NOCT power", "linker-tools"),
										n.declared_p_mp_w,
										"W",
									)}
									{row(
										__("Model power at nominal NOCT", "linker-tools"),
										readObject(n.predicted_nominal).p_mp,
										"W",
									)}
									<div>
										<dt>
											{__(
												"Model powers at the NOCT temperature limits",
												"linker-tools",
											)}
										</dt>
										<dd>
											{(n.p_mp_at_cell_limits_w as number[])
												.map(format)
												.join(" / ")}{" "}
											W
										</dd>
									</div>
								</dl>
							)}
							<div className="lp-table-scroll">
								<table className="lp-data-table">
									<caption>
										{__("Module facts used by the model", "linker-tools")}
									</caption>
									<thead>
										<tr>
											<th>{__("Quantity", "linker-tools")}</th>
											<th>{__("Value", "linker-tools")}</th>
											<th>{__("Source document", "linker-tools")}</th>
										</tr>
									</thead>
									<tbody>
										{Object.entries(readObject(model.input_facts)).map(
											([key, value]) => {
												const f = readObject(value),
													s = f.source ? readObject(f.source) : null;
												const name: Record<string, string> = {
													vmpp_v: "Vmpp (STC)",
													impp_a: "Impp (STC)",
													voc_v: "Voc (STC)",
													isc_a: "Isc (STC)",
													alpha_isc_pct_per_c: "αIsc",
													beta_voc_pct_per_c: "βVoc",
													cell_technology: __(
														"Cell technology",
														"linker-tools",
													),
												};
												return (
													<tr key={key}>
														<th scope="row">{name[key]}</th>
														<td>
															{String(f.raw_value)} {String(f.raw_unit ?? "")}
														</td>
														<td>
															{s && (
																<a
																	href={String(s.url)}
																	target="_blank"
																	rel="noreferrer"
																>
																	{__("Source document", "linker-tools")} ·{" "}
																	{String(s.page)}
																</a>
															)}
														</td>
													</tr>
												);
											},
										)}
									</tbody>
								</table>
							</div>
						</details>
					);
				})()}
		</section>
	);
}
