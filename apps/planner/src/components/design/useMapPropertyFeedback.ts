import { useEffect, useRef } from "react";
import { revealActionResult } from "../revealActionResult.ts";

/** Both drawing forms keep field/refusal feedback beside its editable control. */
export function useMapPropertyFeedback(
	error: string | null,
	invalidField: string | null,
) {
	const form = useRef<HTMLFormElement>(null),
		result = useRef<HTMLDivElement>(null);
	useEffect(() => {
		if (invalidField) {
			const input = form.current?.elements.namedItem(invalidField);
			if (input instanceof window.HTMLElement) revealActionResult(input);
		} else if (error) revealActionResult(result.current);
	}, [invalidField, error]);
	return { form, result };
}
