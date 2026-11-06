import type { ModuleSpec } from "./geometry.ts";
import type { ModuleDraft } from "./solarSetup.ts";
import { sameJson } from "./draft.ts";

export const DECLARED_REFERENCE_PREFIX = "declared_reference";

export interface ModuleTemplate {
	readonly specification: ModuleSpec;
	readonly parameters: ModuleDraft;
}

export function isDeclaredReferenceModule(specification: ModuleSpec): boolean {
	return (
		!specification.source.woo &&
		specification.source.kind === "user_declared" &&
		specification.source.note.startsWith(DECLARED_REFERENCE_PREFIX) &&
		typeof specification.gamma_pdc_per_c === "number" &&
		Number.isFinite(specification.gamma_pdc_per_c) &&
		specification.gamma_pdc_per_c < 0 &&
		specification.gamma_pdc_per_c > -1
	);
}

export function declaredModuleParameters(
	specification: ModuleSpec,
): ModuleDraft | undefined {
	if (!isDeclaredReferenceModule(specification)) return undefined;
	return {
		module_spec_id: specification.id,
		gamma_pdc_per_c: specification.gamma_pdc_per_c!,
		source: {
			kind: "user_declared",
			note: specification.source.note,
			document_sha256: null,
			url: null,
			page: null,
		},
	};
}

export function matchesModule(
	specification: ModuleSpec,
	template: ModuleTemplate,
): boolean {
	return (
		!!specification.source.woo &&
		sameJson(
			{ ...specification, id: template.specification.id },
			template.specification,
		)
	);
}

export function resolveModuleParameters(
	specification: ModuleSpec | undefined,
	templates: readonly ModuleTemplate[] | undefined,
): ModuleDraft | undefined {
	if (!specification) return undefined;
	if (isDeclaredReferenceModule(specification))
		return declaredModuleParameters(specification);
	const template = templates?.find((item) =>
		matchesModule(specification, item),
	);
	return template
		? { ...template.parameters, module_spec_id: specification.id }
		: undefined;
}

export function isCurrentRoofModule(
	specification: ModuleSpec | undefined,
	templates: readonly ModuleTemplate[] | undefined,
): boolean {
	if (!specification) return false;
	if (isDeclaredReferenceModule(specification)) return true;
	return !!templates?.some((template) => matchesModule(specification, template));
}
