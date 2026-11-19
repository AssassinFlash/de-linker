import { sameJson } from "./draft.ts";
import type { ModuleSpec } from "./geometry.ts";
import type { ModuleDraft } from "./solarSetup.ts";

export const DECLARED_REFERENCE_PREFIX = "declared_reference";
export function isCurrentRoofModule(
	specification: ModuleSpec | undefined,
): boolean {
	return (
		!!specification &&
		!specification.source.woo &&
		specification.source.kind === "user_declared" &&
		specification.source.note.startsWith(DECLARED_REFERENCE_PREFIX)
	);
}
export function resolveModuleParameters(
	specification: ModuleSpec | undefined,
): ModuleDraft | undefined {
	if (!specification || !isCurrentRoofModule(specification)) return undefined;
	const gamma = specification.gamma_pdc_per_c;
	if (typeof gamma !== "number" || !(gamma < 0 && gamma > -1)) return undefined;
	return {
		module_spec_id: specification.id,
		gamma_pdc_per_c: gamma,
		source: {
			kind: "user_declared",
			note: specification.source.note,
			document_sha256: null,
			url: null,
			page: null,
		},
	};
}

export function samePanelParameters(
	value: ModuleDraft,
	expected: ModuleDraft,
): boolean {
	const { woo, ...source } = value.source;
	return (
		!woo &&
		value.module_spec_id === expected.module_spec_id &&
		value.gamma_pdc_per_c === expected.gamma_pdc_per_c &&
		sameJson(source, expected.source)
	);
}
