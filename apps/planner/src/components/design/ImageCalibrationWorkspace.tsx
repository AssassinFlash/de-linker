/** Two-point image calibration inside Roof design: upload, set the scale, trace.
 *
 * The photograph or drawing never leaves the browser in this increment; the
 * project records the source's declared measurement basis — the original's
 * identity, its pixel size, the two control points and their real length, the
 * scale that follows from them, the drawing type and the independent second
 * span. Only a measurable view with a passing second span yields engineering
 * lengths; a perspective photograph stays reference-only (dossier precedent,
 * docs/research/2026-10-23-map-workbench-integration/IMPLEMENTATION.md).
 */
import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import type {
	GeometryDocument,
	RoofFace,
	Vec2,
} from "../../domain/geometry.ts";
import type {
	GeometryCommand,
	GeometryEdit,
} from "../../domain/geometryCommands.ts";
import {
	buildCalibration,
	measurementStatus,
	pixelToUv,
	type CalibrationPoints,
	type CalibrationView,
} from "../../domain/imageCalibration.ts";
import type { ImageCalibration } from "../../domain/imageCalibration.ts";
import { GeometryValues } from "./GeometryForm.tsx";
import { roofPlane } from "../../domain/geometryEditing.ts";
import { formatDecimal } from "../../domain/decimal.ts";
import { Notice } from "../Notice.tsx";
import { revealActionResult } from "../revealActionResult.ts";
import { __, sprintf } from "../../i18n.ts";

const MEDIA = ["image/png", "image/jpeg", "image/webp"] as const;
/** The written summary the record carries until the final step replaces it. */
const DEFAULT_NOTE = "Two-point scale from the drawing; not a survey.";
type MediaType = (typeof MEDIA)[number];
// Initial browser intake policy for the drawing image; not a roof limit.
const MAX_IMAGE_BYTES = 8 * 1024 * 1024;

interface Drawing {
	url: string;
	media_type: MediaType;
	pixel_width: number;
	pixel_height: number;
	name: string;
	size: number;
}

/** The image's own pixels, read from the decoded file rather than typed. */
async function decodeImage(file: File): Promise<Drawing> {
	if (
		file.size > MAX_IMAGE_BYTES ||
		!(MEDIA as readonly string[]).includes(file.type)
	)
		throw new Error("image_calibration_file");
	const bitmap = await createImageBitmap(file);
	try {
		const width = bitmap.width,
			height = bitmap.height;
		if (
			!Number.isSafeInteger(width) ||
			!Number.isSafeInteger(height) ||
			width <= 0 ||
			height <= 0
		)
			throw new Error("image_calibration_file");
		return {
			url: URL.createObjectURL(file),
			media_type: file.type as MediaType,
			pixel_width: width,
			pixel_height: height,
			name: file.name,
			size: file.size,
		};
	} finally {
		bitmap.close();
	}
}

/** Ring area in the roof plane, for review only; the server checks the layout. */
function ringArea(ring: readonly Vec2[]): number {
	let sum = 0;
	for (let index = 0; index < ring.length; index++) {
		const [u1, v1] = ring[index]!,
			[u2, v2] = ring[(index + 1) % ring.length]!;
		sum += u1 * v2 - u2 * v1;
	}
	return Math.abs(sum) / 2;
}

/**
 * A click on the `xMidYMid meet` SVG surface as an image pixel. The viewBox is
 * the image's own pixel grid, so the letterboxing must be removed before the
 * point can name a pixel; an off-image click names nothing.
 */
export function imagePixel(
	box: { width: number; height: number },
	clientX: number,
	clientY: number,
	width: number,
	height: number,
	left = 0,
	top = 0,
): Vec2 | null {
	if (box.width <= 0 || box.height <= 0 || width <= 0 || height <= 0)
		return null;
	const scale = Math.min(box.width / width, box.height / height);
	if (!(scale > 0) || !Number.isFinite(scale)) return null;
	const drawnWidth = width * scale,
		drawnHeight = height * scale,
		x = (clientX - left - (box.width - drawnWidth) / 2) / scale,
		y = (clientY - top - (box.height - drawnHeight) / 2) / scale;
	if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
	if (x < 0 || y < 0 || x > width || y > height) return null;
	return [x, y];
}

export function ImageCalibrationWorkspace({
	geometry,
	roofId,
	locale,
	disabled,
	onActivity,
	commit,
}: {
	geometry: GeometryDocument;
	roofId: string | null;
	locale: string;
	disabled: boolean;
	onActivity: (open: boolean) => void;
	commit: (command: GeometryCommand) => boolean;
}) {
	const [open, setOpen] = useState(false),
		[step, setStep] = useState(0),
		[drawing, setDrawing] = useState<Drawing | null>(null),
		[view, setView] = useState<CalibrationView>("horizontal_plan"),
		[mode, setMode] = useState<"scale" | "check" | "trace">("scale"),
		[scalePoints, setScalePoints] = useState<readonly Vec2[]>([]),
		[checkPoints, setCheckPoints] = useState<readonly Vec2[]>([]),
		[withCheck, setWithCheck] = useState(true),
		[target, setTarget] = useState<string>("new"),
		[roofName, setRoofName] = useState(""),
		[trace, setTrace] = useState<readonly Vec2[]>([]),
		[error, setError] = useState<string | null>(null),
		[reading, setReading] = useState(false);
	// Uncontrolled fields keep their own text; this only asks React to re-read
	// them, so the live scale summary follows what is actually in the form.
	const [, setTyped] = useState(0);
	const form = useRef<HTMLFormElement>(null),
		heading = useRef<HTMLHeadingElement>(null),
		trigger = useRef<HTMLButtonElement>(null),
		restoreTrigger = useRef(false),
		focusStep = useRef(false),
		sequence = useRef(0);
	const targetRoof: RoofFace | null =
		target === "new"
			? null
			: (geometry.roofs.find((roof) => roof.id === target) ?? null);
	const targetSource = targetRoof
		? (geometry.sources.find((source) => source.id === targetRoof.source_id) ??
			null)
		: null;
	useEffect(() => {
		onActivity(open);
		return () => onActivity(false);
	}, [open, onActivity]);
	useEffect(
		() => () => {
			sequence.current++;
		},
		[],
	);
	useEffect(() => {
		if (!focusStep.current || !open) return;
		focusStep.current = false;
		revealActionResult(heading.current);
	}, [open, step]);
	useEffect(() => {
		if (restoreTrigger.current && !open && !disabled) {
			trigger.current?.focus();
			if (document.activeElement === trigger.current)
				restoreTrigger.current = false;
		}
	}, [open, disabled]);
	useEffect(
		() => () => {
			if (drawing) URL.revokeObjectURL(drawing.url);
		},
		[drawing],
	);

	/** The image as displayed is not an engineering length; only the declared
	 * scale converts a click. The element's own box gives the pixel. */
	function imagePoint(event: React.MouseEvent<SVGSVGElement>): Vec2 | null {
		if (!drawing) return null;
		const box = event.currentTarget.getBoundingClientRect();
		return imagePixel(
			box,
			event.clientX,
			event.clientY,
			drawing.pixel_width,
			drawing.pixel_height,
			box.left,
			box.top,
		);
	}
	function place(event: React.MouseEvent<SVGSVGElement>) {
		const point = imagePoint(event);
		if (!point) return;
		setError(null);
		if (mode === "scale") {
			setScalePoints((points) =>
				points.length === 2 ? [point] : [...points, point],
			);
		} else if (mode === "check") {
			setCheckPoints((points) =>
				points.length === 2 ? [point] : [...points, point],
			);
		} else {
			setTrace((points) => [...points, point]);
		}
	}
	const formValues = () => new GeometryValues(form.current!, locale);

	function scaleFromField(values: GeometryValues): number {
		return values.metric("length", { positive: true });
	}

	function buildFromFields(values: GeometryValues): ImageCalibration | null {
		if (!drawing || scalePoints.length !== 2) return null;
		// Steps before the last carry no source note; the record's own summary is
		// entered there, so earlier steps validate the arithmetic only.
		const note = values.text("note") || DEFAULT_NOTE;
		const controlPoints: CalibrationPoints = {
			first: scalePoints[0]!,
			second: scalePoints[1]!,
		};
		const check: CalibrationPoints | null =
			withCheck && checkPoints.length === 2
				? { first: checkPoints[0]!, second: checkPoints[1]! }
				: null;
		return buildCalibration({
			view,
			image: {
				media_type: drawing.media_type,
				pixel_width: drawing.pixel_width,
				pixel_height: drawing.pixel_height,
			},
			controlPoints,
			knownLength: scaleFromField(values),
			checkPoints: check,
			checkLength: check
				? values.metric("check_length", { positive: true })
				: null,
			// The tolerance field only exists while the optional check is on; the
			// record still states a limit, so an unchecked check keeps the default.
			checkToleranceRatio:
				values.number("tolerance", {
					min: 0,
					positive: true,
					optional: true,
				}) ?? 0.01,
			downslopeBearingDeg: values.metric("bearing", {
				min: 0,
				maxExclusive: 360,
			}),
			pitchDeg: values.metric("pitch", { min: 0, maxExclusive: 90 }),
			note,
		});
	}

	function review(values?: GeometryValues): ImageCalibration | null {
		if (!drawing) return null;
		try {
			return buildFromFields(values ?? formValues());
		} catch {
			return null;
		}
	}

	function start() {
		if (disabled) return;
		if (drawing) URL.revokeObjectURL(drawing.url);
		setDrawing(null);
		setStep(0);
		setMode("scale");
		setScalePoints([]);
		setCheckPoints([]);
		setWithCheck(true);
		setTrace([]);
		setRoofName(
			geometry.roofs.some((roof) => roof.id === roofId) && roofId
				? ""
				: __("Roof from drawing", "linker-tools"),
		);
		setTarget(roofId ?? "new");
		setError(null);
		setOpen(true);
		focusStep.current = true;
	}
	function close() {
		if (reading) return;
		sequence.current++;
		if (drawing) URL.revokeObjectURL(drawing.url);
		setDrawing(null);
		setTrace([]);
		setScalePoints([]);
		setCheckPoints([]);
		setError(null);
		restoreTrigger.current = true;
		setOpen(false);
	}
	async function choose(file: File | undefined) {
		if (!file || reading) return;
		const step = ++sequence.current;
		setReading(true);
		setError(null);
		try {
			const next = await decodeImage(file);
			if (step !== sequence.current) {
				URL.revokeObjectURL(next.url);
				return;
			}
			if (drawing) URL.revokeObjectURL(drawing.url);
			setDrawing(next);
			setScalePoints([]);
			setCheckPoints([]);
			setTrace([]);
			setMode("scale");
		} catch {
			if (step === sequence.current)
				setError(
					__(
						"This image could not be used. Choose a PNG, JPEG or WebP file up to 8 MB.",
						"linker-tools",
					),
				);
		} finally {
			if (step === sequence.current) setReading(false);
		}
	}

	function checkStep(index: number, values: GeometryValues) {
		const section = form.current?.querySelector<HTMLElement>(
			`[data-calibration-step="${index}"]`,
		);
		for (const input of section?.querySelectorAll<
			HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
		>("input,textarea,select") ?? []) {
			if (input.type === "file") continue;
			if (
				input.required &&
				(input instanceof window.HTMLInputElement && input.type === "checkbox"
					? !input.checked
					: !input.value.trim())
			)
				input.setCustomValidity(
					__("Complete this field to continue.", "linker-tools"),
				);
			if (!input.checkValidity()) {
				setStep(index);
				setError(input.validationMessage);
				window.setTimeout(() => {
					if (!input.isConnected || input.closest("[hidden]")) return;
					input.reportValidity();
					revealActionResult(input);
				});
				return false;
			}
		}
		if (index === 0) {
			if (!drawing) {
				setError(__("Choose the drawing or photo first.", "linker-tools"));
				return false;
			}
			if (target === "new" && !values.text("roof").trim()) {
				setError(__("Name the roof face this drawing shows.", "linker-tools"));
				return false;
			}
		}
		if (index === 1) {
			if (scalePoints.length !== 2) {
				setError(
					__(
						"Mark both ends of the span whose real length you know.",
						"linker-tools",
					),
				);
				return false;
			}
			values.metric("length", { positive: true });
			values.metric("bearing", { min: 0, maxExclusive: 360 });
			values.metric("pitch", { min: 0, maxExclusive: 90 });
			if (withCheck) {
				values.metric("check_length", { positive: true });
				values.number("tolerance", { positive: true, optional: true });
				if (checkPoints.length !== 2) {
					setError(
						__(
							"Mark both ends of the independent second span, or turn the check off.",
							"linker-tools",
						),
					);
					return false;
				}
			}
			const calibration = buildFromFields(values);
			if (!calibration) {
				setError(
					__(
						"The scale could not be recorded from these entries.",
						"linker-tools",
					),
				);
				return false;
			}
			if (
				calibration.measurement_status === "reference_only" &&
				checkPoints.length === 2 &&
				withCheck
			)
				setError(
					sprintf(
						__(
							"The second span differs by %s %%. The drawing stays a reference and cannot measure the roof until the points or the length are corrected.",
							"linker-tools",
						),
						(calibration.check!.residual_ratio * 100).toFixed(1),
					),
				);
		}
		return true;
	}

	function submit(event: FormEvent<HTMLFormElement>) {
		event.preventDefault();
		setError(null);
		try {
			const values = new GeometryValues(event.currentTarget, locale);
			if (!checkStep(step, values)) return;
			if (step < 2) {
				setStep(step + 1);
				focusStep.current = true;
				return;
			}
			for (let index = 0; index < 2; index++)
				if (!checkStep(index, values)) return;
			if (trace.length < 3) {
				setError(
					__(
						"Mark at least three points along the roof outline.",
						"linker-tools",
					),
				);
				return;
			}
			const calibration = buildFromFields(values);
			if (!calibration) return;
			// A perspective photo, or a scale its own second span contradicts,
			// stays a reference: one uniform scale cannot measure it, so it may
			// not create engineering geometry.
			if (calibration.measurement_status !== "usable_uniform_scale") {
				setError(
					__(
						"This drawing is a reference only, so it cannot measure the roof. Mark a measurable plan or slope view whose second span agrees, or keep the drawing beside an already measured roof face.",
						"linker-tools",
					),
				);
				return;
			}
			const ring = trace.map((point) => pixelToUv(point, calibration));
			// Drawing datum: the outline's own lower-left corner becomes UV (0, 0).
			const minU = Math.min(...ring.map(([u]) => u)),
				minV = Math.min(...ring.map(([, v]) => v));
			const boundary = ring.map(([u, v]) => [u - minU, v - minV] as const);
			const name = targetRoof ? targetRoof.name : values.text("roof").trim();
			const source = targetSource ?? {
				id: "source_" + crypto.randomUUID().replaceAll("-", ""),
				kind: "user_drawing" as const,
				note: values.text("source"),
				rights_note: "",
				reference_url: null,
				reference_sha256: null,
				acquired_at_utc: null,
				spatial_precision_m: null,
				calibration_note: "",
				rights_basis: "user_attestation" as const,
				permissions: {
					derive: "permitted" as const,
					retain: "permitted" as const,
					export: values.text("export") as
						"permitted" | "unknown" | "prohibited",
				},
			};
			// The one authoritative face constructor: U is cross-slope, V runs
			// down-slope and the upward normal's horizontal direction is the
			// declared bearing. The drawing's page-down is that same down-slope
			// direction, so the traced ring enters the frame unchanged.
			const plane = roofPlane(
				calibration.applied_pitch_deg ?? 0,
				calibration.downslope_bearing_deg,
				targetRoof?.origin_enu ?? [0, 0, 0],
			);
			const roof: RoofFace = {
				id: targetRoof?.id ?? "roof_" + crypto.randomUUID().replaceAll("-", ""),
				name,
				source_id: source.id,
				origin_enu: plane.origin_enu,
				u_axis_enu: plane.u_axis_enu,
				v_axis_enu: plane.v_axis_enu,
				boundary_uv: boundary,
				holes_uv: targetRoof?.holes_uv ?? [],
			};
			const edits: GeometryEdit[] = [
				{
					type: "put_source",
					before: targetSource,
					value: {
						...source,
						note: targetSource ? source.note : values.text("source"),
						rights_note: targetSource
							? source.rights_note
							: values.text("rights"),
						spatial_precision_m: values.number("precision", {
							optional: true,
							min: 0,
						}),
						calibration,
						calibration_note: values.text("note"),
					},
				},
				{ type: "put_roof", before: targetRoof, value: roof },
			];
			if (commit({ type: "group", edits })) close();
		} catch (cause) {
			if (
				cause instanceof Error &&
				"field" in cause &&
				typeof cause.field === "string"
			) {
				const input = form.current?.elements.namedItem(cause.field);
				if (input instanceof window.HTMLInputElement) {
					input.setCustomValidity(cause.message);
					input.setAttribute("aria-invalid", "true");
					input.reportValidity();
					revealActionResult(input);
				}
				setError(cause.message);
			} else
				setError(
					__(
						"These settings could not be applied. The current design is unchanged and your marks remain.",
						"linker-tools",
					),
				);
		}
	}

	const calibration =
			open && drawing && scalePoints.length === 2 ? review() : null,
		status = calibration
			? measurementStatus(view, calibration.check)
			: "reference_only";
	const markSurface = (
		<>
			{drawing && (
				<div className="lp-plan-view">
					<svg
						className="lp-plan-svg"
						viewBox={`0 0 ${drawing.pixel_width} ${drawing.pixel_height}`}
						role="group"
						tabIndex={0}
						aria-label={__(
							"Place the calibration marks on the image",
							"linker-tools",
						)}
						onClick={place}
					>
						<image
							href={drawing.url}
							width={drawing.pixel_width}
							height={drawing.pixel_height}
						/>
						{trace.length > 1 && (
							<polyline points={trace.map(([x, y]) => `${x},${y}`).join(" ")} />
						)}
						{trace.length > 2 && (
							<line
								x1={trace[0]![0]}
								y1={trace[0]![1]}
								x2={trace.at(-1)![0]}
								y2={trace.at(-1)![1]}
							/>
						)}
						{scalePoints.map(([x, y], index) => (
							<circle
								key={`scale-${index}`}
								cx={x}
								cy={y}
								r={7}
								data-mark="scale"
							/>
						))}
						{checkPoints.map(([x, y], index) => (
							<circle
								key={`check-${index}`}
								cx={x}
								cy={y}
								r={7}
								data-mark="check"
							/>
						))}
						{trace.map(([x, y], index) => (
							<circle
								key={`trace-${index}`}
								cx={x}
								cy={y}
								r={5}
								data-mark="trace"
							/>
						))}
					</svg>
				</div>
			)}
			<div
				className="lp-view-switch"
				role="group"
				aria-label={__("Calibration entry", "linker-tools")}
			>
				<button
					type="button"
					aria-pressed={mode === "scale"}
					onClick={() => setMode("scale")}
				>
					{sprintf(
						__("Scale span (%d of 2)", "linker-tools"),
						scalePoints.length,
					)}
				</button>
				<button
					type="button"
					aria-pressed={mode === "check"}
					disabled={!withCheck}
					onClick={() => setMode("check")}
				>
					{sprintf(
						__("Check span (%d of 2)", "linker-tools"),
						checkPoints.length,
					)}
				</button>
				<button
					type="button"
					aria-pressed={mode === "trace"}
					onClick={() => setMode("trace")}
				>
					{sprintf(
						__("Roof outline (%d points)", "linker-tools"),
						trace.length,
					)}
				</button>
			</div>
			<div className="lp-inline-actions">
				<button
					type="button"
					className="lp-text-button"
					onClick={() => {
						if (mode === "scale") setScalePoints([]);
						else if (mode === "check") setCheckPoints([]);
						else setTrace((points) => points.slice(0, -1));
					}}
				>
					{mode === "trace"
						? __("Remove the last point", "linker-tools")
						: __("Clear these marks", "linker-tools")}
				</button>
				<button
					type="button"
					className="lp-text-button"
					onClick={() => {
						setScalePoints([]);
						setCheckPoints([]);
						setTrace([]);
						setMode("scale");
					}}
				>
					{__("Clear all marks", "linker-tools")}
				</button>
			</div>
		</>
	);
	const stepNames = [
		__("Image and roof", "linker-tools"),
		__("Scale", "linker-tools"),
		__("Outline", "linker-tools"),
	];
	return (
		<div className="lp-geometry-intake">
			<div className="lp-inline-actions">
				<button
					type="button"
					className="lp-button lp-button-secondary"
					ref={trigger}
					disabled={disabled || open || reading}
					onClick={start}
				>
					{__("Calibrate a roof image", "linker-tools")}
				</button>
				<span>
					{__(
						"Scale a drawing or photo with two points and trace the roof outline on it.",
						"linker-tools",
					)}
				</span>
			</div>
			{open && (
				<div className="lp-import-panel">
					<div className="lp-section-heading">
						<div>
							<h3 ref={heading} tabIndex={-1}>
								{stepNames[step]}
							</h3>
							<p>
								{__(
									"Two points and one real length give a single scale. A second independent span checks it; a perspective photo stays a reference and cannot measure the roof.",
									"linker-tools",
								)}
							</p>
						</div>
					</div>
					<ol className="lp-import-steps">
						{stepNames.map((name, index) => (
							<li key={name} aria-current={index === step ? "step" : undefined}>
								<span>{String(index + 1).padStart(2, "0")}</span>
								{name}
							</li>
						))}
					</ol>
					{error && <Notice error>{error}</Notice>}
					<form
						ref={form}
						onSubmit={submit}
						onInput={() => setTyped((value) => value + 1)}
						noValidate
					>
						{step > 0 && markSurface}
						<div data-calibration-step="0" hidden={step !== 0}>
							<label className="lp-field">
								<span>{__("Drawing or photo", "linker-tools")}</span>
								<span className="lp-file-picker">
									<span className="lp-file-button">
										{__("Choose a file", "linker-tools")}
									</span>
									<input
										type="file"
										accept="image/png,image/jpeg,image/webp"
										disabled={reading}
										onChange={(event) =>
											void choose(event.currentTarget.files?.[0])
										}
									/>
									<span className="lp-file-name">
										{drawing
											? drawing.name
											: __("No file selected", "linker-tools")}
									</span>
								</span>
								<small>
									{drawing
										? sprintf(
												__("%1$d × %2$d pixels", "linker-tools"),
												drawing.pixel_width,
												drawing.pixel_height,
											)
										: __(
												"PNG, JPEG or WebP, up to 8 MB. The image stays in this browser; the project records its calibration.",
												"linker-tools",
											)}
								</small>
							</label>
							<div className="lp-geometry-fields">
								<label className="lp-field">
									<span>{__("Drawing type", "linker-tools")}</span>
									<select
										name="view"
										value={view}
										onChange={(event) =>
											setView(event.currentTarget.value as CalibrationView)
										}
									>
										<option value="horizontal_plan">
											{__("Horizontal plan or site plan", "linker-tools")}
										</option>
										<option value="roof_slope_elevation">
											{__("Roof slope elevation", "linker-tools")}
										</option>
										<option value="perspective_photo">
											{__("Perspective photo", "linker-tools")}
										</option>
									</select>
								</label>
								<label className="lp-field">
									<span>{__("Roof face", "linker-tools")}</span>
									<select
										name="target"
										value={target}
										onChange={(event) => setTarget(event.currentTarget.value)}
									>
										<option value="new">
											{__("New roof face", "linker-tools")}
										</option>
										{geometry.roofs.map((roof) => (
											<option key={roof.id} value={roof.id}>
												{sprintf(
													__("Replace the outline of %s", "linker-tools"),
													roof.name,
												)}
											</option>
										))}
									</select>
								</label>
							</div>
							{target === "new" && (
								<label className="lp-field">
									<span>{__("Roof face name", "linker-tools")}</span>
									<input
										name="roof"
										defaultValue={roofName}
										maxLength={4096}
										required
									/>
								</label>
							)}
						</div>
						<div data-calibration-step="1" hidden={step !== 1}>
							<div className="lp-geometry-fields">
								<label className="lp-field">
									<span>
										{__("Real length of the scale span", "linker-tools")}
										<small>m</small>
									</span>
									<input
										name="length"
										inputMode="decimal"
										autoComplete="off"
										required
									/>
								</label>
								<label className="lp-field">
									<span>
										{__("Down-slope bearing as drawn", "linker-tools")}
										<small>°</small>
									</span>
									<input
										name="bearing"
										inputMode="decimal"
										autoComplete="off"
										defaultValue="0"
										required
									/>
									<small>
										{__(
											"Clockwise from project north to the direction drawn down the page: 0 north, 90 east, 180 south, 270 west. The page's right edge is then cross-slope.",
											"linker-tools",
										)}
									</small>
								</label>
								<label className="lp-field">
									<span>
										{__("Roof pitch", "linker-tools")}
										<small>°</small>
									</span>
									<input
										name="pitch"
										inputMode="decimal"
										autoComplete="off"
										defaultValue="0"
										required
									/>
									<small>
										{__(
											"A horizontal plan is converted into slope lengths once through this pitch. A slope drawing states them already.",
											"linker-tools",
										)}
									</small>
								</label>
							</div>
							<label className="lp-geometry-check">
								<input
									name="withCheck"
									type="checkbox"
									checked={withCheck}
									onChange={(event) => {
										setWithCheck(event.currentTarget.checked);
										if (!event.currentTarget.checked) setMode("scale");
									}}
								/>
								{__(
									"Check the scale with a second, independent span",
									"linker-tools",
								)}
							</label>
							{withCheck && (
								<div className="lp-geometry-fields">
									<label className="lp-field">
										<span>
											{__("Real length of the check span", "linker-tools")}
											<small>m</small>
										</span>
										<input
											name="check_length"
											inputMode="decimal"
											autoComplete="off"
											required
										/>
									</label>
									<label className="lp-field">
										<span>{__("Permitted difference", "linker-tools")}</span>
										<input
											name="tolerance"
											inputMode="decimal"
											autoComplete="off"
											defaultValue={formatDecimal(0.01, locale)}
											required
										/>
										<small>
											{__(
												"Relative difference between the two spans that still counts as agreement, for example 0.01 for one percent. It is your declared limit, not a surveying rule.",
												"linker-tools",
											)}
										</small>
									</label>
								</div>
							)}
							{calibration && (
								<dl className="lp-field-summary">
									<div>
										<dt>{__("Recorded scale", "linker-tools")}</dt>
										<dd>
											{sprintf(
												__("%s m per pixel", "linker-tools"),
												calibration.m_per_pixel.toPrecision(6),
											)}
										</dd>
									</div>
									<div>
										<dt>{__("Measurement status", "linker-tools")}</dt>
										<dd>
											{status === "usable_uniform_scale"
												? __("Usable uniform scale", "linker-tools")
												: __("Reference only", "linker-tools")}
										</dd>
									</div>
									{calibration.check && (
										<div>
											<dt>{__("Check span difference", "linker-tools")}</dt>
											<dd>
												{sprintf(
													__("%s %%", "linker-tools"),
													(calibration.check.residual_ratio * 100).toPrecision(
														3,
													),
												)}
											</dd>
										</div>
									)}
								</dl>
							)}
						</div>
						<div data-calibration-step="2" hidden={step !== 2}>
							<label className="lp-field">
								<span>
									{__("Measurement or drawing reference", "linker-tools")}
								</span>
								<textarea
									name="note"
									rows={3}
									maxLength={4096}
									required
									defaultValue={DEFAULT_NOTE}
								/>
							</label>
							{!targetSource && (
								<>
									<label className="lp-field">
										<span>{__("Source reference", "linker-tools")}</span>
										<textarea
											name="source"
											rows={3}
											maxLength={4096}
											required
											defaultValue={drawing?.name ?? ""}
										/>
									</label>
									<label className="lp-field">
										<span>
											{__("Permission or licence basis", "linker-tools")}
										</span>
										<textarea
											name="rights"
											rows={3}
											maxLength={4096}
											required
										/>
									</label>
									<label className="lp-field">
										<span>
											{__("Declared spatial precision", "linker-tools")}
											<small>m</small>
										</span>
										<input
											name="precision"
											inputMode="decimal"
											autoComplete="off"
										/>
										<small>
											{__(
												"0 or greater. An empty field means unknown. This is a source claim, separate from the scale arithmetic.",
												"linker-tools",
											)}
										</small>
									</label>
									<label className="lp-field">
										<span>
											{__("Permission to export geometry", "linker-tools")}
										</span>
										<select name="export" defaultValue="unknown">
											<option value="unknown">
												{__("Unknown", "linker-tools")}
											</option>
											<option value="permitted">
												{__("Permitted", "linker-tools")}
											</option>
											<option value="prohibited">
												{__("Prohibited", "linker-tools")}
											</option>
										</select>
									</label>
									<label className="lp-geometry-check">
										<input name="retention" type="checkbox" required />
										{__(
											"I have permission to use this drawing, derive the roof outline from it and keep the calibration with the project.",
											"linker-tools",
										)}
									</label>
								</>
							)}
							{calibration && (
								<dl className="lp-field-summary lp-import-review">
									<div>
										<dt>{__("Roof face", "linker-tools")}</dt>
										<dd>{targetRoof ? targetRoof.name : roofName}</dd>
									</div>
									<div>
										<dt>{__("Outline points", "linker-tools")}</dt>
										<dd>{trace.length}</dd>
									</div>
									<div>
										<dt>{__("Roof-plane area", "linker-tools")}</dt>
										<dd>
											{ringArea(
												trace.map((point) => pixelToUv(point, calibration)),
											).toFixed(2)}{" "}
											<small>m²</small>
										</dd>
									</div>
									<div>
										<dt>{__("Measurement status", "linker-tools")}</dt>
										<dd>
											{status === "usable_uniform_scale"
												? __("Usable uniform scale", "linker-tools")
												: __("Reference only", "linker-tools")}
										</dd>
									</div>
								</dl>
							)}
							<p className="lp-profile-help">
								{__(
									"Adding the drawing records its calibration with this roof face and replaces the outline with the marks above. Openings remain editable in roof properties.",
									"linker-tools",
								)}
							</p>
						</div>
						<div className="lp-inline-actions">
							{step > 0 && (
								<button
									type="button"
									className="lp-button lp-button-secondary"
									onClick={() => setStep(step - 1)}
								>
									{__("Back", "linker-tools")}
								</button>
							)}
							<button className="lp-button" type="submit" disabled={reading}>
								{step < 2
									? __("Continue", "linker-tools")
									: __("Add roof to current design", "linker-tools")}
							</button>
							<button type="button" className="lp-text-button" onClick={close}>
								{__("Cancel", "linker-tools")}
							</button>
						</div>
					</form>
				</div>
			)}
		</div>
	);
}
