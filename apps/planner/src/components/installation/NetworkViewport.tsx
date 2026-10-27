import { useMemo, useRef } from "react";
import type { GeometryDocument } from "../../domain/geometry.ts";
import type {
	InstallationInputs,
	RoutePoint,
} from "../../domain/installation.ts";
import { add, vectorFromRoof } from "../../domain/coordinates.ts";
import { __ } from "../../i18n.ts";

export function NetworkViewport({
	geometry,
	plan,
	draftPoints,
	pick,
}: {
	geometry: GeometryDocument;
	plan: InstallationInputs;
	draftPoints?: readonly RoutePoint[];
	pick?: ((point: RoutePoint) => void) | undefined;
}) {
	const svg = useRef<SVGSVGElement>(null);
	const roofs = useMemo(
		() =>
			geometry.roofs.map((r) =>
				r.boundary_uv.map(([u, v]) =>
					add(r.origin_enu, vectorFromRoof(r, [u, v, 0])),
				),
			),
		[geometry],
	);
	const all = [
		...roofs.flat().map((p) => [p[0], p[1]] as const),
		...plan.instances.flatMap((d) =>
			d.ports.map((p) => [p.position.east_m, p.position.north_m] as const),
		),
		...plan.routes.flatMap((r) =>
			r.points.map((p) => [p.east_m, p.north_m] as const),
		),
		...(draftPoints ?? []).map((p) => [p.east_m, p.north_m] as const),
	];
	let minX = Infinity,
		maxX = -Infinity,
		minY = Infinity,
		maxY = -Infinity;
	for (const [x, y] of all) {
		minX = Math.min(minX, x);
		maxX = Math.max(maxX, x);
		minY = Math.min(minY, -y);
		maxY = Math.max(maxY, -y);
	}
	if (!all.length) {
		minX = minY = 0;
		maxX = maxY = 1;
	}
	// View framing only; it does not create geometry or installation dimensions.
	const span = Math.max(maxX - minX, maxY - minY, 1),
		margin = span / 10;
	const line = (points: readonly RoutePoint[]) =>
		points.map((p) => `${p.east_m},${-p.north_m}`).join(" ");
	return (
		<div className="lp-plan-view">
			<svg
				ref={svg}
				role="img"
				aria-label={__(
					"Installation plan · East and North in metres",
					"linker-tools",
				)}
				viewBox={`${minX - margin} ${minY - margin} ${maxX - minX + 2 * margin} ${maxY - minY + 2 * margin}`}
				width="100%"
				height="360"
				onClick={(event) => {
					if (!pick || !svg.current) return;
					const matrix = svg.current.getScreenCTM();
					if (!matrix) return;
					const point = new DOMPoint(
						event.clientX,
						event.clientY,
					).matrixTransform(matrix.inverse());
					pick({ east_m: point.x, north_m: -point.y, height_m: null });
				}}
			>
				{roofs.map((ring, i) => (
					<polygon
						key={geometry.roofs[i]!.id}
						points={ring.map((p) => `${p[0]},${-p[1]}`).join(" ")}
						fill="none"
						stroke="currentColor"
						opacity={0.25}
						vectorEffect="non-scaling-stroke"
					/>
				))}
				{plan.routes.map((r) => (
					<polyline
						key={r.id}
						points={line(r.points)}
						fill="none"
						stroke="currentColor"
						strokeWidth="2"
						strokeDasharray={
							r.points.some((p) => p.height_m === null) ? "5 4" : undefined
						}
						vectorEffect="non-scaling-stroke"
					>
						<title>{r.name}</title>
					</polyline>
				))}
				{draftPoints && (
					<polyline
						points={line(draftPoints)}
						fill="none"
						stroke="currentColor"
						strokeWidth="3"
						vectorEffect="non-scaling-stroke"
					/>
				)}
				{plan.instances.flatMap((d) =>
					d.ports.map((p) => (
						<g key={d.id + ":" + p.id}>
							<circle
								cx={p.position.east_m}
								cy={-p.position.north_m}
								r={span / 120}
								fill="currentColor"
							/>
							<text
								x={p.position.east_m + span / 80}
								y={-p.position.north_m - span / 100}
								fontSize={span / 35}
							>
								{d.name} · {p.name}
							</text>
						</g>
					)),
				)}
			</svg>
			<p className="lp-profile-help">
				{pick
					? __(
							"Click to add a plan point, then enter its height from the source measurement or drawing.",
							"linker-tools",
						)
					: __(
							"Plan view shows horizontal positions. Heights remain in the route properties and 3D view.",
							"linker-tools",
						)}
			</p>
		</div>
	);
}
