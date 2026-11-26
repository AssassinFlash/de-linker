import { validate2020 } from "../data/schemaValidator.ts";
import schema from "../contracts/plant-search-plan.schema.json" with { type: "json" };
import { ApiError } from "../data/protocol.ts";
import type { JsonObject } from "../data/protocol.ts";
import { sameJson } from "./draft.ts";
import {
	equipmentDraft,
	changeEquipment,
	checkRetainedEquipment,
	comparisonModels,
} from "./equipment.ts";
import { compileEquipmentRequirements } from "./equipmentRequirements.ts";
import {
	plantInputs,
	compilePlant,
	plantGroupDraft,
	readEquipmentPlant,
	readPlantDraft,
} from "./equipmentPlant.ts";
import type {
	EquipmentPlant,
	PlantDraft,
	PlantGroupDraft,
} from "./equipmentPlant.ts";
import type { EquipmentProduct } from "../data/equipmentProducts.ts";

export interface PlantSearchPlan extends JsonObject {
	schema_version: 1;
	requirements: JsonObject;
	units: (JsonObject & {
		id: string;
		name: string;
		requirements: JsonObject;
	})[];
	parallel_groups: PlantGroupDraft[];
}
const validate = validate2020<PlantSearchPlan>(schema);

export function readPlantSearch(value: unknown): PlantSearchPlan {
	if (!validate(value))
		throw new ApiError(422, "equipment_requirements_incomplete");
	const ids = new Set(value.units.map((u) => u.id)),
		used = new Set<string>();
	if (
		ids.size !== value.units.length ||
		new Set(value.parallel_groups.map((g) => g.id)).size !==
			value.parallel_groups.length
	)
		throw new ApiError(422, "equipment_plant_incomplete");
	for (const unit of value.units) {
		if (
			unit.requirements.grid_phase !== value.requirements.grid_phase ||
			unit.requirements.operating_mode !== value.requirements.operating_mode
		)
			throw new ApiError(422, "equipment_plant_incomplete");
	}
	for (const group of value.parallel_groups) {
		if (
			new Set(group.unit_ids).size !== group.unit_ids.length ||
			group.unit_ids.some((id) => !ids.has(id) || used.has(id))
		)
			throw new ApiError(422, "equipment_plant_incomplete");
		for (const id of group.unit_ids) used.add(id);
	}
	return value;
}

export function compilePlantSearch(draft: PlantDraft): PlantSearchPlan {
	const requirements = compileEquipmentRequirements(draft.requirements);
	return readPlantSearch({
		schema_version: 1,
		requirements,
		units: draft.units.map((unit) => ({
			id: unit.id,
			name: unit.name,
			requirements: compileEquipmentRequirements({
				...equipmentDraft(unit.inputs),
				grid_phase: requirements.grid_phase ?? null,
				operating_mode: requirements.operating_mode ?? null,
			}),
		})),
		parallel_groups: draft.parallel_groups.map(
			({ controller_use, comparison_controller_product_id, ...group }) => ({
				...group,
				controller_product_id:
					controller_use === "retain" ||
					comparison_controller_product_id === undefined
						? group.controller_product_id
						: comparison_controller_product_id,
			}),
		),
	});
}

export function matchesPlantSearch(
	plan: PlantSearchPlan,
	plant: EquipmentPlant,
): boolean {
	return (
		sameJson(plan.requirements, plant.requirements) &&
		plan.units.length === plant.units.length &&
		plan.units.every((request, i) => {
			const unit = plant.units[i]!;
			return (
				request.id === unit.id &&
				request.name === unit.name &&
				sameJson(
					request.requirements,
					compileEquipmentRequirements({
						...unit.selection,
						...(Object.hasOwn(request.requirements, "application")
							? { application: request.requirements.application! }
							: {}),
					}),
				)
			);
		}) &&
		plan.parallel_groups.length === plant.parallel_groups.length &&
		plan.parallel_groups.every((request, i) => {
			const group = plant.parallel_groups[i]!;
			return (
				request.id === group.id &&
				sameJson(request.unit_ids, group.unit_ids) &&
				request.control_network === group.control_network &&
				(request.controller_product_id === null ||
					request.controller_product_id === group.controller_product_id)
			);
		})
	);
}

export function adoptPlantCandidate(
	inputs: JsonObject,
	value: EquipmentPlant,
	products: readonly EquipmentProduct[],
	choice: JsonObject,
	searched: JsonObject = inputs,
): JsonObject {
	const plant = readEquipmentPlant(value);
	const authored = readPlantDraft(inputs);
	const searchedDraft =
		searched === inputs ? authored : readPlantDraft(searched);
	// The frozen whole-plant capacity can be derived from the active PV arrays.
	const frozenPlan =
		searched.equipment_plant_requirements === undefined
			? null
			: readPlantSearch(searched.equipment_plant_requirements);
	const draft = {
		...authored,
		requirements: {
			...authored.requirements,
			...(frozenPlan === null
				? {}
				: { pv_dc_kw: frozenPlan.requirements.pv_dc_kw }),
			...(inputs.backup_demand !== undefined
				? { operating_mode: "backup" }
				: {}),
			...(plant.requirements.application === null &&
			authored.requirements.application === undefined
				? { application: null }
				: {}),
		},
	};
	if (!matchesPlantSearch(compilePlantSearch(draft), plant))
		throw new ApiError(409, "equipment_selection_changed");
	const revisions = [
		...plant.units.flatMap((u) =>
			Object.entries(u.selection.product_revisions),
		),
		...plant.parallel_groups
			.filter((g) => g.controller_product_id !== null)
			.map(
				(g) =>
					[String(g.controller_product_id), g.controller_revision] as const,
			),
	];
	if (
		revisions.some(
			([id, revision]) =>
				!products.some(
					(p) => String(p.id) === id && p.product_revision === revision,
				),
		)
	)
		throw new ApiError(409, "product_evidence_changed");
	const updated: PlantDraft = {
		...draft,
		units: plant.units.map((unit, i) => {
			const previous = equipmentDraft(draft.units[i]!.inputs);
			checkRetainedEquipment(previous, unit.selection);
			return {
				id: unit.id,
				name: unit.name,
				inputs: changeEquipment(draft.units[i]!.inputs, {
					...unit.selection,
					comparison_models: comparisonModels(
						equipmentDraft(searchedDraft.units[i]!.inputs),
					),
					...(previous.equipment_use === undefined
						? {}
						: { equipment_use: previous.equipment_use }),
				}),
			};
		}),
		parallel_groups: plant.parallel_groups.map((group, i) => {
			const previous = draft.parallel_groups[i]!;
			if (
				previous.controller_use === "retain" &&
				previous.controller_product_id !== group.controller_product_id
			)
				throw new ApiError(409, "retained_equipment_changed");
			return {
				...plantGroupDraft(group),
				comparison_controller_product_id:
					searchedDraft.parallel_groups[i]!.comparison_controller_product_id ===
					undefined
						? searchedDraft.parallel_groups[i]!.controller_product_id
						: searchedDraft.parallel_groups[i]!
								.comparison_controller_product_id,
				...(previous.controller_use === undefined
					? {}
					: { controller_use: previous.controller_use }),
			};
		}),
	};
	const prepared = compilePlant(updated, products);
	return {
		...plantInputs(inputs, updated),
		equipment_plant: prepared,
		...(sameJson(prepared, plant) ? { equipment_candidate: choice } : {}),
	};
}
