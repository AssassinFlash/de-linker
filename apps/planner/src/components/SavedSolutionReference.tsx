import type { Json, JsonObject } from "../data/protocol.ts";
import { __ } from "../i18n.ts";

/** An input archive is editable project data, never permission or equipment proof. */
export function SavedSolutionReference({ value }: { value: Json | undefined }) {
	if (!value || typeof value !== "object" || Array.isArray(value)) return null;
	const source = value as JsonObject;
	if (source.authority !== "historical_user_input") return null;
	return (
		<details className="lp-section">
			<summary>{__("Original inputs", "linker-tools")}</summary>
			<p>{typeof source.title === "string" ? source.title : ""}</p>
			<a
				className="lp-text-button"
				download="saved-solution-inputs.json"
				href={
					"data:application/json;charset=utf-8," +
					encodeURIComponent(JSON.stringify(value, null, 2))
				}
			>
				{__("Download original inputs (JSON)", "linker-tools")}
			</a>
		</details>
	);
}
