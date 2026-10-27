import { ApiError } from "./protocol.ts";
import type { JsonObject } from "./protocol.ts";
import { readObject } from "./readProtocol.ts";
import { documentReference } from "./documentReference.ts";

const finite = (v: unknown): v is number =>
	typeof v === "number" && Number.isFinite(v);
const positive = (v: unknown) => finite(v) && v > 0;
const nullable = (v: unknown) => v === null || finite(v);
function invalid(): never {
	throw new ApiError(502, "invalid_run_result");
}
export function readPvOperatingResult(
	value: unknown,
	strings: JsonObject[],
): JsonObject {
	const row = readObject(value),
		model = readObject(row.model),
		conditions = readObject(row.conditions);
	if (
		!["available", "unavailable"].includes(String(model.status)) ||
		model.method !== "woo_batzelis_seeded_desoto_v1" ||
		!Array.isArray(row.points) ||
		![
			conditions.irradiance_w_m2,
			conditions.hot_cell_c,
			conditions.cold_cell_c,
		].every(nullable) ||
		(conditions.source_note !== null &&
			typeof conditions.source_note !== "string")
	)
		invalid();
	for (const value of Object.values(readObject(model.input_facts))) {
		const fact = readObject(value);
		if (fact.source != null) documentReference(fact.source, true);
		else if (model.status === "available") invalid();
	}
	if (model.status === "available") {
		const p = readObject(model.parameters),
			d = readObject(model.diagnostics);
		if (
			![p.a_ref, p.I_L_ref, p.I_o_ref, p.R_sh_ref, p.irrad_ref].every(
				positive,
			) ||
			!finite(p.R_s) ||
			p.R_s < 0 ||
			![
				p.alpha_sc,
				p.EgRef,
				p.dEgdT,
				p.temp_ref,
				model.numerical_residual_relative,
				model.numerical_tolerance_relative,
				d.gamma_pmax_per_c_model,
			].every(finite) ||
			!nullable(d.gamma_pmax_per_c_declared) ||
			typeof model.sha256 !== "string" ||
			!/^[a-f0-9]{64}$/.test(model.sha256)
		)
			invalid();
		readObject(d.stc);
		if (d.noct !== undefined) {
			const n = readObject(d.noct),
				pred = readObject(n.predicted_nominal);
			if (
				!finite(n.cell_c) ||
				!positive(n.reference_irradiance_w_m2) ||
				!nullable(n.declared_p_mp_w) ||
				!positive(pred.p_mp) ||
				![n.cell_c_interval, n.p_mp_at_cell_limits_w].every(
					(a) => Array.isArray(a) && a.length === 2 && a.every(finite),
				)
			)
				invalid();
		}
	} else if (row.points.length) invalid();
	const identities = new Set(strings.map((s) => s.id)),
		seen = new Set<string>();
	if (row.points.length && row.points.length !== strings.length * 2) invalid();
	for (const value of row.points) {
		const p = readObject(value),
			key = String(p.string_id) + ":" + String(p.case);
		if (
			!identities.has(p.string_id) ||
			!["hot", "cold"].includes(String(p.case)) ||
			seen.has(key) ||
			![p.irradiance_w_m2, p.v_mp_v, p.i_mp_a, p.i_sc_a, p.p_mp_w].every(
				positive,
			) ||
			!finite(p.cell_c) ||
			p.cell_c !==
				(p.case === "hot" ? conditions.hot_cell_c : conditions.cold_cell_c) ||
			p.irradiance_w_m2 !== conditions.irradiance_w_m2
		)
			invalid();
		seen.add(key);
	}
	return row;
}
