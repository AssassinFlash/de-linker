import { useEffect, useId, useRef, useState } from "react";
import type { FormEvent } from "react";
import type { GeometryDocument } from "../../domain/geometry.ts";
import type {
	GeometryImportCommand,
	PreparedGeometryImport,
} from "../../domain/geometryImports.ts";
import { readGeometryImportCommand } from "../../domain/geometryImports.ts";
import { geoJsonChoices } from "../../domain/geoJsonChoices.ts";
import type { GeoJsonChoice } from "../../domain/geoJsonChoices.ts";
import { roofPlaneAtVertex } from "../../domain/geometryEditing.ts";
import { fileBase64 } from "../../domain/profiles.ts";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import type { Session } from "../../data/protocol.ts";
import type { GeometryImportIntent } from "../../data/GeometryImportStore.ts";
import { useGeometryImport } from "../../data/useGeometryImport.ts";
import type { GeometryImportJournal } from "../../data/useGeometryImport.ts";
import { isPreMutationInputRefusal } from "../../data/inputRefusal.ts";
import policy from "../../contracts/geometry-import-policy.json" with { type: "json" };
import { GeometryValues } from "./GeometryForm.tsx";
import { GeometryImportFields, choiceKey } from "./GeometryImportFields.tsx";
import { GeometryImportSettings } from "./GeometryImportSettings.tsx";
import { PlanViewport } from "./PlanViewport.tsx";
import { Notice } from "../Notice.tsx";
import { revealActionResult } from "../revealActionResult.ts";
import { __ } from "../../i18n.ts";

/** Preparing a source and adding it to project history are separate actions. */
export function GeometryIntake({
	geometry,
	projectId,
	session,
	client,
	locale,
	recheck,
	disabled,
	onActivity,
	attach,
	currentAssetIds,
	confirmedAssetIds,
	recoveryScopes,
	recoveryChecking,
	store,
}: {
	geometry: GeometryDocument;
	projectId: string;
	session: Session;
	client: PlannerClient;
	locale: string;
	recheck: () => void;
	disabled: boolean;
	onActivity: (open: boolean) => void;
	attach: (before: GeometryDocument, asset: PreparedGeometryImport) => boolean;
	currentAssetIds: readonly string[];
	confirmedAssetIds: readonly string[];
	recoveryScopes?: readonly string[] | undefined;
	recoveryChecking?: boolean | undefined;
	store?: GeometryImportJournal | undefined;
}) {
	const [open, setOpen] = useState(false),
		[step, setStep] = useState(0),
		[snapshot, setSnapshot] = useState(geometry),
		[recovery, setRecovery] = useState<GeometryImportIntent | null>(null),
		[content, setContent] = useState(""),
		[filename, setFilename] = useState(""),
		[choices, setChoices] = useState<readonly GeoJsonChoice[]>([]),
		[selected, setSelected] = useState(""),
		[roofName, setRoofName] = useState(""),
		[zeroHeight, setZeroHeight] = useState(false),
		[previousCommand, setPreviousCommand] =
			useState<GeometryImportCommand | null>(null),
		[reading, setReading] = useState(false),
		[error, setError] = useState<string | null>(null),
		[applied, setApplied] = useState<string | null>(null);
	const id = useId(),
		form = useRef<HTMLFormElement>(null),
		heading = useRef<HTMLHeadingElement>(null),
		trigger = useRef<HTMLButtonElement>(null),
		readSequence = useRef(0),
		focusStep = useRef(false),
		restoreTrigger = useRef(false);
	const flow = useGeometryImport({
		projectId,
		session,
		client,
		recheck,
		confirmedAssetIds,
		recoveryScopes,
		...(recoveryChecking === undefined ? {} : { recoveryChecking }),
		...(store ? { store } : {}),
	});
	const admitted = client.isCurrentScope(session.query_scope),
		frozen = flow.intent ?? recovery,
		command = frozen
			? readGeometryImportCommand(JSON.parse(frozen.body))
			: null,
		asset = flow.asset,
		choice = choices.find((item) => choiceKey(item) === selected),
		anchor = snapshot.coordinate_system.anchor,
		reference =
			anchor || choice
				? {
						schema_version: 1 as const,
						method: "wgs84_cart_topocentric_v1" as const,
						longitude_deg: anchor?.longitude_deg ?? choice!.firstPoint[0],
						latitude_deg: anchor?.latitude_deg ?? choice!.firstPoint[1],
						ellipsoid_height_m: 0,
						height_basis: "zero_height_horizontal_convention" as const,
					}
				: null;
	const aligned =
		(!snapshot.roofs.length &&
			!snapshot.arrays.length &&
			!snapshot.obstacles.length &&
			!snapshot.keepouts.length &&
			!anchor &&
			snapshot.coordinate_system.north_reference === "unreferenced") ||
		(snapshot.coordinate_system.north_reference === "true_north" &&
			anchor !== null);
	useEffect(() => {
		onActivity(open);
		return () => onActivity(false);
	}, [open, onActivity]);
	useEffect(
		() => () => {
			readSequence.current++;
		},
		[],
	);
	useEffect(() => {
		if (!focusStep.current || !open || flow.busy) return;
		focusStep.current = false;
		revealActionResult(heading.current, () =>
			client.isCurrentScope(session.query_scope),
		);
	}, [open, step, asset, flow.busy, flow.error, client, session.query_scope]);
	useEffect(() => {
		if (
			restoreTrigger.current &&
			!open &&
			!flow.busy &&
			!flow.checking &&
			!disabled &&
			!recoveryChecking &&
			admitted
		) {
			trigger.current?.focus();
			if (document.activeElement === trigger.current)
				restoreTrigger.current = false;
		}
	}, [open, flow.busy, flow.checking, disabled, recoveryChecking, admitted]);
	function move(next: number) {
		focusStep.current = true;
		setStep(next);
	}
	function start(record: GeometryImportIntent | null = null) {
		if (disabled || flow.busy || !admitted) return;
		flow.dismiss();
		setSnapshot(geometry);
		setRecovery(record);
		setContent("");
		setFilename("");
		setChoices([]);
		setSelected("");
		setRoofName("");
		setZeroHeight(false);
		setPreviousCommand(null);
		setError(null);
		setStep(0);
		focusStep.current = true;
		setOpen(true);
	}
	function close() {
		if (reading || (flow.busy && !flow.durable)) return;
		readSequence.current++;
		flow.dismiss();
		setRecovery(null);
		setContent("");
		setFilename("");
		setChoices([]);
		setError(null);
		restoreTrigger.current = true;
		setOpen(false);
	}
	async function choose(file: File | undefined) {
		if (!file || flow.busy || frozen) return;
		const sequence = ++readSequence.current;
		setReading(true);
		setContent("");
		setFilename("");
		setChoices([]);
		setSelected("");
		setError(null);
		try {
			const bytes = await fileBase64(file, policy.max_file_bytes),
				found = geoJsonChoices(bytes);
			if (
				sequence !== readSequence.current ||
				!client.isCurrentScope(session.query_scope)
			)
				return;
			setContent(bytes);
			setFilename(file.name);
			setChoices(found);
			setSelected(found.length === 1 ? choiceKey(found[0]!) : "");
			setRoofName(found.length === 1 ? (found[0]!.name ?? "") : "");
		} catch {
			if (
				sequence === readSequence.current &&
				client.isCurrentScope(session.query_scope)
			)
				setError(
					__(
						"This file could not be used. Choose a UTF-8 GeoJSON file up to 4 MiB with closed roof polygons containing only WGS 84 longitude/latitude pairs.",
						"linker-tools",
					),
				);
		} finally {
			if (sequence === readSequence.current) setReading(false);
		}
	}
	function checkStep(index: number, values: GeometryValues) {
		const section = form.current?.querySelector<HTMLElement>(
			`[data-import-step="${index}"]`,
		);
		for (const input of section?.querySelectorAll<
			HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
		>("input,textarea,select") ?? []) {
			// An explicit drawing datum replaces this height only for this run.
			// Keep its raw value and error intact if the user switches back.
			if (input.name === "height" && zeroHeight) continue;
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
				move(index);
				setError(input.validationMessage);
				window.setTimeout(() => {
					if (
						!client.isCurrentScope(session.query_scope) ||
						!input.isConnected ||
						input.closest("[hidden]")
					)
						return;
					input.reportValidity();
					revealActionResult(input);
				});
				return false;
			}
		}
		if (index === 0 && (!choice || !content)) return false;
		if (index === 1) {
			values.metric("pitch", { min: 0, maxExclusive: 90 });
			values.metric("bearing", { min: 0, maxExclusive: 360 });
			if (!zeroHeight) values.metric("height");
		}
		if (index === 2) values.number("precision", { optional: true, min: 0 });
		return true;
	}
	function fieldError(cause: unknown) {
		if (!client.isCurrentScope(session.query_scope)) return;
		if (
			cause instanceof Error &&
			"field" in cause &&
			typeof cause.field === "string"
		) {
			const input = form.current?.elements.namedItem(cause.field);
			if (input instanceof window.HTMLInputElement) {
				const section = input.closest<HTMLElement>("[data-import-step]");
				move(Number(section?.dataset.importStep ?? step));
				input.setCustomValidity(cause.message);
				input.setAttribute("aria-invalid", "true");
				window.setTimeout(() => {
					if (
						!client.isCurrentScope(session.query_scope) ||
						!input.isConnected ||
						input.closest("[hidden]")
					)
						return;
					input.reportValidity();
					revealActionResult(input);
				});
			}
			setError(cause.message);
		} else
			setError(
				__(
					"The roof preview could not be prepared. Your file and entries remain available for correction.",
					"linker-tools",
				),
			);
	}
	async function submit(event: FormEvent<HTMLFormElement>) {
		event.preventDefault();
		setError(null);
		if (reading || flow.busy || frozen || !admitted) return;
		try {
			const values = new GeometryValues(event.currentTarget, locale);
			if (!checkStep(step, values)) return;
			if (step < 2) {
				move(step + 1);
				return;
			}
			for (let index = 0; index < 3; index++)
				if (!checkStep(index, values)) return;
			if (!choice || !reference || !aligned) return;
			const request: GeometryImportCommand = {
				schema_version: 1,
				project_id: projectId,
				content_base64: content,
				key: crypto.randomUUID(),
				options: {
					schema_version: 1,
					format: "geojson_wgs84_horizontal_v1",
					plane_intersection_method: "geodetic_vertical_line_v1",
					feature_index: choice.featureIndex,
					polygon_index: choice.polygonIndex,
					roof_name: roofName.trim(),
					reference,
					plane: {
						...roofPlaneAtVertex(
							reference,
							choice.firstPoint,
							values.metric("pitch", { min: 0, maxExclusive: 90 }),
							values.metric("bearing", { min: 0, maxExclusive: 360 }),
							zeroHeight ? 0 : values.metric("height"),
						),
						basis_note: values.text("basis"),
					},
					source: {
						label: values.text("source"),
						rights_note: values.text("rights"),
						spatial_precision_m: values.number("precision", {
							optional: true,
							min: 0,
						}),
						export_permission: values.text("export") as
							"unknown" | "permitted" | "prohibited",
					},
				},
			};
			focusStep.current = true;
			await flow.prepare(request);
		} catch (cause) {
			fieldError(cause);
		}
	}
	if (!admitted) return null;
	const stepNames = [
		__("File and roof", "linker-tools"),
		__("Roof plane", "linker-tools"),
		__("Source", "linker-tools"),
	];
	return (
		<div className="lp-geometry-intake">
			<div className="lp-inline-actions">
				<button
					type="button"
					className="lp-button lp-button-secondary"
					ref={trigger}
					disabled={
						disabled || open || flow.busy || flow.checking || recoveryChecking
					}
					onClick={() => start()}
				>
					{__("Import roof geometry", "linker-tools")}
				</button>
				{applied && currentAssetIds.includes(applied) && (
					<span role="status">
						{confirmedAssetIds.includes(applied)
							? __(
									"The roof import is included in the saved project.",
									"linker-tools",
								)
							: __(
									"Imported roof is in the current design. Save the project to record it.",
									"linker-tools",
								)}
					</span>
				)}
			</div>
			{flow.storageFailed && (
				<Notice error>
					{__(
						"Browser recovery could not be read or updated. An upload starts only after a recovery copy of its original file and settings is saved. Project versions already saved on the server are unchanged.",
						"linker-tools",
					)}
				</Notice>
			)}
			{!open && flow.records.length > 0 && (
				<details className="lp-comparison">
					<summary>{__("Imports to review", "linker-tools")}</summary>
					<p>
						{__(
							"Review an earlier upload before retrying it or adding its roof to this project.",
							"linker-tools",
						)}
					</p>
					{flow.records.map((record) => (
						<button
							type="button"
							className="lp-text-button"
							key={record.scope + record.key}
							disabled={disabled}
							onClick={() => start(record)}
						>
							{record.label}
						</button>
					))}
				</details>
			)}
			{open && (
				<div className="lp-import-panel">
					<div className="lp-section-heading">
						<div>
							<h3 ref={heading} tabIndex={-1}>
								{asset
									? __("Review imported roof", "linker-tools")
									: recovery
										? __("Review an earlier upload", "linker-tools")
										: stepNames[step]}
							</h3>
							<p>
								{__(
									"Preview the roof outline and its openings, then add it to your design. Importing a drawing does not verify site dimensions or engineering compliance.",
									"linker-tools",
								)}
							</p>
						</div>
					</div>
					{error && <Notice error>{error}</Notice>}
					{!!flow.error && (
						<Notice error>
							{isPreMutationInputRefusal(flow.error)
								? __(
										"The file or roof settings could not be accepted. Your file and entries are still available. Check the file format and roof settings, then try again.",
										"linker-tools",
									)
								: __(
										"The upload has not been confirmed. Retry uses the same original file and settings; your current design is kept.",
										"linker-tools",
									)}
						</Notice>
					)}
					{(command ?? previousCommand) && (
						<GeometryImportSettings
							command={(command ?? previousCommand)!}
							locale={locale}
						/>
					)}
					{frozen && !asset && (
						<div className="lp-inline-actions">
							<button
								type="button"
								className="lp-button"
								disabled={flow.busy}
								onClick={() => {
									focusStep.current = true;
									void flow.retry(frozen);
								}}
							>
								{flow.busy
									? __("Preparing preview…", "linker-tools")
									: __("Check or retry this upload", "linker-tools")}
							</button>
							{!!flow.error &&
								isPreMutationInputRefusal(flow.error) &&
								recovery && (
									<button
										type="button"
										className="lp-button lp-button-secondary"
										onClick={() => {
											try {
												const original = readGeometryImportCommand(
														JSON.parse(recovery.body),
													),
													found = geoJsonChoices(original.content_base64);
												setPreviousCommand(original);
												setContent(original.content_base64);
												setFilename(
													__("Retained original file", "linker-tools"),
												);
												setChoices(found);
												setSelected(
													`${original.options.feature_index}:${original.options.polygon_index}`,
												);
												setRoofName(original.options.roof_name);
												setRecovery(null);
												flow.dismiss();
												move(0);
											} catch (cause) {
												fieldError(cause);
											}
										}}
									>
										{__("Correct this import", "linker-tools")}
									</button>
								)}
						</div>
					)}
					{
						<form
							key={previousCommand?.key ?? "new"}
							hidden={!!frozen || !!asset}
							ref={form}
							noValidate
							onSubmit={(event) => {
								void submit(event);
							}}
							onInput={(event) => {
								setError(null);
								const input = event.target;
								if (
									input instanceof window.HTMLInputElement ||
									input instanceof window.HTMLTextAreaElement ||
									input instanceof window.HTMLSelectElement
								) {
									input.setCustomValidity("");
									input.removeAttribute("aria-invalid");
								}
							}}
						>
							<ol
								className="lp-import-steps"
								aria-label={__("Import progress", "linker-tools")}
							>
								{stepNames.map((name, index) => (
									<li
										key={name}
										aria-current={step === index ? "step" : undefined}
									>
										<span>{index + 1}</span>
										{name}
									</li>
								))}
							</ol>
							{!aligned && (
								<Notice error>
									{__(
										"The existing design needs a geographic origin and a source reference for true north before another roof can be imported. Close this import and open Project coordinate references. These settings do not rotate or move existing objects; the design must already match the references.",
										"linker-tools",
									)}
								</Notice>
							)}
							<fieldset disabled={reading || flow.busy || !!frozen || !aligned}>
								<div hidden={step !== 0}>
									<label className="lp-field">
										<span id={id + "-file"}>
											{__("Roof file", "linker-tools")}
										</span>
										<div className="lp-file-picker">
											<span className="lp-file-button" aria-hidden="true">
												{__("Choose file", "linker-tools")}
											</span>
											<span
												className="lp-file-name"
												id={id + "-file-name"}
												aria-live="polite"
											>
												{filename || __("No file selected", "linker-tools")}
											</span>
											<input
												type="file"
												aria-labelledby={id + "-file"}
												aria-describedby={
													id + "-file-name " + id + "-file-hint"
												}
												accept=".geojson,.json,application/geo+json,application/json"
												onChange={(event) => {
													void choose(event.currentTarget.files?.[0]);
												}}
											/>
										</div>
										<small id={id + "-file-hint"}>
											{__("WGS 84 GeoJSON · up to 4 MiB", "linker-tools")}
										</small>
									</label>
								</div>
								<GeometryImportFields
									original={previousCommand?.options}
									step={step}
									choices={choices}
									selected={selected}
									select={(key) => {
										setSelected(key);
										const choice = choices.find(
											(choice) => choiceKey(choice) === key,
										);
										if (!roofName) setRoofName(choice?.name ?? "");
									}}
									roofName={roofName}
									setRoofName={setRoofName}
									reference={reference}
									locale={locale}
									zeroHeight={zeroHeight}
									setZeroHeight={setZeroHeight}
								/>
								<div className="lp-inline-actions">
									{step > 0 && (
										<button
											type="button"
											className="lp-button lp-button-secondary"
											onClick={() => {
												setError(null);
												move(step - 1);
											}}
										>
											{__("Back", "linker-tools")}
										</button>
									)}
									<button
										type="submit"
										className="lp-button"
										disabled={!content || reading || flow.busy}
									>
										{step < 2
											? __("Continue", "linker-tools")
											: __("Prepare roof preview", "linker-tools")}
									</button>
								</div>
							</fieldset>
						</form>
					}
					{asset && (
						<div className="lp-import-review">
							<PlanViewport
								document={asset.geometry}
								roof={asset.geometry.roofs[0]!}
								poses={[]}
								selected={null}
								select={() => {}}
								commit={() => false}
								disabled
								previewOnly
							/>
							<dl className="lp-field-summary">
								<div>
									<dt>{__("Roof-plane area", "linker-tools")}</dt>
									<dd>
										{/* Display policy only: two fractional digits do not
										    establish the source's survey precision. */}
										{new Intl.NumberFormat(locale, {
											maximumFractionDigits: 2,
										}).format(asset.areaM2)}{" "}
										m²
									</dd>
								</div>
								<div>
									<dt>{__("Openings retained", "linker-tools")}</dt>
									<dd>{asset.geometry.roofs[0]!.holes_uv.length}</dd>
								</div>
							</dl>
							<button
								type="button"
								className="lp-button"
								disabled={flow.busy || currentAssetIds.includes(asset.id)}
								onClick={() => {
									if (!client.isCurrentScope(session.query_scope)) return;
									if (attach(snapshot, asset)) {
										setApplied(asset.id);
										close();
									} else
										setError(
											__(
												"The design or coordinate reference has changed. Your imported source is retained; review it against the current project before adding it.",
												"linker-tools",
											),
										);
								}}
							>
								{__("Add roof to current design", "linker-tools")}
							</button>
							<p className="lp-profile-help">
								{__(
									"One editable roof face is added as a single step in project history. Save the project to record the addition. You can undo this addition in the open design.",
									"linker-tools",
								)}
							</p>
						</div>
					)}
					<div className="lp-inline-actions">
						<button
							type="button"
							className="lp-button lp-button-secondary"
							disabled={reading || (flow.busy && !flow.durable)}
							onClick={close}
						>
							{__("Close import", "linker-tools")}
						</button>
					</div>
				</div>
			)}
		</div>
	);
}
