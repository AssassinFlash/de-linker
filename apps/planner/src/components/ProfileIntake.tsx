import { useCallback, useEffect, useId, useRef, useState } from "react";
import type { PlannerClient } from "../data/PlannerClient.ts";
import type { DraftStore, ProfileImportIntent } from "../data/DraftStore.ts";
import type { Session } from "../data/protocol.ts";
import { ApiError } from "../data/protocol.ts";
import { wire } from "../data/readProtocol.ts";
import {
	fileBase64,
	readAsset,
	readImport,
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

export function ProfileIntake({
	projectId,
	session,
	client,
	store,
	locale,
	timezone,
	recheck,
	attach,
	registerGuard,
	confirmedAssetIds = [],
}: {
	projectId: string;
	session: Session;
	client: PlannerClient;
	store: DraftStore;
	locale: string;
	timezone: string | null;
	recheck: () => void;
	attach: (assetId: string, role: Measurement) => Promise<boolean>;
	registerGuard: (guard: () => boolean) => void;
	confirmedAssetIds?: readonly string[];
}) {
	const id = useId();
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
	const [requests, setRequests] = useState<readonly ProfileImportIntent[]>([]),
		[pending, setPending] = useState<string | null>(null);
	const [asset, setAsset] = useState<ProfileAsset | null>(null),
		[durable, setDurable] = useState(false);
	const [selected, setSelected] = useState<string | null>(null);
	const lifetime = useRef(0),
		flight = useRef(false),
		form = useRef<HTMLDivElement>(null);
	const numberValidity = useCallback(
		(valid: boolean) => setNumberValid(valid),
		[],
	);
	const current = (instance: number) =>
		instance === lifetime.current && client.isCurrentScope(session.query_scope);
	function restore(body: string) {
		const command = readImport(JSON.parse(body));
		if (command.project_id !== projectId)
			throw new Error("wrong_profile_project");
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
		const instance = ++lifetime.current;
		void store
			.readProfileImports(session.query_scope, projectId)
			.then((records) => {
				if (instance !== lifetime.current) return;
				setRequests(records);
				if (records[0]) restore(records[0].body);
			})
			.catch(() => {
				if (instance === lifetime.current) setRecoveryFailed(true);
			})
			.finally(() => {
				if (instance === lifetime.current) setChecking(false);
			});
		return () => {
			lifetime.current++;
		};
	}, [projectId, session.query_scope, store]);
	const serverRecorded = asset !== null && confirmedAssetIds.includes(asset.id);
	const unprotected =
		(Boolean(content) || readingFile) && !durable && !serverRecorded;
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
			instance = lifetime.current;
		setSelected(asset.id);
		setRequests((previous) =>
			previous.filter((request) => request.body !== body),
		);
		setPending(null);
		setContent("");
		setFileName("");
		setInspection(null);
		setAsset(null);
		setDurable(false);
		setOpen(false);
		void store.clearProfileImport(session.query_scope, body).catch(() => {
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
			(!inspection ||
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
		try {
			body ??= wire(
				readImport({
					schema_version: 1,
					project_id: projectId,
					content_base64: content,
					mapping,
					source_label: label.trim(),
					rights_note: rights.trim(),
					key: crypto.randomUUID(),
				}),
				session.runtime.limits.max_json_depth,
				session.runtime.limits.max_body_bytes,
			);
			setPending(body);
			try {
				await store.writeProfileImport(session.query_scope, body);
				if (instance === lifetime.current) setDurable(true);
			} catch {
				if (instance === lifetime.current) setRecoveryFailed(true);
			}
			if (!current(instance)) return;
			const confirmed = readAsset(
				await client.send("profiles/csv", body, session.query_scope),
				projectId,
			);
			if (current(instance)) setAsset(confirmed);
		} catch (cause) {
			failure(cause, instance);
			// A typed input refusal guarantees no asset publication. An unknown
			// acknowledgement or transient failure retains the exact wire/key.
			if (
				body &&
				current(instance) &&
				cause instanceof ApiError &&
				[400, 413, 415, 422].includes(cause.status)
			) {
				// A definitive pre-publication refusal makes this editable input,
				// even if the browser cannot clean up its older recovery record.
				// Revoke the durable admission before awaiting that cleanup.
				setPending(null);
				setDurable(false);
				const refusedBody = body;
				setRequests((previous) =>
					previous.filter((request) => request.body !== refusedBody),
				);
				try {
					await store.clearProfileImport(session.query_scope, body);
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
			await store.clearProfileImport(session.query_scope, pending);
			if (!current(instance)) return;
			const remaining = await store.readProfileImports(
				session.query_scope,
				projectId,
			);
			if (!current(instance)) return;
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
			setOpen(false);
			if (remaining[0]) restore(remaining[0].body);
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
	if (!open)
		return (
			<>
				{selected && (
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
				)}
				<button
					className="lp-button lp-button-secondary"
					type="button"
					disabled={checking}
					onClick={() => setOpen(true)}
				>
					{__("Import interval data", "linker-tools")}
				</button>
			</>
		);
	return (
		<div className="lp-profile-intake" ref={form}>
			{requests.length > 0 && (
				<label className="lp-field">
					<span id={id + "-requests"}>
						{__("Imports to review", "linker-tools")}
					</span>
					<select
						aria-labelledby={id + "-requests"}
						disabled={busy || unprotected}
						value={
							requests.find((request) => request.body === pending)?.key ?? ""
						}
						onChange={(event) => {
							const request = requests.find(
								(item) => item.key === event.currentTarget.value,
							);
							if (request) restore(request.body);
						}}
					>
						<option value="" disabled>
							{__("Select…", "linker-tools")}
						</option>
						{requests.map((request) => (
							<option key={request.key} value={request.key}>
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
			<ProfileError error={error} />
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
					<details className="lp-comparison">
						<summary>{__("Original import settings", "linker-tools")}</summary>
						<pre>
							{JSON.stringify(
								{
									mapping: readImport(JSON.parse(pending)).mapping,
									source_label: label,
									rights_note: rights,
								},
								null,
								2,
							)}
						</pre>
					</details>
					{!asset && (
						<button
							className="lp-button"
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
					<fieldset disabled={busy} className="lp-brief-fields">
						<h3>{__("1 · Preview source columns", "linker-tools")}</h3>
						<p>
							{__(
								"CSV files need UTF-8 encoding and unique column headers. Preview sends the file for a private structure check without saving a project data source.",
								"linker-tools",
							)}
						</p>
						<div className="grid gap-5 md:grid-cols-2">
							<label className="lp-field">
								<span id={id + "-file"}>
									{__("Source file", "linker-tools")}
								</span>
								<div className="lp-file-picker">
									<span className="lp-file-button" aria-hidden="true">
										{__("Choose CSV file", "linker-tools")}
									</span>
									<span
										className="lp-file-name"
										id={id + "-file-name"}
										aria-live="polite"
									>
										{fileName ||
											(content
												? __("Recovered source file", "linker-tools")
												: __("No file selected", "linker-tools"))}
									</span>
									<input
										ref={fileInput}
										type="file"
										aria-labelledby={id + "-file"}
										aria-describedby={id + "-file-name"}
										accept=".csv,.txt,text/csv,text/plain"
										onChange={(event) => {
											void chooseFile(event.currentTarget.files?.[0]);
										}}
									/>
								</div>
							</label>
							<label className="lp-field">
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
									<option value=";">{__("Semicolon", "linker-tools")}</option>
									<option value=",">{__("Comma", "linker-tools")}</option>
									<option value={"\t"}>{__("Tab", "linker-tools")}</option>
									<option value="|">
										{__("Vertical bar", "linker-tools")}
									</option>
								</select>
							</label>
						</div>
						<div className="lp-inline-actions">
							<button
								className="lp-button lp-button-secondary"
								type="button"
								disabled={!content || !delimiter}
								onClick={() => {
									void inspect();
								}}
							>
								{__("Preview columns", "linker-tools")}
							</button>
							<button
								className="lp-text-button"
								type="button"
								onClick={() => {
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
								className="lp-table-scroll"
								role="region"
								aria-label={__("Original file preview", "linker-tools")}
								tabIndex={0}
							>
								<table className="lp-data-table">
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
									new Intl.NumberFormat(locale).format(inspection.record_count),
								)}
							</p>
							<form
								onSubmit={(event) => {
									event.preventDefault();
									void importSource();
								}}
							>
								<fieldset disabled={busy} className="lp-brief-fields">
									<h3>{__("2 · Define values and source", "linker-tools")}</h3>
									<ProfileMapping
										columns={inspection.columns}
										fields={fields}
										locale={locale}
										onChange={setFields}
										onValidity={numberValidity}
									/>
									<div className="grid gap-5 md:grid-cols-2">
										<label className="lp-field">
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
										<label className="lp-field">
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
									<p className="lp-profile-help">
										{__(
											"Each mapped column must be different and interval durations must be positive. The original file and gaps are preserved.",
											"linker-tools",
										)}
									</p>
									<p className="lp-profile-help">
										{__(
											"Import stores the original file and these settings as a private project source. Selecting a profile and saving the project are separate steps.",
											"linker-tools",
										)}
									</p>
									<button
										className="lp-button"
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
