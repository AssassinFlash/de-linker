import { useEffect, useMemo, useRef, useState } from "react";
import type { PointerEvent } from "react";
import type {
	GeometryDocument,
	PanelArray,
	PanelPose,
	RoofFace,
	Vec2,
} from "../../domain/geometry.ts";
import type { GeometryCommand } from "../../domain/geometryCommands.ts";
import { dot } from "../../domain/coordinates.ts";
import { requireUvResolution } from "../../domain/geometryNumerics.ts";
import { __, sprintf } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";

interface View {
	x: number;
	y: number;
	width: number;
	height: number;
}
interface Gesture {
	document: GeometryDocument;
	pointer: number;
	start: Vec2;
	client: Vec2;
	array: PanelArray | null;
	view: View;
}
const points = (ring: readonly Vec2[]) =>
	ring.map(([u, v]) => `${u},${-v}`).join(" ");
const ringPath = (ring: readonly Vec2[]) =>
	"M" + ring.map(([u, v]) => `${u},${-v}`).join("L") + "Z";

export function PlanViewport({
	document: geometry,
	roof,
	poses,
	selected,
	select,
	commit,
	disabled,
}: {
	document: GeometryDocument;
	roof: RoofFace;
	poses: readonly PanelPose[];
	selected: string | null;
	select: (id: string) => void;
	commit: (command: GeometryCommand) => boolean;
	disabled: boolean;
}) {
	const svg = useRef<SVGSVGElement>(null),
		gesture = useRef<Gesture | null>(null);
	const [tool, setTool] = useState<"select" | "pan">("select"),
		[view, setView] = useState<View | null>(null),
		[preview, setPreview] = useState<{ array: string; delta: Vec2 } | null>(
			null,
		);
	function abort() {
		const active = gesture.current;
		gesture.current = null;
		setPreview(null);
		if (active && svg.current?.hasPointerCapture(active.pointer))
			svg.current.releasePointerCapture(active.pointer);
	}
	useEffect(() => {
		abort();
	}, [geometry, disabled, tool]);
	useEffect(() => {
		const escape = (event: KeyboardEvent) => {
			if (event.key === "Escape") abort();
		};
		window.addEventListener("keydown", escape);
		window.addEventListener("blur", abort);
		return () => {
			window.removeEventListener("keydown", escape);
			window.removeEventListener("blur", abort);
			const active = gesture.current;
			gesture.current = null;
			if (active && svg.current?.hasPointerCapture(active.pointer))
				svg.current.releasePointerCapture(active.pointer);
		};
	}, []);
	const roofPoses = useMemo(
		() => poses.filter((pose) => pose.roof_id === roof.id),
		[poses, roof.id],
	);
	const arrays = geometry.arrays.filter((array) => array.roof_id === roof.id);
	const obstacles = geometry.obstacles
		.filter((object) => object.roof_id === roof.id)
		.map((object) => {
			const delta: Vec2 = [
				dot(object.extrusion_axis_enu, roof.u_axis_enu) * object.height_m,
				dot(object.extrusion_axis_enu, roof.v_axis_enu) * object.height_m,
			];
			return {
				...object,
				top: object.footprint_uv.map(
					([u, v]) => [u + delta[0], v + delta[1]] as const,
				),
			};
		});
	const keepouts = geometry.keepouts.filter(
		(object) => object.roof_id === roof.id,
	);
	const all = [
		...roof.boundary_uv,
		...roof.holes_uv.flat(),
		...roofPoses.flatMap((pose) => pose.footprint_uv),
		...obstacles.flatMap((object) => [...object.footprint_uv, ...object.top]),
		...keepouts.flatMap((object) => object.footprint_uv),
	];
	let fit: View;
	try {
		requireUvResolution(all.flat());
		const us = all.map((p) => p[0]),
			vs = all.map((p) => p[1]);
		const minU = Math.min(...us),
			maxU = Math.max(...us),
			minV = Math.min(...vs),
			maxV = Math.max(...vs);
		const span = Math.max(maxU - minU, maxV - minV);
		if (!Number.isFinite(span) || span <= 0) throw new Error("invalid_view");
		// Display margin only, independent of all engineering clearances.
		const padding = span * 0.08;
		fit = {
			x: minU - padding,
			y: -maxV - padding,
			width: maxU - minU + 2 * padding,
			height: maxV - minV + 2 * padding,
		};
	} catch {
		return (
			<Notice error>
				{__(
					"This coordinate range cannot be displayed at the supported numerical precision. The source geometry remains in the open project draft and its numeric properties remain editable.",
					"linker-tools",
				)}
			</Notice>
		);
	}
	const current = view ?? fit;
	function at(event: PointerEvent<SVGSVGElement>): Vec2 | null {
		const matrix = svg.current?.getScreenCTM();
		if (!matrix) return null;
		const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(
			matrix.inverse(),
		);
		return [point.x, -point.y];
	}
	function down(event: PointerEvent<SVGSVGElement>) {
		if (disabled || event.button !== 0) return;
		const point = at(event);
		if (!point) return;
		const target = (event.target as Element).closest<SVGElement>(
			"[data-object]",
		);
		const id = target?.dataset.object;
		if (id && tool === "select") select(id);
		const array =
			arrays.find((array) => array.id === target?.dataset.array) ?? null;
		if (tool === "select" && !array) return;
		gesture.current = {
			document: geometry,
			pointer: event.pointerId,
			start: point,
			client: [event.clientX, event.clientY],
			array: tool === "select" ? array : null,
			view: current,
		};
		event.currentTarget.setPointerCapture(event.pointerId);
	}
	function move(event: PointerEvent<SVGSVGElement>) {
		const active = gesture.current;
		if (!active || active.pointer !== event.pointerId) return;
		const point = at(event);
		if (!point) return;
		if (active.array)
			setPreview({
				array: active.array.id,
				delta: [point[0] - active.start[0], point[1] - active.start[1]],
			});
		else {
			// Convert CSS displacement with the original matrix scale, so view updates do not feed back into the pan.
			const matrix = svg.current?.getScreenCTM();
			if (!matrix) return;
			setView({
				...active.view,
				x: active.view.x - (event.clientX - active.client[0]) / matrix.a,
				y: active.view.y - (event.clientY - active.client[1]) / matrix.d,
			});
		}
	}
	function finish(event: PointerEvent<SVGSVGElement>, cancelled: boolean) {
		const active = gesture.current;
		if (!active || active.pointer !== event.pointerId) return;
		gesture.current = null;
		const point = at(event);
		// Three CSS pixels distinguish a click from a drag. This is interaction policy, not a metric tolerance.
		if (
			!cancelled &&
			!disabled &&
			active.array &&
			point &&
			Math.hypot(
				event.clientX - active.client[0],
				event.clientY - active.client[1],
			) >= 3
		) {
			commit({
				type: "group",
				before: active.document,
				edits: [
					{
						type: "put_array",
						before: active.array,
						value: {
							...active.array,
							origin_uv: [
								active.array.origin_uv[0] + point[0] - active.start[0],
								active.array.origin_uv[1] + point[1] - active.start[1],
							],
						},
					},
				],
			});
		}
		setPreview(null);
		if (event.currentTarget.hasPointerCapture(event.pointerId))
			event.currentTarget.releasePointerCapture(event.pointerId);
	}
	function zoom(factor: number) {
		abort();
		setView({
			x: current.x + (current.width * (1 - factor)) / 2,
			y: current.y + (current.height * (1 - factor)) / 2,
			width: current.width * factor,
			height: current.height * factor,
		});
	}
	return (
		<div className="lp-plan-view">
			<div
				className="lp-canvas-tools"
				role="group"
				aria-label={__("Plan view controls", "linker-tools")}
			>
				<button
					type="button"
					className="lp-tool-button"
					aria-pressed={tool === "select"}
					onClick={() => setTool("select")}
				>
					{__("Select / move array", "linker-tools")}
				</button>
				<button
					type="button"
					className="lp-tool-button"
					aria-pressed={tool === "pan"}
					onClick={() => setTool("pan")}
				>
					{__("Pan view", "linker-tools")}
				</button>
				<button
					type="button"
					className="lp-tool-button"
					onClick={() => zoom(0.8)}
					aria-label={__("Zoom in", "linker-tools")}
				>
					+
				</button>
				<button
					type="button"
					className="lp-tool-button"
					onClick={() => zoom(1.25)}
					aria-label={__("Zoom out", "linker-tools")}
				>
					−
				</button>
				<button
					type="button"
					className="lp-tool-button"
					onClick={() => {
						abort();
						setView(null);
					}}
				>
					{__("Fit view", "linker-tools")}
				</button>
			</div>
			<svg
				ref={svg}
				className="lp-plan-svg"
				viewBox={`${current.x} ${current.y} ${current.width} ${current.height}`}
				role="img"
				aria-label={sprintf(
					__(
						"Roof plane: %s. U increases to the right; V increases upward.",
						"linker-tools",
					),
					roof.name,
				)}
				onPointerDown={down}
				onPointerMove={move}
				onPointerUp={(event) => finish(event, false)}
				onPointerCancel={(event) => finish(event, true)}
				onLostPointerCapture={() => {
					gesture.current = null;
					setPreview(null);
				}}
			>
				<path
					d={[ringPath(roof.boundary_uv), ...roof.holes_uv.map(ringPath)].join(
						" ",
					)}
					fillRule="evenodd"
					className="lp-roof-shape"
					data-object={roof.id}
					data-selected={selected === roof.id || undefined}
				/>
				{arrays.map((array) => (
					<g
						key={array.id}
						transform={
							preview?.array === array.id
								? `translate(${preview.delta[0]} ${-preview.delta[1]})`
								: undefined
						}
						data-array={array.id}
					>
						{roofPoses
							.filter((pose) => pose.array_id === array.id)
							.map((pose) => (
								<polygon
									key={pose.id}
									points={points(pose.footprint_uv)}
									className="lp-panel-shape"
									data-object={pose.id}
									data-array={array.id}
									data-excluded={!pose.included || undefined}
									data-selected={
										selected === pose.id || selected === array.id || undefined
									}
								/>
							))}
					</g>
				))}
				{/* Keep constraint objects visible/selectable when module projections overlap them. */}
				{keepouts.map((object) => (
					<polygon
						key={object.id}
						points={points(object.footprint_uv)}
						className="lp-keepout-shape"
						data-object={object.id}
						data-selected={selected === object.id || undefined}
					/>
				))}
				{obstacles.map((object) => (
					<g
						key={object.id}
						className="lp-obstacle-shape"
						data-object={object.id}
						data-selected={selected === object.id || undefined}
					>
						<polygon points={points(object.footprint_uv)} />
						<polygon points={points(object.top)} />
						{object.footprint_uv.map((point, index) => (
							<polygon
								key={index}
								points={points([
									point,
									object.footprint_uv[
										(index + 1) % object.footprint_uv.length
									]!,
									object.top[(index + 1) % object.top.length]!,
									object.top[index]!,
								])}
							/>
						))}
					</g>
				))}
			</svg>
			<div className="lp-canvas-caption">
				<span>{__("Roof plane · metres", "linker-tools")}</span>
				<span>U → · V ↑</span>
			</div>
			<p className="lp-profile-help">
				{__(
					"Dragging a module moves its array in this roof plane. Numeric properties provide the same operation. Pan and zoom change only the view.",
					"linker-tools",
				)}
			</p>
		</div>
	);
}
