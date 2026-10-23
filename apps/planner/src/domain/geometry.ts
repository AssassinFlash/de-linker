/** Shared metric design data. No Three objects, camera state or GPU resources. */
export type Vec2 = readonly [number, number];
export type Vec3 = readonly [number, number, number];

export interface Source {
	id: string;
	kind:
		| "user_measurement"
		| "user_drawing"
		| "licensed_dataset"
		| "synthetic_fixture";
	note: string;
	rights_note: string;
	reference_url: string | null;
	reference_sha256: string | null;
	acquired_at_utc: string | null;
	spatial_precision_m: number | null;
	calibration_note: string;
	rights_basis: "user_attestation" | "referenced_licence" | "synthetic";
	permissions: {
		derive: "permitted" | "unknown" | "prohibited";
		retain: "permitted" | "unknown" | "prohibited";
		export: "permitted" | "unknown" | "prohibited";
	};
}

export interface RoofFace {
	id: string;
	name: string;
	source_id: string;
	origin_enu: Vec3;
	u_axis_enu: Vec3;
	v_axis_enu: Vec3;
	/** Open rings, metres in the face's orthonormal U/V basis. */
	boundary_uv: readonly Vec2[];
	holes_uv: readonly (readonly Vec2[])[];
}

export interface ModuleSpec {
	id: string;
	model: string;
	width_m: number;
	length_m: number;
	thickness_m: number;
	stc_power_w: number;
	source: {
		kind: "datasheet" | "user_declared";
		note: string;
		document_sha256: string | null;
		url: string | null;
		page: number | null;
	};
}

export interface PanelArray {
	id: string;
	name: string;
	source_id: string;
	roof_id: string;
	module_spec_id: string;
	/** Lower-left row anchor on the roof face, not a panel centre. */
	origin_uv: Vec2;
	rotation_deg: number;
	/** Added tilt about the row U axis, relative to this roof face. */
	mount_tilt_deg: number;
	lower_edge_clearance_m: number;
	rows: number;
	columns: number;
	column_gap_m: number;
	/** Clear projected gap between successive rows on the roof plane. */
	row_gap_m: number;
	excluded_slots: readonly string[];
	mounting_note: string;
}

export interface Obstacle {
	id: string;
	name: string;
	source_id: string;
	roof_id: string;
	footprint_uv: readonly Vec2[];
	extrusion_axis_enu: Vec3;
	height_m: number;
}

export interface Keepout {
	id: string;
	name: string;
	source_id: string;
	roof_id: string;
	footprint_uv: readonly Vec2[];
	reason: string;
}

export interface RoofLayoutRules {
	roof_id: string;
	source_id: string;
	edge_clearance_m: number | null;
	obstacle_clearance_m: number | null;
	source_note: string;
}

export interface GeometryDocument {
	schema_version: 1;
	coordinate_system: {
		kind: "local_enu";
		unit: "m";
		height_reference: "relative_to_project_origin";
		north_reference: "true_north" | "user_declared" | "unreferenced";
		north_source_id: string | null;
		anchor: {
			latitude_deg: number;
			longitude_deg: number;
			source_id: string;
			datum: "EPSG:4326";
		} | null;
	};
	sources: readonly Source[];
	roofs: readonly RoofFace[];
	module_specs: readonly ModuleSpec[];
	arrays: readonly PanelArray[];
	obstacles: readonly Obstacle[];
	keepouts: readonly Keepout[];
	layout_rules: readonly RoofLayoutRules[];
}

export interface PanelPose {
	id: string;
	array_id: string;
	roof_id: string;
	row: number;
	column: number;
	included: boolean;
	centre_uvn: Vec3;
	u_axis_uvn: Vec3;
	v_axis_uvn: Vec3;
	normal_uvn: Vec3;
	footprint_uv: readonly Vec2[];
	/** Derived absolute display point; use local frame for fit/rebased rendering. */
	centre_enu: Vec3;
	u_axis_enu: Vec3;
	v_axis_enu: Vec3;
	normal_enu: Vec3;
	width_m: number;
	length_m: number;
	thickness_m: number;
	stc_power_w: number;
}
