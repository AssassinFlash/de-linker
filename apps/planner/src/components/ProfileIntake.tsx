import { FileDropzone } from "./FileDropzone.tsx";
import { useCallback, useEffect, useId, useRef, useState } from "react";
import { isPreMutationInputRefusal } from "../data/inputRefusal.ts";
import type { PlannerClient } from "../data/PlannerClient.ts";
import type { DraftStore } from "../data/DraftStore.ts";
import { profileIntents, intentId } from "../data/recoveryIntents.ts";
import type { ScopedProfileImport } from "../data/recoveryIntents.ts";
import type { Session } from "../data/protocol.ts";
import { ApiError } from "../data/protocol.ts";
import { wire } from "../data/readProtocol.ts";
import {
	fileBase64,
	readAsset,
	readImport,
	readProfileImport,
	isStandardProfile,
	readInspection,
} from "../domain/profiles.ts";
import type {
	CsvInspection,
	Measurement,
	ProfileAsset,
	ProfilePreview,
} from "../domain/profiles.ts";
import { __, sprintf } from "../i18n.ts";
import {
	emptyMapping,
	mappedProfile,
	ProfileMapping,
} from "./ProfileMapping.tsx";
import { Notice } from "./Notice.tsx";
import { OwnedProfile } from "./OwnedProfile.tsx";
import { ProfileError } from "./ProfileError.tsx";
import { ProfileImportSettings } from "./ProfileImportSettings.tsx";
import { ScenarioNumber } from "./energy/ScenarioNumber.tsx";
import { revealActionResult } from "./revealActionResult.ts";

export function ProfileIntake({
	projectId,
	session,
	client,
	store,
	locale,
	timezone,
	annualKwh = null,
	recheck,
	attach,
	registerGuard,
	confirmedAssetIds = [],
	currentAssetIds = [],
	recoveryScopes,
	recoveryChecking = false,
}: {
	projectId: string;
	session: Session;
	client: PlannerClient;
	store: DraftStore;
	locale: string;
	timezone: string | null;
	annualKwh?: number | null;
	recheck: () => void;
	attach: (assetId: string, role: Measurement) => Promise<boolean>;
	registerGuard: (guard: () => boolean) => void;
	confirmedAssetIds?: readonly string[];
	currentAssetIds: readonly string[];
	recoveryScopes?: readonly string[] | undefined;
	recoveryChecking?: boolean;
}) {
	const id = useId();
	const [standard, setStandard] = useState(false);
	const [annual, setAnnual] = useState<number | null>(annualKwh);
	const [year, setYear] = useState<number | null>(new Date().getFullYear());
	const [pattern, setPattern] = useState("H0");
	const [standardZone, setStandardZone] = useState(timezone ?? "");
	const [invalidStandard, setInvalidStandard] = useState<ReadonlySet<string>>(
		new Set(),
	);
	const reportStandard = useCallback(
		(field: string, valid: boolean) =>
			setInvalidStandard((previous) => {
				const next = new Set(previous);
				if (valid) next.delete(field);
				else next.add(field);
				return next;
			}),
		[],
	);
	const standardValid =
		annual !== null &&
		annual > 0 &&
		year !== null &&
		standardZone.trim() !== "" &&
		invalidStandard.size === 0;
	const fileInput = useRef<HTMLInputElement>(null);
	const [fileName, setFileName] = useState("");
	const [readingFile, setReadingFile] = useState(false);
	const [open, setOpen] = useState(false),
		[busy, setBusy] = useState(false),
		[checking, setChecking] = useState(true);
	const [content, setContent] = useState(""),
		[delimiter, setDelimiter] = useState("");
	const [inspection, setInspection] = useState<CsvInspection | null>(null);
	const [fields, setFields] = useState(() => emptyMapping(timezone));
	const [numberValid, setNumberValid] = useState(true);
	const [label, setLabel] = useState(""),
		[rights, setRights] = useState("");
	const [error, setError] = useState<unknown>(null),
		[recoveryFailed, setRecoveryFailed] = useState(false),
		[closeBlocked, setCloseBlocked] = useState(false);
	const [requests, setRequests] = useState<readonly ScopedProfileImport[]>([]),
		[pending, setPending] = useState<string | null>(null);
	const [asset, setAsset] = useState<ProfileAsset | null>(null),
		[durable, setDurable] = useState(false);
	const pendingScope = useRef(session.query_scope);
	const [selected, setSelected] = useState<string | null>(null);
	const importTrigger = useRef<HTMLButtonElement>(null);
	const selectionNotice = useRef<HTMLDivElement>(null);
	const feedback = useRef<"selection" | "cancel" | null>(null);
	const selectedInDraft =
		selected !== null && currentAssetIds.includes(selected);
	const canReveal = useCallback(
		() => client.isCurrentScope(session.query_scope),
		[client, session.query_scope],
	);
	const admitted = canReveal();
	const openWork = useRef(false);
	openWork.current = Boolean(
		pending || content || readingFile || label || rights || (open && standard),
	);
	const lifetime = useRef(0),
		flight = useRef(false),
		form = useRef<HTMLDivElement>(null);
	const numberValidity = useCallback(
		(valid: boolean) => setNumberValid(valid),
		[],
	);
	const current = (instance: number) =>
		instance === lifetime.current && client.isCurrentScope(session.query_scope);
	useEffect(() => {
		if (
			open ||
			!feedback.current ||
			!client.isCurrentScope(session.query_scope)
		)
			return;
		const target =
			feedback.current === "selection" && selectedInDraft
				? selectionNotice.current
				: importTrigger.current;
		if (revealActionResult(target, canReveal)) feedback.current = null;
	}, [
		open,
		selected,
		selectedInDraft,
		client,
		session.query_scope,
		canReveal,
		admitted,
	]);
	function restore(body: string, scope: string) {
		pendingScope.current = scope;
		const command = readProfileImport(JSON.parse(body));
		if (isStandardProfile(command)) {
			setStandard(true);
			setAnnual(command.annual_kwh);
			setYear(command.year);
			setPattern(command.profile);
			setStandardZone(command.timezone);
			if (command.project_id !== projectId)
				throw new Error("wrong_profile_project");
			setPending(body);
			setContent("");
			setAsset(null);
			setDurable(true);
			setOpen(true);
			return;
		}
		if (command.project_id !== projectId)
			throw new Error("wrong_profile_project");
		setStandard(false);
		setPending(body);
		setContent(command.content_base64);
		setFileName("");
		setDelimiter(command.mapping.delimiter);
		setLabel(command.source_label);
		setRights(command.rights_note);
		setAsset(null);
		setInspection(null);
		setDurable(true);
		setOpen(true);
		const m = command.mapping;
		setFields({
			timestamp: m.timestamp_column,
			value: m.value_column,
			measurement: m.measurement,
			unit: m.value_kind,
			timeRole: m.timestamp_role,
			timezone: m.timezone,
			origin: m.origin,
			durationMode: m.end_timestamp_column ? "ends" : "fixed",
			minutes: m.interval_seconds === null ? null : m.interval_seconds / 60,
			end: m.end_timestamp_column ?? "",
			fold: m.fold_column ?? "",
			endFold: m.end_fold_column ?? "",
			decimal: m.decimal,
		});
	}
	useEffect(() => {
		lifetime.current++;
		return () => {
			lifetime.current++;
		};
	}, [projectId, session.query_scope]);
	useEffect(() => {
		if (recoveryChecking || !admitted) return;
		const instance = lifetime.current;
		let active = true;
		setChecking(true);
		void profileIntents(
			store,
			recoveryScopes ?? [session.query_scope],
			projectId,
		)
			.then((records) => {
				if (
					!active ||
					instance !== lifetime.current ||
					!client.isCurrentScope(session.query_scope)
				)
					return;
				setRequests(records);
				if (!openWork.current && records[0])
					restore(records[0].body, records[0].scope);
			})
			.catch(() => {
				if (active && instance === lifetime.current) setRecoveryFailed(true);
			})
			.finally(() => {
				if (active && instance === lifetime.current) setChecking(false);
			});
		return () => {
			active = false;
		};
	}, [
		admitted,
		client,
		projectId,
		session.query_scope,
		store,
		recoveryScopes,
		recoveryChecking,
	]);
	const serverRecorded = asset !== null && confirmedAssetIds.includes(asset.id);
	const unprotected =
		(Boolean(content) || readingFile || (open && standard)) &&
		!durable &&
		!serverRecorded;
	useEffect(() => {
		if (
			!serverRecorded ||
			!asset ||
			!pending ||
			!client.isCurrentScope(session.query_scope)
		)
			return;
		// The owned import receipt and the server-confirmed project baseline
		// now protect this selection independently of browser recovery storage.
		const body = pending,
			originScope = pendingScope.current,
			instance = lifetime.current;
		setSelected(asset.id);
		setRequests((previous) =>
			previous.filter(
				(request) => request.body !== body || request.scope !== originScope,
			),
		);
		setPending(null);
		setContent("");
		setFileName("");
		setInspection(null);
		setAsset(null);
		setDurable(false);
		feedback.current = "selection";
		setOpen(false);
		void store.clearProfileImport(originScope, body).catch(() => {
			if (
				instance === lifetime.current &&
				client.isCurrentScope(session.query_scope)
			)
				setRecoveryFailed(true);
		});
	}, [serverRecorded, asset, pending, client, session.query_scope, store]);
	useEffect(() => {
		registerGuard(() => {
			if (!unprotected) return true;
			setCloseBlocked(true);
			form.current
				?.querySelector<HTMLElement>(
					"button:not(:disabled),input:not(:disabled)",
				)
				?.focus();
			return false;
		});
		return () => registerGuard(() => true);
	}, [registerGuard, unprotected]);
	useEffect(() => {
		if (!unprotected) return;
		const guard = (event: BeforeUnloadEvent) => {
			event.preventDefault();
			event.returnValue = "";
		};
		window.addEventListener("beforeunload", guard);
		return () => window.removeEventListener("beforeunload", guard);
	}, [unprotected]);
	function failure(cause: unknown, instance: number) {
		if (instance !== lifetime.current) return;
		if (
			cause instanceof ApiError &&
			([401, 403].includes(cause.status) || cause.code === "session_changed")
		) {
			recheck();
			return;
		}
		if (current(instance)) setError(cause);
	}
	async function chooseFile(file: File | undefined) {
		if (!file || flight.current) return;
		const instance = lifetime.current;
		flight.current = true;
		setBusy(true);
		setReadingFile(true);
		setError(null);
		setContent("");
		setFileName("");
		setInspection(null);
		setFields(emptyMapping(timezone));
		setLabel("");
		setRights("");
		setDurable(false);
		setAsset(null);
		try {
			const encoded = await fileBase64(
				file,
				session.runtime.limits.max_csv_bytes,
			);
			if (instance !== lifetime.current) return;
			setContent(encoded);
			setFileName(file.name);
			setInspection(null);
			setFields(emptyMapping(timezone));
			setDurable(false);
			setAsset(null);
		} catch (cause) {
			if (fileInput.current) fileInput.current.value = "";
			failure(cause, instance);
		} finally {
			if (instance === lifetime.current) {
				flight.current = false;
				setReadingFile(false);
				setBusy(false);
			}
		}
	}
	async function inspect() {
		if (!content || !delimiter || flight.current) return;
		const instance = lifetime.current;
		flight.current = true;
		setBusy(true);
		setError(null);
		try {
			const result = readInspection(
				await client.query(
					"profiles/inspect",
					{
						schema_version: 1,
						project_id: projectId,
						content_base64: content,
						delimiter,
						page_size: Math.min(10, session.runtime.limits.max_page_size),
					},
					session.query_scope,
				),
				delimiter,
			);
			if (current(instance)) setInspection(result);
		} catch (cause) {
			failure(cause, instance);
		} finally {
			if (instance === lifetime.current) {
				flight.current = false;
				setBusy(false);
			}
		}
	}
	async function importSource() {
		if (flight.current) return;
		const mapping = mappedProfile(fields, delimiter);
		if (
			!pending &&
			(standard
				? !standardValid
				: !inspection ||
					!mapping ||
					(fields.durationMode === "fixed" && !numberValid) ||
					!label.trim() ||
					!rights.trim())
		)
			return;
		const instance = lifetime.current;
		flight.current = true;
		setBusy(true);
		setError(null);
		let body = pending;
		if (!body) pendingScope.current = session.query_scope;
		const originScope = pendingScope.current;
		try {
			body ??= wire(
				readProfileImport(
					standard
						? {
								schema_version: 1,
								project_id: projectId,
								edition: pattern.endsWith("25") ? 2025 : 1999,
								profile: pattern,
								year,
								annual_kwh: annual,
								timezone: standardZone.trim(),
								key: crypto.randomUUID(),
							}
						: {
								schema_version: 1,
								project_id: projectId,
								content_base64: content,
								mapping,
								source_label: label.trim(),
								rights_note: rights.trim(),
								key: crypto.randomUUID(),
							},
				),
				session.runtime.limits.max_json_depth,
				session.runtime.limits.max_body_bytes,
			);
			setPending(body);
			try {
				await store.writeProfileImport(originScope, body);
				if (instance === lifetime.current) setDurable(true);
			} catch {
				if (instance === lifetime.current) setRecoveryFailed(true);
			}
			if (!current(instance)) return;
			const confirmed = readAsset(
				await client.send(
					isStandardProfile(readProfileImport(JSON.parse(body)))
						? "profiles/standard"
						: "profiles/csv",
					body,
					session.query_scope,
				),
				projectId,
			);
			if (current(instance)) setAsset(confirmed);
		} catch (cause) {
			failure(cause, instance);
			// A typed input refusal guarantees no asset publication. An unknown
			// acknowledgement or transient failure retains the exact wire/key.
			if (body && current(instance) && isPreMutationInputRefusal(cause)) {
				// A definitive pre-publication refusal makes this editable input,
				// even if the browser cannot clean up its older recovery record.
				// Revoke the durable admission before awaiting that cleanup.
				setPending(null);
				setDurable(false);
				const refusedBody = body;
				setRequests((previous) =>
					previous.filter(
						(request) =>
							request.body !== refusedBody || request.scope !== originScope,
					),
				);
				try {
					await store.clearProfileImport(originScope, body);
				} catch {
					if (current(instance)) setRecoveryFailed(true);
				}
			}
		} finally {
			if (instance === lifetime.current) {
				flight.current = false;
				setBusy(false);
			}
		}
	}
	async function select(confirmed: ProfileAsset, preview: ProfilePreview) {
		if (flight.current || !pending) return;
		const instance = lifetime.current;
		flight.current = true;
		setBusy(true);
		try {
			if (
				!current(instance) ||
				!(await attach(confirmed.id, preview.measurement)) ||
				!current(instance)
			)
				return;
			setSelected(confirmed.id);
			await store.clearProfileImport(pendingScope.current, pending);
			if (!current(instance)) return;
			const remaining = await profileIntents(
				store,
				recoveryScopes ?? [session.query_scope],
				projectId,
			);
			// Only finish this component's already-persisted local operation.
			// Native verification may hide it between the final read and this
			// continuation. No server mutation/navigation/cache write occurs here;
			// feedback still waits for live admission, and another scope unmounts
			// this editor. Refusing local completion would strand the user until
			// another click after a same-scope verification.
			if (instance !== lifetime.current) return;
			setRequests(remaining);
			setPending(null);
			setContent("");
			setFileName("");
			setInspection(null);
			setAsset(null);
			setLabel("");
			setRights("");
			setFields(emptyMapping(timezone));
			setDurable(false);
			feedback.current = "selection";
			setOpen(false);
		} catch (cause) {
			failure(cause, instance);
			if (current(instance)) setRecoveryFailed(true);
		} finally {
			if (instance === lifetime.current) {
				flight.current = false;
				setBusy(false);
			}
		}
	}
	const selectedRequest = requests.find(
		(request) =>
			request.body === pending && request.scope === pendingScope.current,
	);
	if (!open)
		return (
			<>
				{selected && selectedInDraft && (
					<div ref={selectionNotice} tabIndex={-1} className="sc-focus-target">
						<Notice>
							{confirmedAssetIds.includes(selected)
								? __(
										"This profile selection is saved with the project.",
										"linker-tools",
									)
								: __(
										"The profile is selected in the open draft. Save the project to record this selection.",
										"linker-tools",
									)}
						</Notice>
					</div>
				)}
				<button
					ref={importTrigger}
					className="sc-button sc-focus-target"
					type="button"
					disabled={checking || recoveryChecking}
					onClick={() => {
						setStandard(false);
						setOpen(true);
					}}
				>
					{__("Import interval data", "linker-tools")}
				</button>
				<button
					className="sc-button"
					type="button"
					disabled={checking || recoveryChecking}
					onClick={() => {
						setAnnual(annualKwh);
						setStandardZone(timezone ?? "");
						setStandard(true);
						setOpen(true);
					}}
				>
					{__("Use a typical load profile", "linker-tools")}
				</button>
			</>
		);
	return (
		<div className="sc-profile-intake" ref={form}>
			{requests.length > 0 && (
				<label className="sc-field">
					<span id={id + "-requests"}>
						{__("Imports to review", "linker-tools")}
					</span>
					<select
						aria-labelledby={id + "-requests"}
						disabled={busy || unprotected}
						value={selectedRequest ? intentId(selectedRequest) : ""}
						onChange={(event) => {
							const request = requests.find(
								(item) => intentId(item) === event.currentTarget.value,
							);
							if (request) restore(request.body, request.scope);
						}}
					>
						<option value="" disabled>
							{__("Select…", "linker-tools")}
						</option>
						{requests.map((request) => (
							<option key={intentId(request)} value={intentId(request)}>
								{request.label}
							</option>
						))}
					</select>
				</label>
			)}
			{closeBlocked && unprotected && (
				<Notice error>
					{__(
						"Finish importing or cancel the open file before leaving this project.",
						"linker-tools",
					)}
				</Notice>
			)}
			{recoveryFailed && (
				<Notice error>
					{__(
						"Browser recovery could not be stored or read. The open import may be lost if this page closes. After selecting the profile, the project still needs to be saved.",
						"linker-tools",
					)}
				</Notice>
			)}
			<ProfileError error={error} focus={admitted} canReveal={canReveal} />
			{pending ? (
				<>
					<p>
						{asset
							? __(
									"The source is stored. Review its interpretation before selecting it in the open draft.",
									"linker-tools",
								)
							: __(
									"The import result is not confirmed. Retrying uses the original file, mapping and request key.",
									"linker-tools",
								)}
					</p>
					<details className="sc-disclosure">
						<summary>{__("Original import settings", "linker-tools")}</summary>
						{isStandardProfile(readProfileImport(JSON.parse(pending))) ? (
							<p>
								{__("BDEW/VDEW template · German calendar", "linker-tools")}{" "}
								{`BDEW ${JSON.parse(pending).edition} · ${JSON.parse(pending).profile} · ${JSON.parse(pending).year} · ${new Intl.NumberFormat(locale).format(JSON.parse(pending).annual_kwh)} kWh · ${JSON.parse(pending).timezone}`}
							</p>
						) : (
							<ProfileImportSettings
								command={readImport(JSON.parse(pending))}
								locale={locale}
							/>
						)}
					</details>
					{!asset && (
						<button
							className="sc-button sc-primary"
							type="button"
							disabled={busy}
							onClick={() => {
								void importSource();
							}}
						>
							{__("Check or retry this import", "linker-tools")}
						</button>
					)}
				</>
			) : (
				<>
					{standard ? (
						<fieldset disabled={busy} className="sc-brief-fields">
							<h3>
								{__("Annual consumption and daily pattern", "linker-tools")}
							</h3>
							<p>
								{__(
									"BDEW/VDEW standard profiles use a German calendar. For other European sites, use them as an explicit template or import local meter data. The preview shows the actual annual total and time zone.",
									"linker-tools",
								)}
							</p>
							<div className="grid gap-5 md:grid-cols-2">
								<ScenarioNumber
									field="annual"
									label={__("Annual consumption", "linker-tools")}
									value={annual}
									unit="kWh"
									locale={locale}
									onChange={setAnnual}
									report={reportStandard}
								/>
								<ScenarioNumber
									field="year"
									label={__("Profile year", "linker-tools")}
									value={year}
									unit=""
									locale={locale}
									min={2000}
									max={2100}
									integer
									onChange={setYear}
									report={reportStandard}
								/>
								<label className="sc-field">
									<span>{__("Typical usage pattern", "linker-tools")}</span>
									<select
										value={pattern}
										onChange={(e) => setPattern(e.currentTarget.value)}
									>
										<option value="H0">
											{__("Household · H0", "linker-tools")}
										</option>
										<option value="G0">
											{__("General business · G0", "linker-tools")}
										</option>
										<option value="G1">
											{__("Business on weekdays · G1", "linker-tools")}
										</option>
										<option value="G2">
											{__("Evening business · G2", "linker-tools")}
										</option>
										<option value="G3">
											{__("Continuous operation · G3", "linker-tools")}
										</option>
										<option value="G4">
											{__("Retail · G4", "linker-tools")}
										</option>
										<option value="G5">
											{__("Bakery · G5", "linker-tools")}
										</option>
										<option value="G6">
											{__("Weekend business · G6", "linker-tools")}
										</option>
										<option value="H25">
											{__("Household · H25 (2025)", "linker-tools")}
										</option>
										<option value="G25">
											{__("Business · G25 (2025)", "linker-tools")}
										</option>
										<option value="L25">
											{__("Agriculture · L25 (2025)", "linker-tools")}
										</option>
									</select>
								</label>
								<label className="sc-field">
									<span>{__("Time zone", "linker-tools")}</span>
									<input
										value={standardZone}
										onChange={(e) => setStandardZone(e.currentTarget.value)}
										placeholder="Europe/Berlin"
									/>
								</label>
							</div>
							<div className="sc-actions">
								<button
									type="button"
									className="sc-button sc-primary"
									disabled={!standardValid}
									onClick={() => void importSource()}
								>
									{__("Create and review load profile", "linker-tools")}
								</button>
								<button
									type="button"
									className="sc-text-button"
									onClick={() => {
										feedback.current = "cancel";
										setOpen(false);
										setStandard(false);
										setError(null);
										setCloseBlocked(false);
									}}
								>
									{__("Cancel", "linker-tools")}
								</button>
							</div>
						</fieldset>
					) : (
						<>
							<fieldset disabled={busy} className="sc-brief-fields">
								<h3>{__("1 · Preview source columns", "linker-tools")}</h3>
								<p>
									{__(
										"CSV files need UTF-8 encoding and unique column headers. Preview sends the file for a private structure check without saving a project data source.",
										"linker-tools",
									)}
								</p>
								<div className="grid gap-5 md:grid-cols-2">
									<FileDropzone
										label={__("Source file", "linker-tools")}
										action={__("Choose CSV file", "linker-tools")}
										accept=".csv,.txt,text/csv,text/plain"
										filename={
											fileName ||
											(content
												? __("Recovered source file", "linker-tools")
												: "")
										}
										inputRef={fileInput}
										onFile={(file) => void chooseFile(file)}
									/>
									<label className="sc-field">
										<span id={id + "-delimiter"}>
											{__("Column delimiter", "linker-tools")}
										</span>
										<select
											aria-labelledby={id + "-delimiter"}
											value={delimiter}
											onChange={(event) => {
												setDelimiter(event.currentTarget.value);
												setInspection(null);
												setFields((previous) => ({
													...previous,
													timestamp: "",
													value: "",
													end: "",
													fold: "",
													endFold: "",
												}));
											}}
										>
											<option value="">{__("Select…", "linker-tools")}</option>
											<option value=";">
												{__("Semicolon", "linker-tools")}
											</option>
											<option value=",">{__("Comma", "linker-tools")}</option>
											<option value={"\t"}>{__("Tab", "linker-tools")}</option>
											<option value="|">
												{__("Vertical bar", "linker-tools")}
											</option>
										</select>
									</label>
								</div>
								<div className="sc-actions">
									<button
										className="sc-button"
										type="button"
										disabled={!content || !delimiter}
										onClick={() => {
											void inspect();
										}}
									>
										{__("Preview columns", "linker-tools")}
									</button>
									<button
										className="sc-text-button"
										type="button"
										onClick={() => {
											feedback.current = "cancel";
											setContent("");
											setFileName("");
											setInspection(null);
											setOpen(false);
											setError(null);
											setCloseBlocked(false);
										}}
									>
										{__("Cancel", "linker-tools")}
									</button>
								</div>
							</fieldset>
							{inspection && (
								<>
									<div
										className="sc-table-scroll"
										role="region"
										aria-label={__("Original file preview", "linker-tools")}
										tabIndex={0}
									>
										<table className="sc-data-table">
											<caption>
												{__("Original cells · preview only", "linker-tools")}
											</caption>
											<thead>
												<tr>
													<th scope="col">
														{__("Starting file line", "linker-tools")}
													</th>
													{inspection.columns.map((column, index) => (
														<th key={index} scope="col">
															{column}
														</th>
													))}
												</tr>
											</thead>
											<tbody>
												{inspection.rows.map((row) => (
													<tr key={row.line}>
														<th scope="row">{row.line}</th>
														{row.cells.map((cell, index) => (
															<td key={index}>{cell}</td>
														))}
													</tr>
												))}
											</tbody>
										</table>
									</div>
									<p>
										{sprintf(
											__(
												"Data records: %s. Timestamps, units and values are checked after mapping.",
												"linker-tools",
											),
											new Intl.NumberFormat(locale).format(
												inspection.record_count,
											),
										)}
									</p>
									<form
										onSubmit={(event) => {
											event.preventDefault();
											void importSource();
										}}
									>
										<fieldset disabled={busy} className="sc-brief-fields">
											<h3>
												{__("2 · Define values and source", "linker-tools")}
											</h3>
											<ProfileMapping
												columns={inspection.columns}
												fields={fields}
												locale={locale}
												onChange={setFields}
												onValidity={numberValidity}
											/>
											<div className="grid gap-5 md:grid-cols-2">
												<label className="sc-field">
													<span id={id + "-source-label"}>
														{__("Source label", "linker-tools")}
													</span>
													<input
														aria-labelledby={id + "-source-label"}
														aria-describedby={id + "-source-help"}
														required
														maxLength={256}
														value={label}
														onChange={(event) =>
															setLabel(event.currentTarget.value)
														}
													/>
													<small id={id + "-source-help"}>
														{__(
															"This name identifies the source in the project. The original file name is not stored.",
															"linker-tools",
														)}
													</small>
												</label>
												<label className="sc-field">
													<span id={id + "-rights"}>
														{__(
															"Source and permission for permanent private storage",
															"linker-tools",
														)}
													</span>
													<textarea
														aria-labelledby={id + "-rights"}
														aria-describedby={id + "-rights-help"}
														required
														rows={3}
														maxLength={4096}
														value={rights}
														onChange={(event) =>
															setRights(event.currentTarget.value)
														}
													/>
													<small id={id + "-rights-help"}>
														{__(
															"This records where the data came from and your permission to store it permanently with this private project. Examples include your own meter export or data you are authorised to retain.",
															"linker-tools",
														)}
													</small>
												</label>
											</div>
											<p className="sc-field-help">
												{__(
													"Each mapped column must be different and interval durations must be positive. The original file and gaps are preserved.",
													"linker-tools",
												)}
											</p>
											<p className="sc-field-help">
												{__(
													"Import stores the original file and these settings as a private project source. Selecting a profile and saving the project are separate steps.",
													"linker-tools",
												)}
											</p>
											<button
												className="sc-button sc-primary"
												disabled={
													!mappedProfile(fields, delimiter) ||
													(fields.durationMode === "fixed" && !numberValid) ||
													!label.trim() ||
													!rights.trim()
												}
											>
												{__("Import and review data", "linker-tools")}
											</button>
										</fieldset>
									</form>
								</>
							)}
						</>
					)}
				</>
			)}
			{busy && (
				<p role="status">{__("Processing interval data…", "linker-tools")}</p>
			)}
			{asset && (
				<OwnedProfile
					key={asset.id}
					projectId={projectId}
					assetId={asset.id}
					session={session}
					client={client}
					locale={locale}
					recheck={recheck}
					onSelect={(confirmed, preview) => {
						void select(confirmed, preview);
					}}
				/>
			)}
		</div>
	);
}
