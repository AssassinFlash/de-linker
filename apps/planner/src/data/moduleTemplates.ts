import Ajv2020 from "ajv/dist/2020.js";
import schema from "../contracts/pv-generation.schema.json" with { type: "json" };
import policy from "../contracts/geometry-policy.json" with { type: "json" };
import type { ModuleDraft } from "../domain/solarSetup.ts";
import { emptyGeometry } from "../domain/geometryCommands.ts";
import { readGeometry } from "../domain/validateGeometry.ts";
import { sameJson } from "../domain/draft.ts";
import { ApiError } from "./protocol.ts";
import { readObject } from "./readProtocol.ts";

import type { ModuleTemplate } from "../domain/productModules.ts";
export type { ModuleTemplate } from "../domain/productModules.ts";
export { matchesModule } from "../domain/productModules.ts";
const ajv = new Ajv2020({ strict: true, strictNumbers: true });
const parameters = ajv.compile<ModuleDraft>({
	$defs: schema.$defs,
	$ref: "#/$defs/PvModuleParameters",
});

export function readModuleTemplates(value: unknown): readonly ModuleTemplate[] {
	const reply = readObject(value);
	if (
		reply.schema_version !== 1 ||
		reply.provider !== "woocommerce" ||
		!Array.isArray(reply.pv_modules)
	)
		throw new ApiError(502, "invalid_product_reply");
	return reply.pv_modules.map((value) => {
		const row = readObject(value);
		const specification = readGeometry(
			{
				...emptyGeometry(),
				module_specs: [row.specification],
			},
			policy,
		).module_specs[0]!;
		const gamma = row.parameters;
		if (
			!parameters(gamma) ||
			!specification.source.woo ||
			gamma.module_spec_id !== specification.id ||
			!sameJson(gamma.source.woo, specification.source.woo)
		)
			throw new ApiError(502, "invalid_product_reply");
		return { specification, parameters: gamma };
	});
}
