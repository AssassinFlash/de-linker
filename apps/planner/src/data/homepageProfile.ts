import {
	acknowledgeSave,
	beginDraft,
	editDraft,
	prepareSave,
} from "../domain/draft.ts";
import {
	fileBase64,
	readAsset,
	readImport,
	readPreview,
} from "../domain/profiles.ts";
import type { CsvMapping, ImportCommand } from "../domain/profiles.ts";
import { attachGrossLoad } from "../domain/grossLoad.ts";
import type { PlannerClient } from "./PlannerClient.ts";
import { ApiError } from "./protocol.ts";
import type { JsonObject, Project, Session } from "./protocol.ts";
import { readObject, readProject, wire } from "./readProtocol.ts";

export interface HomepageProfileFile {
	readonly file: File;
	readonly mapping: CsvMapping;
	readonly source: string;
	readonly rights: string;
}

export interface HomepageProfileUpload extends JsonObject {
	readonly request: ImportCommand;
	readonly revision_key: string;
}

export async function prepareHomepageProfile(
	upload: HomepageProfileFile,
	limits: Session["runtime"]["limits"],
): Promise<HomepageProfileUpload> {
	const request = readImport({
		schema_version: 1,
		// Only the recovery record uses an unassigned project ID.
		project_id: "0".repeat(32),
		content_base64: await fileBase64(upload.file, limits.max_csv_bytes),
		mapping: upload.mapping,
		source_label: upload.source.trim(),
		rights_note: upload.rights.trim(),
		key: crypto.randomUUID(),
	});
	wire(request, limits.max_json_depth, limits.max_body_bytes);
	return { request, revision_key: crypto.randomUUID() };
}

export function readHomepageProfile(value: unknown): HomepageProfileUpload {
	const row = readObject(value);
	const request = readImport(row.request);
	if (
		request.project_id !== "0".repeat(32) ||
		request.mapping.measurement !== "gross_load" ||
		request.mapping.origin !== "measured" ||
		typeof row.revision_key !== "string"
	)
		throw new Error("invalid_creation_recovery");
	return { request, revision_key: row.revision_key };
}

export async function attachHomepageProfile(
	client: PlannerClient,
	session: Session,
	project: Project,
	upload: HomepageProfileUpload,
): Promise<Project> {
	const scope = session.query_scope;
	const asset = readAsset(
		await client.query(
			"profiles/csv",
			{ ...upload.request, project_id: project.id },
			scope,
		),
		project.id,
	);
	const result = readPreview(
		await client.query(
			"profiles/preview",
			{
				schema_version: 1,
				project_id: project.id,
				asset_id: asset.id,
				offset: 0,
				page_size: Math.min(20, session.runtime.limits.max_page_size),
			},
			scope,
		),
		asset,
	);
	if (result.measurement !== "gross_load")
		throw new ApiError(422, "gross_load_profile_required");
	const draft = prepareSave(
		editDraft(beginDraft(project), attachGrossLoad(project.inputs, result)),
		upload.revision_key,
		{
			maxDepth: session.runtime.limits.max_json_depth,
			maxBytes: session.runtime.limits.max_body_bytes,
		},
	);
	const intent = draft.pending;
	if (!intent) return project;
	const resultProject = readProject(
		await client.send("projects/revise", intent.body, scope),
	);
	return acknowledgeSave(draft, intent, resultProject).baseline;
}
