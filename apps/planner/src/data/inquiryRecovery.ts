import type { Project } from "./protocol.ts";

const pendingPrefix = "linker-preliminary-inquiry-pending:";
const requestField = "linker_request_id";
const protectedAction = "inquiry";
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
	"linker_draft_hash",
	"linker_project_notes_present",
	"linker_include_project_notes",
	"linker_individual_review",
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

function semanticField(name: string): boolean {
	return (
		replayFields.has(name) ||
		/^linker_project_note_revisions\[[a-zA-Z0-9_-]+\]$/.test(name)
	);
}

function key(scope: string, project: Pick<Project, "id" | "revision">): string {
	return pendingPrefix + scope + ":" + project.id + ":" + project.revision;
}

function identityField(form: HTMLFormElement): HTMLInputElement | null {
	return form.querySelector(
		`input[type="hidden"][name="${requestField}"][data-linker-protected-action="${protectedAction}"]`,
	);
}

/** Carries only the native logical request and semantic input across a lost
 * navigation response. The next authorized form supplies fresh credentials. */
export function rememberInquiry(
	form: HTMLFormElement,
	scope: string,
	project: Pick<Project, "id" | "revision">,
): boolean {
	const identity = identityField(form);
	if (!identity || !uuid4.test(identity.value)) return false;
	const payload = new Map<string, string>();
	for (const [name, value] of new window.FormData(form))
		if (typeof value === "string" && semanticField(name))
			payload.set(name, value);
	window.sessionStorage.setItem(
		key(scope, project),
		JSON.stringify(Object.fromEntries(payload)),
	);
	return true;
}

export function pendingInquiry(
	scope: string,
	project: Pick<Project, "id" | "revision">,
): NativeInquiry | null {
	try {
		const raw = JSON.parse(
			window.sessionStorage.getItem(key(scope, project)) ?? "null",
		);
		if (
			!raw ||
			!uuid4.test(raw[requestField] ?? "") ||
			raw.linker_preliminary_project !== `${project.id}:${project.revision}`
		)
			return null;
		return new Map(
			Object.entries(raw).filter(
				(entry): entry is [string, string] =>
					semanticField(entry[0]) && typeof entry[1] === "string",
			),
		);
	} catch {
		return null;
	}
}

/** The Woo protection client tries the original receipt before obtaining new
 * proof. Keep the viewed fields frozen while posting the exact original data. */
export function restoreInquiry(
	form: HTMLFormElement,
	payload: NativeInquiry,
): void {
	const identity = identityField(form);
	const requestId = payload.get(requestField);
	if (!identity || !requestId) throw new Error("invalid_inquiry_form");
	identity.value = requestId;
	identity.dataset.linkerProtectionRecovery = "true";
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
	for (const [name, value] of payload) {
		if (name === requestField) continue;
		const input = document.createElement("input");
		input.type = "hidden";
		input.name = name;
		input.value = value;
		form.append(input);
	}
}
