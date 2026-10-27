import type { ModuleSpec } from "./geometry.ts";
import type { ModuleDraft } from "./solarSetup.ts";
import { sameJson } from "./draft.ts";

export interface ModuleTemplate {
	readonly specification: ModuleSpec;
	readonly parameters: ModuleDraft;
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
