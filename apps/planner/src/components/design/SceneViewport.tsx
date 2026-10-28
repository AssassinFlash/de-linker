import { Component, useEffect, useId, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { ArrayTransform } from "./SceneControls.tsx";
import { SceneCamera } from "./SceneCamera.tsx";
import { SCENE_FOV_DEG, sceneViewDirection } from "../../domain/sceneCamera.ts";
import {
	Box3,
	Color,
	DoubleSide,
	ExtrudeGeometry,
	Group,
	InstancedMesh,
	Matrix4,
	Path,
	Quaternion,
	Shape,
	ShapeGeometry,
	Vector3,
	Vector2,
	WebGPURenderer,
	Line,
	LineBasicMaterial,
	BufferGeometry,
} from "three/webgpu";
import type {
	GeometryDocument,
	PanelArray,
	PanelPose,
	RoofFace,
	Vec3,
} from "../../domain/geometry.ts";
import type { GeometryCommand } from "../../domain/geometryCommands.ts";
import {
	add,
	cross,
	dot,
	fromRender,
	scale,
	toRender,
	vectorFromRoof,
} from "../../domain/coordinates.ts";
import {
	centredRings,
	panelBatches,
	renderBoundsPoints,
	requireRenderCoordinates,
} from "../../domain/renderGeometry.ts";
import { __ } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";
import {
	releaseBackend,
	releaseUnownedRenderer,
} from "../../domain/renderLifetime.ts";

interface Palette {
	roof: string;
	module: string;
	selected: string;
	obstacle: string;
	keepout: string;
	background: string;
}
interface SceneProps {
	document: GeometryDocument;
	poses: readonly PanelPose[];
	selected: string | null;
	select: (id: string) => void;
	commit: (command: GeometryCommand) => boolean;
	disabled: boolean;
	routes?: readonly (readonly Vec3[])[];
	/** A validated row for this exact frozen document; null is not zero visibility. */
	directBeam?: ReadonlyMap<string, number | null> | undefined;
}
const vector = (point: Vec3) => new Vector3(...point);
const sceneLens = { fov: SCENE_FOV_DEG };
const roofRotation = (roof: RoofFace) =>
	new Quaternion().setFromRotationMatrix(
		new Matrix4().makeBasis(
			vector(toRender(roof.u_axis_enu)),
			vector(toRender(roof.v_axis_enu)),
			vector(toRender(cross(roof.u_axis_enu, roof.v_axis_enu))),
		),
	);

class SceneBoundary extends Component<
	{ children: ReactNode; failed: () => void },
	{ failed: boolean }
> {
	state = { failed: false };
	static getDerivedStateFromError() {
		return { failed: true };
	}
	componentDidCatch() {
		this.props.failed();
	}
	render() {
		return this.state.failed ? null : this.props.children;
	}
}

function RoofMesh({
	roof,
	reference,
	palette,
	select,
}: {
	roof: RoofFace;
	reference: Vec3;
	palette: Palette;
	select: (id: string) => void;
}) {
	const rings = useMemo(
		() => centredRings(roof.boundary_uv, roof.holes_uv),
		[roof],
	);
	const geometry = useMemo(() => {
		const shape = new Shape(rings.boundary.map(([u, v]) => new Vector2(u, v)));
		shape.holes = rings.holes.map(
			(ring) => new Path(ring.map(([u, v]) => new Vector2(u, v))),
		);
		return new ShapeGeometry(shape);
	}, [rings]);
	useEffect(() => () => geometry.dispose(), [geometry]);
	return (
		<mesh
			geometry={geometry}
			position={toRender(
				add(
					add(roof.origin_enu, scale(reference, -1)),
					vectorFromRoof(roof, [...rings.pivot, 0]),
				),
			)}
			quaternion={roofRotation(roof)}
			onClick={(event) => {
				event.stopPropagation();
				select(roof.id);
			}}
		>
			<meshStandardMaterial
				color={palette.roof}
				side={DoubleSide}
				roughness={0.9}
			/>
		</mesh>
	);
}

function PanelBatch({
	batch,
	array,
	palette,
	selected,
	select,
	directBeam,
}: {
	batch: ReturnType<typeof panelBatches>[number];
	array: PanelArray;
	palette: Palette;
	selected: string | null;
	select: (id: string) => void;
	directBeam?: ReadonlyMap<string, number | null> | undefined;
}) {
	const mesh = useRef<InstancedMesh>(null!);
	const { invalidate } = useThree();
	useEffect(() => {
		const instance = mesh.current;
		batch.poses.forEach((pose, index) => {
			const matrix = new Matrix4().makeBasis(
				vector(pose.u_axis_uvn),
				vector(pose.v_axis_uvn),
				vector(pose.normal_uvn),
			);
			matrix.scale(new Vector3(pose.width_m, pose.length_m, pose.thickness_m));
			matrix.setPosition(
				pose.centre_uvn[0] - batch.pivot[0],
				pose.centre_uvn[1] - batch.pivot[1],
				pose.centre_uvn[2] - batch.pivot[2],
			);
			requireRenderCoordinates(matrix.elements);
			instance.setMatrixAt(index, matrix);
			const visibility = directBeam?.get(pose.id);
			instance.setColorAt(
				index,
				directBeam && pose.included
					? visibility === null || visibility === undefined
						? new Color(palette.roof)
						: new Color(palette.module).lerp(
								new Color(palette.selected),
								visibility,
							)
					: new Color(
							pose.id === selected || selected === array.id
								? palette.selected
								: pose.included
									? palette.module
									: palette.roof,
						),
			);
		});
		instance.instanceMatrix.needsUpdate = true;
		if (instance.instanceColor) instance.instanceColor.needsUpdate = true;
		instance.computeBoundingBox();
		instance.computeBoundingSphere();
		invalidate();
	}, [batch, array.id, selected, palette, invalidate, directBeam]);
	return (
		<group
			position={[
				batch.pivot[0] - array.origin_uv[0],
				batch.pivot[1] - array.origin_uv[1],
				batch.pivot[2],
			]}
		>
			<instancedMesh
				ref={mesh}
				args={[undefined, undefined, batch.poses.length]}
				onClick={(event) => {
					event.stopPropagation();
					const pose = batch.poses[event.instanceId ?? -1];
					if (pose) select(pose.id);
				}}
			>
				<boxGeometry args={[1, 1, 1]} />
				<meshStandardMaterial metalness={0.2} roughness={0.34} />
			</instancedMesh>
		</group>
	);
}

function Panels({
	document,
	frame,
	poses,
	array,
	roof,
	reference,
	palette,
	selected,
	select,
	commit,
	disabled,
	directBeam,
}: {
	document: GeometryDocument;
	frame: string;
	poses: readonly PanelPose[];
	array: PanelArray;
	roof: RoofFace;
	reference: Vec3;
	palette: Palette;
	selected: string | null;
	select: (id: string) => void;
	commit: (command: GeometryCommand) => boolean;
	disabled: boolean;
	directBeam?: ReadonlyMap<string, number | null> | undefined;
}) {
	const group = useRef<Group>(null!);
	const start = useRef<{
		position: Vector3;
		array: PanelArray;
		roof: RoofFace;
		document: GeometryDocument;
		frame: string;
	} | null>(null);
	const { invalidate } = useThree();
	const batches = useMemo(() => panelBatches(poses), [poses]);
	const origin = toRender(
		add(
			add(roof.origin_enu, scale(reference, -1)),
			vectorFromRoof(roof, [...array.origin_uv, 0]),
		),
	);
	const active =
		selected === array.id || poses.some((pose) => pose.id === selected);
	return (
		<>
			<group ref={group} position={origin} quaternion={roofRotation(roof)}>
				{batches.map((batch) => (
					<PanelBatch
						key={batch.key}
						batch={batch}
						array={array}
						palette={palette}
						selected={selected}
						select={select}
						directBeam={directBeam}
					/>
				))}
			</group>
			{active && !disabled && (
				<ArrayTransform
					object={group}
					frame={frame}
					start={() => {
						start.current = {
							position: group.current.position.clone(),
							array,
							roof,
							document,
							frame,
						};
					}}
					cancel={() => {
						start.current = null;
						group.current?.position.set(...origin);
						invalidate();
					}}
					finish={() => {
						const before = start.current;
						start.current = null;
						if (!before) return;
						if (before.frame !== frame) {
							group.current.position.set(...origin);
							invalidate();
							return;
						}
						const delta = fromRender(
							group.current.position.clone().sub(before.position).toArray() as [
								number,
								number,
								number,
							],
						);
						const u = dot(delta, before.roof.u_axis_enu),
							v = dot(delta, before.roof.v_axis_enu);
						if (u !== 0 || v !== 0) {
							const accepted = commit({
								type: "group",
								before: before.document,
								edits: [
									{
										type: "put_array",
										before: before.array,
										value: {
											...before.array,
											origin_uv: [
												before.array.origin_uv[0] + u,
												before.array.origin_uv[1] + v,
											],
										},
									},
								],
							});
							if (!accepted) group.current.position.set(...origin);
						}
						invalidate();
					}}
				/>
			)}
		</>
	);
}

function SiteObjects({
	document: geometry,
	reference,
	palette,
	select,
}: {
	document: GeometryDocument;
	reference: Vec3;
	palette: Palette;
	select: (id: string) => void;
}) {
	const objects = useMemo(
		() =>
			[...geometry.obstacles, ...geometry.keepouts].map((object) => {
				const roof = geometry.roofs.find((roof) => roof.id === object.roof_id)!;
				const rings = centredRings(object.footprint_uv);
				const shape = new Shape(
					rings.boundary.map(([u, v]) => new Vector2(u, v)),
				);
				const obstacle = "height_m" in object;
				const geometryObject = obstacle
					? new ExtrudeGeometry(shape, {
							depth: 1,
							bevelEnabled: false,
							steps: 1,
						})
					: new ShapeGeometry(shape);
				const axis = obstacle
					? object.extrusion_axis_enu
					: cross(roof.u_axis_enu, roof.v_axis_enu);
				const matrix = new Matrix4().makeBasis(
					vector(toRender(roof.u_axis_enu)),
					vector(toRender(roof.v_axis_enu)),
					vector(toRender(obstacle ? scale(axis, object.height_m) : axis)),
				);
				matrix.setPosition(
					...toRender(
						add(
							add(roof.origin_enu, scale(reference, -1)),
							vectorFromRoof(roof, [...rings.pivot, 0]),
						),
					),
				);
				if (obstacle) requireRenderCoordinates([object.height_m]);
				return {
					id: object.id,
					geometry: geometryObject,
					matrix,
					color: obstacle ? palette.obstacle : palette.keepout,
					obstacle,
				};
			}),
		[geometry, reference, palette],
	);
	useEffect(
		() => () => objects.forEach((object) => object.geometry.dispose()),
		[objects],
	);
	return (
		<>
			{objects.map((object) => (
				<mesh
					key={object.id}
					geometry={object.geometry}
					matrix={object.matrix}
					matrixAutoUpdate={false}
					onClick={(event) => {
						event.stopPropagation();
						select(object.id);
					}}
				>
					<meshStandardMaterial
						color={object.color}
						transparent={!object.obstacle}
						opacity={object.obstacle ? 1 : 0.45}
						side={DoubleSide}
						polygonOffset
						polygonOffsetFactor={-1}
					/>
				</mesh>
			))}
		</>
	);
}

function RendererLifecycle({ fail }: { fail: () => void }) {
	const { gl } = useThree();
	useEffect(() => {
		const canvas = gl.domElement;
		const lost = (event: Event) => {
			event.preventDefault();
			fail();
		};
		canvas.addEventListener("webglcontextlost", lost);
		return () => canvas.removeEventListener("webglcontextlost", lost);
	}, [gl, fail]);
	return null;
}

function RouteLines({
	paths,
	reference,
	color,
}: {
	paths: readonly (readonly Vec3[])[];
	reference: Vec3;
	color: string;
}) {
	const lines = useMemo(
		() =>
			paths.map((path) => {
				const points = path.map((point) =>
					toRender(add(point, scale(reference, -1))),
				);
				requireRenderCoordinates(points.flat());
				return new Line(
					new BufferGeometry().setFromPoints(points.map(vector)),
					new LineBasicMaterial({ color, depthTest: false }),
				);
			}),
		[paths, reference, color],
	);
	useEffect(
		() => () => {
			for (const line of lines) {
				line.geometry.dispose();
				line.material.dispose();
			}
		},
		[lines],
	);
	return (
		<>
			{lines.map((line, i) => (
				<primitive key={i} object={line} dispose={null} />
			))}
		</>
	);
}

/** Loaded only when 3D is opened. Geometry persists independently of this GPU tree. */
export default function SceneViewport(props: SceneProps) {
	const compatibilityHelp = useId();
	const frame = useMemo(() => JSON.stringify(props.document), [props.document]);
	const host = useRef<HTMLDivElement>(null);
	const [palette, setPalette] = useState<Palette | null>(null),
		[failed, setFailed] = useState(false),
		[attempt, setAttempt] = useState(0);
	const [backend, setBackend] = useState("");
	const [fitRequest, setFitRequest] = useState(0);
	const [forceWebGL, setForceWebGL] = useState(false);
	const alive = useRef(true);
	const generation = useRef(0);
	useEffect(() => {
		alive.current = true;
		return () => {
			alive.current = false;
			generation.current++;
		};
	}, []);
	useEffect(() => {
		if (!host.current) return;
		const style = getComputedStyle(host.current),
			token = (name: string) => style.getPropertyValue(name).trim();
		setPalette({
			roof: token("--proto-neutral-300"),
			module: token("--proto-teal-900"),
			selected: token("--proto-teal-400"),
			obstacle: token("--proto-neutral-600"),
			keepout: token("--proto-teal-700"),
			background: token("--proto-neutral-100"),
		});
	}, []);
	const reference =
		props.document.roofs[0]?.origin_enu ?? props.routes?.[0]?.[0];
	const bounds = useMemo(() => {
		if (!reference) return null;
		try {
			const points = [
				...(props.document.roofs.length
					? renderBoundsPoints(props.document, props.poses, reference)
					: []),
				...(props.routes ?? []).flatMap((route) =>
					route.map((point) => toRender(add(point, scale(reference, -1)))),
				),
			].map(vector);
			const box = new Box3().setFromPoints(points),
				centre = box.getCenter(new Vector3()),
				size = box.getSize(new Vector3()).length();
			if (!Number.isFinite(size) || size <= 0) return null;
			return {
				centre,
				size,
				direction: props.document.roofs.length
					? sceneViewDirection(props.document, props.selected, props.poses)
					: ([0, Math.SQRT1_2, Math.SQRT1_2] as Vec3),
			};
		} catch {
			return null;
		}
	}, [props.document, props.poses, props.selected, props.routes, reference]);
	return (
		<div className="lp-scene-view" ref={host}>
			{failed ? (
				<Notice error>
					<p>
						{__(
							"3D rendering is unavailable. The design remains available in the plan view and numeric properties.",
							"linker-tools",
						)}
					</p>
					<button
						type="button"
						className="lp-button lp-button-secondary"
						onClick={() => {
							generation.current++;
							setBackend("");
							setFailed(false);
							setAttempt((value) => value + 1);
						}}
					>
						{__("Retry 3D", "linker-tools")}
					</button>
				</Notice>
			) : !bounds || !reference ? (
				<Notice error>
					{__(
						"This geometry cannot be displayed in 3D at the supported numerical precision. Numeric properties remain available.",
						"linker-tools",
					)}
				</Notice>
			) : (
				palette && (
					<SceneBoundary
						key={attempt + String(forceWebGL)}
						failed={() => setFailed(true)}
					>
						<Canvas
							role="img"
							aria-label={__("Roof design", "linker-tools")}
							frameloop="demand"
							dpr={[1, 2]}
							camera={sceneLens}
							gl={async (defaults) => {
								const identity = ++generation.current;
								const renderer = new WebGPURenderer({
									canvas: defaults.canvas as HTMLCanvasElement,
									antialias: true,
									forceWebGL,
								});
								let initialBackend: typeof renderer.backend | null =
									renderer.backend;
								renderer.onDeviceLost = () => {
									if (alive.current && identity === generation.current)
										setFailed(true);
								};
								try {
									await renderer.init();
									if (initialBackend !== renderer.backend) {
										await releaseBackend(initialBackend);
										initialBackend = null;
									}
									if (!alive.current || identity !== generation.current) {
										throw new Error("scene_unmounted");
									}
								} catch (error) {
									// A rejected init never hands this instance to R3F for disposal.
									await releaseUnownedRenderer(renderer, initialBackend);
									if (alive.current && identity === generation.current)
										setFailed(true);
									throw error;
								}
								const backend = renderer.backend as unknown as {
									isWebGPUBackend?: boolean;
									isWebGLBackend?: boolean;
								};
								setBackend(
									backend.isWebGPUBackend
										? "WebGPU"
										: backend.isWebGLBackend
											? "WebGL 2"
											: "",
								);
								return renderer;
							}}
							fallback={<p>{__("Roof design", "linker-tools")}</p>}
						>
							<color attach="background" args={[palette.background]} />
							<ambientLight intensity={1.4} />
							<directionalLight position={[10, 30, 20]} intensity={2} />
							{props.document.roofs.map((roof) => (
								<RoofMesh
									key={roof.id}
									roof={roof}
									reference={reference}
									palette={palette}
									select={props.select}
								/>
							))}
							{props.document.arrays.map((array) => (
								<Panels
									key={array.id}
									document={props.document}
									frame={frame}
									array={array}
									roof={props.document.roofs.find(
										(roof) => roof.id === array.roof_id,
									)!}
									reference={reference}
									poses={props.poses.filter(
										(pose) => pose.array_id === array.id,
									)}
									palette={palette}
									selected={props.selected}
									select={props.select}
									commit={props.commit}
									disabled={props.disabled}
									directBeam={props.directBeam}
								/>
							))}
							<SiteObjects
								document={props.document}
								reference={reference}
								palette={palette}
								select={props.select}
							/>
							<SceneCamera extent={bounds} request={fitRequest} />
							{props.routes && (
								<RouteLines
									paths={props.routes}
									reference={reference}
									color={palette.module}
								/>
							)}
							<RendererLifecycle fail={() => setFailed(true)} />
						</Canvas>
					</SceneBoundary>
				)
			)}
			<div className="lp-canvas-caption">
				<button
					type="button"
					className="lp-tool-button"
					disabled={failed || !bounds}
					onClick={() => {
						setFitRequest((value) => value + 1);
					}}
				>
					{__("Fit 3D view", "linker-tools")}
				</button>
				<span data-renderer={backend || undefined}>
					{backend ? "3D" : __("Preparing 3D…", "linker-tools")}
				</span>
			</div>
			<details className="lp-comparison">
				<summary>{__("View options", "linker-tools")}</summary>
				<label className="lp-geometry-check">
					<input
						type="checkbox"
						aria-describedby={compatibilityHelp}
						checked={forceWebGL}
						onChange={(event) => {
							generation.current++;
							setBackend("");
							setForceWebGL(event.currentTarget.checked);
							setFailed(false);
						}}
					/>
					<span>{__("Compatibility mode", "linker-tools")}</span>
				</label>
				<p id={compatibilityHelp} className="lp-profile-help">
					{__(
						"Use this if the 3D view does not display correctly.",
						"linker-tools",
					)}
				</p>
			</details>
			{!props.disabled && (
				<p className="lp-profile-help">
					{__(
						"Dragging the selected array's handles changes its position in the roof plane. Camera controls change only the view. Lighting is for display; it does not calculate shading losses.",
						"linker-tools",
					)}
				</p>
			)}
		</div>
	);
}
