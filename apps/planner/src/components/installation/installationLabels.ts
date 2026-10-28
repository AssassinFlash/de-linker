import type {
	ConductorClosure,
	ConductorSpecification,
	PvStringClosure,
} from "../../domain/installation.ts";
import { formatDecimal } from "../../domain/decimal.ts";
import { __ } from "../../i18n.ts";

/** A declared cross-section is shown as declared, never as a sizing result. */
export function conductorLabel(
	conductor: ConductorSpecification | null,
	locale: string,
): string {
	return conductor === null
		? __("Cross-section not declared", "linker-tools")
		: `${formatDecimal(conductor.cross_section_mm2, locale)} mm²`;
}
export function conductorClosureLabel(status: ConductorClosure): string {
	return {
		declared: __("One cross-section declared", "linker-tools"),
		unconfirmed: __("Cross-section missing for a recorded run", "linker-tools"),
		conflicting: __(
			"Recorded runs declare different cross-sections",
			"linker-tools",
		),
		not_recorded: __("No run recorded", "linker-tools"),
	}[status];
}
export function closureLabel(closure: PvStringClosure): string {
	return closure.recorded
		? __("Cross-section and all quantities recorded", "linker-tools")
		: __("Cross-section or quantity still open", "linker-tools");
}
