import type { Project } from "./protocol.ts";

const pendingPrefix = "linker-preliminary-inquiry-pending:";
const requestField = "linker_request_id";
const uuid4 =
	/^[a-f\d]{8}-[a-f\d]{4}-4[a-f\d]{3}-[89ab][a-f\d]{3}-[a-f\d]{12}$/i;
const replayFields = new Set([
	"name",
	"email",
	"company",
	"message",
	"consent",
	"lang",
	requestField,
	"linker_preliminary_project",
	"linker_report_transfer",
	"linker_draft_hash",
	"linker_project_notes_present",
	"linker_include_project_notes",
	"billing_address_1",
	"billing_address_2",
	"billing_city",
	"billing_postcode",
	"billing_country",
	"billing_state",
	"billing_phone",
	"billing_vat_id",
]);
type NativeInquiry = Map<string, string>;
export type PendingInquiry = {
	requestId: string;
	expiresAt: number;
	fields?: Record<string, string>;
};
type ProjectVersion = Pick<Project, "id" | "revision">;

export function guidedInquiryRetry(url: URL): {
	revision: number;
	handle: string | null;
} | null {
	if (
		url.hash !== "#sc-review" ||
		url.searchParams.get("guided") !== "inquiry" ||
		!/^[a-f0-9]{32}$/.test(url.searchParams.get("run") ?? "")
	)
		return null;
	const raw = url.searchParams.get("retry_revision") ?? "";
	const revision = Number(raw);
	if (!/^[1-9]\d*$/.test(raw) || !Number.isSafeInteger(revision)) return null;
	const handle = url.searchParams.get("linker_inquiry_retry");
	return { revision, handle: handle && uuid4.test(handle) ? handle : null };
}

function semanticField(name: string): boolean {
	return (
		replayFields.has(name) ||
		/^linker_project_note_revisions\[[a-zA-Z0-9_-]+\]$/.test(name)
	);
}

function key(scope: string, project: ProjectVersion): string {
	return pendingPrefix + scope + ":" + project.id + ":" + project.revision;
}

function identityField(form: HTMLFormElement): HTMLInputElement | null {
	return form.querySelector(`input[type="hidden"][name="${requestField}"]`);
}

export function replayWindow(form: HTMLFormElement): number {
	const seconds = Number(form.dataset.linkerInquiryReplaySeconds);
	return Number.isSafeInteger(seconds) && seconds > 0 ? seconds : 0;
}

/** The next authorized form supplies fresh credentials. */
export function rememberInquiry(
	form: HTMLFormElement,
	scope: string,
	project: ProjectVersion,
): { saved: boolean; attempt: PendingInquiry } | null {
	const seconds = replayWindow(form);
	const identity = identityField(form);
	if (!seconds || !identity || !uuid4.test(identity.value)) return null;
	const payload = new Map<string, string>();
	for (const [name, value] of new window.FormData(form))
		if (typeof value === "string" && semanticField(name))
			payload.set(name, value);
	const attempt = {
		requestId: identity.value,
		expiresAt: Date.now() + seconds * 1000,
		fields: Object.fromEntries(payload),
	};
	try {
		window.sessionStorage.setItem(key(scope, project), JSON.stringify(attempt));
		return { saved: true, attempt };
	} catch {
		return { saved: false, attempt };
	}
}

function readPending(storageKey: string): PendingInquiry | null {
	const record = JSON.parse(
		window.sessionStorage.getItem(storageKey) ?? "null",
	);
	return record &&
		typeof record.requestId === "string" &&
		uuid4.test(record.requestId) &&
		Number.isSafeInteger(record.expiresAt)
		? record
		: null;
}

export function pendingInquiryRevision(
	scope: string,
	projectId: string,
): number | null {
	const prefix = pendingPrefix + scope + ":" + projectId + ":";
	let oldest: { revision: number; expiresAt: number } | null = null;
	try {
		for (let i = 0; i < window.sessionStorage.length; i++) {
			const name = window.sessionStorage.key(i);
			if (!name?.startsWith(prefix)) continue;
			const revision = Number(name.slice(prefix.length));
			if (!Number.isSafeInteger(revision) || revision < 1) continue;
			const pending = pendingInquiry(scope, { id: projectId, revision });
			if (pending && (!oldest || pending.expiresAt < oldest.expiresAt))
				oldest = { revision, expiresAt: pending.expiresAt };
		}
	} catch {
		// Browser storage is optional for the native submission.
	}
	return oldest?.revision ?? null;
}

export function pendingInquiry(
	scope: string,
	project: ProjectVersion,
): PendingInquiry | null {
	try {
		const storageKey = key(scope, project);
		const record = readPending(storageKey);
		if (!record) return null;
		const { requestId, expiresAt } = record;
		if (!record.fields) return { requestId, expiresAt };
		if (Date.now() >= expiresAt) {
			const expired = { requestId, expiresAt };
			try {
				window.sessionStorage.setItem(storageKey, JSON.stringify(expired));
			} catch {
				// Expired values are not used even if this tab cannot write the marker.
			}
			return expired;
		}
		if (
			record.fields[requestField] !== requestId ||
			record.fields.linker_preliminary_project !==
				`${project.id}:${project.revision}`
		)
			return null;
		return record;
	} catch {
		return null;
	}
}

/** Once Woo has definitely refused an attempt, its revised form can send anew. */
export function forgetInquiry(scope: string, project: ProjectVersion): void {
	try {
		window.sessionStorage.removeItem(key(scope, project));
	} catch {
		// Storage may be unavailable; the native retry still holds this tab's fields.
	}
}

export function inquiryPayload(pending: PendingInquiry): NativeInquiry | null {
	return pending.fields && Date.now() < pending.expiresAt
		? new Map(
				Object.entries(pending.fields).filter(
					([name, value]) => semanticField(name) && typeof value === "string",
				),
			)
		: null;
}

/** Ask Woo for the original receipt with the unchanged submission details. */
export function restoreInquiry(
	form: HTMLFormElement,
	payload: NativeInquiry,
): void {
	const identity = identityField(form);
	const requestId = payload.get(requestField);
	if (!identity || !requestId) throw new Error("invalid_inquiry_form");
	identity.value = requestId;
	for (const control of Array.from(form.elements)) {
		if (
			control === identity ||
			!(
				control instanceof window.HTMLInputElement ||
				control instanceof window.HTMLTextAreaElement ||
				control instanceof window.HTMLSelectElement
			) ||
			!semanticField(control.name)
		)
			continue;
		if (
			control instanceof window.HTMLInputElement &&
			control.type === "hidden"
		) {
			control.remove();
			continue;
		}
		const value = payload.get(control.name);
		if (
			control instanceof window.HTMLInputElement &&
			control.type === "checkbox"
		)
			control.checked = value === control.value;
		else if (value !== undefined) control.value = value;
		control.disabled = true;
	}
	for (const [name, value] of [
		...payload,
		["linker_inquiry_receipt_only", "1"] as const,
	]) {
		if (name === requestField) continue;
		const input = document.createElement("input");
		input.type = "hidden";
		input.name = name;
		input.value = value;
		form.append(input);
	}
}
