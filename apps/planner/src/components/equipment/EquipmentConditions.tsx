import type { Json, JsonObject } from "../../data/protocol.ts";
import { readObject } from "../../data/readProtocol.ts";
import { __, sprintf } from "../../i18n.ts";

/** Display only the conditions and documents frozen with this assessment. */
export function EquipmentConditions({
	assessment,
	locale,
}: {
	assessment: JsonObject;
	locale: string;
}) {
	const requirements = [
		...((assessment.installation_requirements ?? []) as JsonObject[]),
	];
	if (assessment.manufacturer_pair)
		requirements.push(readObject(assessment.manufacturer_pair));
	for (const value of (assessment.systems ?? []) as JsonObject[]) {
		const system = readObject(value),
			pair = readObject(system.assessment).manufacturer_pair;
		if (pair)
			requirements.push({
				...readObject(pair),
				unit_id: system.id!,
				unit_name: system.name!,
			});
	}
	const distinct = new Map(
		requirements.map((r) => [
			JSON.stringify([r.unit_id, r.group_id, r.conditions, r.documents]),
			r,
		]),
	);
	if (
		![...distinct.values()].some(
			(r) =>
				(Array.isArray(r.conditions) && r.conditions.length) ||
				(Array.isArray(r.documents) && r.documents.length),
		)
	)
		return null;
	return (
		<details className="lp-comparison">
			<summary>
				{__("Components and manufacturer conditions", "linker-tools")}
			</summary>
			{[...distinct.values()].map((r, index) => (
				<div key={index}>
					{typeof r.unit_name === "string" && <h4>{r.unit_name}</h4>}
					{typeof r.group_name === "string" && (
						<h4>
							{__("Coordination group", "linker-tools")} · {r.group_name}
						</h4>
					)}
					{((r.conditions ?? []) as Json[]).map((condition, i) => {
						const value =
							typeof condition === "string"
								? condition
								: readObject(condition)[locale.startsWith("de") ? "de" : "en"];
						return typeof value === "string" ? <p key={i}>{value}</p> : null;
					})}
					{((r.documents ?? []) as JsonObject[]).map((doc, i) => (
						<p key={i}>
							<a href={String(doc.url)} target="_blank" rel="noreferrer">
								{__("Source document", "linker-tools")}
							</a>
							{typeof doc.page === "number"
								? ` · ${sprintf(__("Page %d", "linker-tools"), doc.page)}`
								: ""}
						</p>
					))}
				</div>
			))}
		</details>
	);
}
