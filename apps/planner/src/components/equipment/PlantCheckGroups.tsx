import type { ReactNode } from "react";
import type { JsonObject } from "../../data/protocol.ts";
import { readObject } from "../../data/readProtocol.ts";
import { __ } from "../../i18n.ts";
import { equipmentStatus } from "./equipmentLabels.ts";

export function PlantCheckGroups({
	assessment,
	renderCheck,
}: {
	assessment: JsonObject;
	renderCheck: (check: JsonObject) => ReactNode;
}) {
	const checks = assessment.checks as JsonObject[],
		assigned = new Set<JsonObject>();
	const products = new Map(
		(assessment.selected_products as JsonObject[]).map((p) => [
			p.product_id,
			p,
		]),
	);
	const status = (items: JsonObject[]) =>
		items.some((c) => c.status === "violated")
			? "violated"
			: items.length && items.every((c) => c.status === "satisfied")
				? "satisfied"
				: "unresolved";
	const units = (assessment.systems as JsonObject[]).map((u) => {
		const items = checks.filter((c) =>
			String(c.id).startsWith(`unit:${u.id}:`),
		);
		items.forEach((c) => assigned.add(c));
		const product = products.get(readObject(u.selection).inverter_product_id);
		return {
			id: String(u.id),
			name: String(u.name),
			model: product ? `${product.brand} ${product.model}` : "",
			items,
		};
	});
	const groups = new Map<string, { name: string; items: JsonObject[] }>();
	for (const check of checks) {
		if (!String(check.id).startsWith("group:")) continue;
		const id = String(check.id).split(":")[1]!;
		if (!groups.has(id))
			groups.set(id, {
				name: typeof check.group_name === "string" ? check.group_name : "",
				items: [],
			});
		groups.get(id)!.items.push(check);
		assigned.add(check);
	}
	const project = checks.filter((c) => !assigned.has(c));
	return (
		<>
			{project.length > 0 && (
				<details className="lp-comparison" open>
					<summary>
						{__("Project requirements and joint checks", "linker-tools")} ·{" "}
						{equipmentStatus(status(project))}
					</summary>
					{project.map(renderCheck)}
				</details>
			)}
			{units.map((u) => (
				<details className="lp-comparison" key={u.id}>
					<summary>
						{u.name} · {u.model} · {equipmentStatus(status(u.items))}
					</summary>
					{u.items.map(renderCheck)}
				</details>
			))}
			{[...groups.entries()].map(([id, group]) => (
				<details className="lp-comparison" key={id}>
					<summary>
						{__("Coordination group", "linker-tools")} {group.name} ·{" "}
						{equipmentStatus(status(group.items))}
					</summary>
					{group.items.map(renderCheck)}
				</details>
			))}
		</>
	);
}
