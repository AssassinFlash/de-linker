/** One completed edit becomes one immutable project-history step. */
import type {
	GeometryDocument,
	RoofFace,
	Source,
	ModuleSpec,
	PanelArray,
	Obstacle,
	Keepout,
	RoofLayoutRules,
	Vec2,
} from "./geometry.ts";
import policy from "../contracts/geometry-policy.json" with { type: "json" };
import { readGeometry } from "./validateGeometry.ts";
import { sameJson } from "./draft.ts";

type Put<T> = { before: T | null; value: T };
export type GeometryEdit =
	| {
			type: "set_coordinate_system";
			before: GeometryDocument["coordinate_system"];
			value: GeometryDocument["coordinate_system"];
	  }
	| ({ type: "put_roof" } & Put<RoofFace>)
	| ({ type: "put_source" } & Put<Source>)
	| ({ type: "put_module" } & Put<ModuleSpec>)
	| ({ type: "put_array" } & Put<PanelArray>)
	| ({ type: "put_obstacle" } & Put<Obstacle>)
	| ({ type: "put_keepout" } & Put<Keepout>)
	| {
			type: "set_rules";
			before: RoofLayoutRules | null;
			value: RoofLayoutRules;
	  }
	| { type: "toggle_panel"; array_id: string; row: number; column: number }
	| { type: "move_arrays"; ids: readonly string[]; delta_uv: Vec2 }
	| { type: "rotate_arrays"; ids: readonly string[]; delta_deg: number }
	| { type: "delete_roof"; id: string; expected_dependents: readonly string[] }
	| { type: "delete_object"; id: string };
export type GeometryCommand =
	| GeometryEdit
	| {
			type: "group";
			/** A gesture depends on the whole frame, not only its edited object. */
			before?: GeometryDocument;
			edits: readonly GeometryEdit[];
	  };

export class GeometryCommandError extends Error {
	constructor(code: string) {
		super(code);
		this.name = "GeometryCommandError";
	}
}

function put<T extends { id: string }>(
	items: readonly T[],
	before: T | null,
	value: T,
): readonly T[] {
	const current = items.find((item) => item.id === value.id);
	if (
		before === null
			? current !== undefined
			: !current || before.id !== value.id || !sameJson(before, current)
	)
		throw new GeometryCommandError("geometry_object_changed");
	return current
		? items.map((item) => (item.id === value.id ? value : item))
		: [...items, value];
}

export function roofDependents(
	document: GeometryDocument,
	id: string,
): readonly string[] {
	return [...document.arrays, ...document.obstacles, ...document.keepouts]
		.filter((object) => object.roof_id === id)
		.map((object) => object.id)
		.sort();
}

export function applyGeometryCommand(
	document: GeometryDocument,
	command: GeometryCommand,
): GeometryDocument {
	if (
		command.type === "group" &&
		command.before !== undefined &&
		!sameJson(command.before, document)
	)
		throw new GeometryCommandError("geometry_frame_changed");
	const edits = command.type === "group" ? command.edits : [command];
	// Local editing resource policy, not a physical/site restriction.
	if (edits.length > 256)
		throw new GeometryCommandError("geometry_command_limit");
	let next = document;
	for (const edit of edits) next = applyEdit(next, edit);
	return readGeometry(next, policy);
}

function applyEdit(
	document: GeometryDocument,
	edit: GeometryEdit,
): GeometryDocument {
	switch (edit.type) {
		case "set_coordinate_system":
			if (!sameJson(document.coordinate_system, edit.before))
				throw new GeometryCommandError("geometry_object_changed");
			return { ...document, coordinate_system: edit.value };
		case "put_roof":
			return {
				...document,
				roofs: put(document.roofs, edit.before, edit.value),
			};
		case "put_source":
			return {
				...document,
				sources: put(document.sources, edit.before, edit.value),
			};
		case "put_module":
			return {
				...document,
				module_specs: put(document.module_specs, edit.before, edit.value),
			};
		case "put_array":
			return {
				...document,
				arrays: put(document.arrays, edit.before, edit.value),
			};
		case "put_obstacle":
			return {
				...document,
				obstacles: put(document.obstacles, edit.before, edit.value),
			};
		case "put_keepout":
			return {
				...document,
				keepouts: put(document.keepouts, edit.before, edit.value),
			};
		case "set_rules": {
			const current =
				document.layout_rules.find(
					(rule) => rule.roof_id === edit.value.roof_id,
				) ?? null;
			if (!sameJson(current, edit.before))
				throw new GeometryCommandError("geometry_object_changed");
			return {
				...document,
				layout_rules: [
					...document.layout_rules.filter(
						(rule) => rule.roof_id !== edit.value.roof_id,
					),
					edit.value,
				],
			};
		}
		case "toggle_panel": {
			const array = document.arrays.find((item) => item.id === edit.array_id);
			if (
				!array ||
				!Number.isSafeInteger(edit.row) ||
				!Number.isSafeInteger(edit.column) ||
				edit.row < 0 ||
				edit.column < 0 ||
				edit.row >= array.rows ||
				edit.column >= array.columns
			)
				throw new GeometryCommandError("geometry_slot_missing");
			const slot = `${edit.row}:${edit.column}`;
			const excluded = array.excluded_slots.includes(slot)
				? array.excluded_slots.filter((key) => key !== slot)
				: [...array.excluded_slots, slot].sort();
			return {
				...document,
				arrays: put(document.arrays, array, {
					...array,
					excluded_slots: excluded,
				}),
			};
		}
		case "move_arrays":
		case "rotate_arrays": {
			if (
				new Set(edit.ids).size !== edit.ids.length ||
				edit.ids.some((id) => !document.arrays.some((array) => array.id === id))
			)
				throw new GeometryCommandError("geometry_array_missing");
			return {
				...document,
				arrays: document.arrays.map((array) =>
					!edit.ids.includes(array.id)
						? array
						: edit.type === "move_arrays"
							? {
									...array,
									origin_uv: [
										array.origin_uv[0] + edit.delta_uv[0],
										array.origin_uv[1] + edit.delta_uv[1],
									],
								}
							: { ...array, rotation_deg: array.rotation_deg + edit.delta_deg },
				),
			};
		}
		case "delete_roof": {
			if (
				!document.roofs.some((roof) => roof.id === edit.id) ||
				!sameJson(
					roofDependents(document, edit.id),
					[...edit.expected_dependents].sort(),
				)
			)
				throw new GeometryCommandError("geometry_dependents_changed");
			return {
				...document,
				roofs: document.roofs.filter((roof) => roof.id !== edit.id),
				arrays: document.arrays.filter((item) => item.roof_id !== edit.id),
				obstacles: document.obstacles.filter(
					(item) => item.roof_id !== edit.id,
				),
				keepouts: document.keepouts.filter((item) => item.roof_id !== edit.id),
				layout_rules: document.layout_rules.filter(
					(item) => item.roof_id !== edit.id,
				),
			};
		}
		case "delete_object": {
			if (document.roofs.some((roof) => roof.id === edit.id))
				throw new GeometryCommandError("geometry_roof_requires_dependents");
			if (
				![
					...document.sources,
					...document.module_specs,
					...document.arrays,
					...document.obstacles,
					...document.keepouts,
				].some((item) => item.id === edit.id)
			)
				throw new GeometryCommandError("geometry_object_missing");
			return {
				...document,
				sources: document.sources.filter((item) => item.id !== edit.id),
				module_specs: document.module_specs.filter(
					(item) => item.id !== edit.id,
				),
				arrays: document.arrays.filter((item) => item.id !== edit.id),
				obstacles: document.obstacles.filter((item) => item.id !== edit.id),
				keepouts: document.keepouts.filter((item) => item.id !== edit.id),
			};
		}
	}
}

export function emptyGeometry(): GeometryDocument {
	return {
		schema_version: 1,
		coordinate_system: {
			kind: "local_enu",
			unit: "m",
			height_reference: "relative_to_project_origin",
			north_reference: "unreferenced",
			north_source_id: null,
			anchor: null,
		},
		sources: [],
		roofs: [],
		module_specs: [],
		arrays: [],
		obstacles: [],
		keepouts: [],
		layout_rules: [],
	};
}
