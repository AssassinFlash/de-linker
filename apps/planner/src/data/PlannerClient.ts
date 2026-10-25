import { boundedBody } from "./boundedBody.ts";
import { ApiError, RPC_PATHS, readEvidenceIssue } from "./protocol.ts";
import type { JsonObject, JsonRpcPath, Session } from "./protocol.ts";
import { readObject, readSession, wire } from "./readProtocol.ts";
import { readProfileIssue } from "./profileIssue.ts";

// Matches the reviewed native gateway. These are transport resource policy,
// never a physical limit or a statement of production capacity.
const MAX_REPLY_BYTES = 32 * 1024 * 1024;
const INITIAL_BODY_BYTES = 16 * 1024 * 1024;
const INITIAL_DEPTH = 32;

export interface ClientOptions {
	baseUrl: string;
	nonceUrl: string;
	origin: string;
	fetch?: typeof fetch;
}

/** Cookie credentials and native nonces only; identity headers are not an API. */
export class PlannerClient {
	get origin(): string {
		return this.base.origin;
	}
	private readonly base: URL;
	private readonly nonceUrl: URL;
	private readonly fetcher: typeof fetch;
	private restNonce = "";
	private session: Session | null = null;
	private generation = 0;

	constructor(options: ClientOptions) {
		this.base = new URL(options.baseUrl);
		this.nonceUrl = new URL(options.nonceUrl);
		for (const url of [this.base, this.nonceUrl]) {
			if (
				url.origin !== options.origin ||
				url.username ||
				url.password ||
				url.hash
			)
				throw new Error("cross_origin_planner_configuration");
		}
		if (this.base.search) throw new Error("invalid_planner_base");
		this.base.pathname = this.base.pathname.replace(/\/$/, "") + "/";
		this.fetcher = options.fetch ?? globalThis.fetch.bind(globalThis);
	}

	/** Rechecks native identity without resubmitting any saved or pending mutation. */
	async bootstrap(signal?: AbortSignal): Promise<Session> {
		const generation = ++this.generation;
		this.session = null;
		this.restNonce = "";
		await this.refreshNonce(generation, signal);
		for (let attempt = 0; attempt < 2; attempt++) {
			const value = await this.post(
				new URL("bootstrap", this.base),
				'{"schema_version":1}',
				signal,
			);
			this.checkGeneration(generation);
			const session = readSession(value);
			if (session.cookie_confirmed) {
				this.session = session;
				return session;
			}
		}
		throw new ApiError(401, "cookie_confirmation_required");
	}

	async query(
		path: JsonRpcPath,
		command: JsonObject,
		expectedScope: string,
		signal?: AbortSignal,
	): Promise<unknown> {
		const session = this.requireSession();
		return this.send(
			path,
			wire(
				command,
				session.runtime.limits.max_json_depth,
				session.runtime.limits.max_body_bytes,
			),
			expectedScope,
			signal,
		);
	}

	/** Retries must pass the exact captured body and key, not regenerate either. */
	async send(
		path: JsonRpcPath,
		serializedBody: string,
		expectedScope: string,
		signal?: AbortSignal,
	): Promise<unknown> {
		const session = this.requireSession();
		if (session.query_scope !== expectedScope)
			throw new ApiError(401, "session_changed");
		if (
			!(RPC_PATHS as readonly string[]).includes(path) ||
			path === ("assets/content" as string)
		)
			throw new ApiError(400, "invalid_rpc_path");
		if (
			new TextEncoder().encode(serializedBody).length >
			session.runtime.limits.max_body_bytes
		)
			throw new ApiError(413, "body_too_large");
		let value: unknown;
		try {
			value = JSON.parse(serializedBody);
		} catch {
			throw new ApiError(422, "invalid_json_object");
		}
		wire(
			readObject(value),
			session.runtime.limits.max_json_depth,
			session.runtime.limits.max_body_bytes,
		);
		return this.post(new URL("rpc/" + path, this.base), serializedBody, signal);
	}

	/** Owned immutable PDF bytes; this path never requests a new calculation. */
	async reportPdf(
		projectId: string,
		assetId: string,
		expectedScope: string,
		signal?: AbortSignal,
		expectedSha256?: string,
	): Promise<Blob> {
		return this.reportFile(
			projectId,
			assetId,
			expectedScope,
			"pdf",
			signal,
			expectedSha256,
		);
	}

	async reportCsv(
		projectId: string,
		assetId: string,
		expectedScope: string,
		expectedSha256: string,
		signal?: AbortSignal,
	): Promise<Blob> {
		return this.reportFile(
			projectId,
			assetId,
			expectedScope,
			"csv",
			signal,
			expectedSha256,
		);
	}

	private async reportFile(
		projectId: string,
		assetId: string,
		expectedScope: string,
		format: "pdf" | "csv",
		signal?: AbortSignal,
		expectedSha256?: string,
	): Promise<Blob> {
		const session = this.requireSession(),
			generation = this.generation;
		if (session.query_scope !== expectedScope)
			throw new ApiError(401, "session_changed");
		const headers: Record<string, string> = {
			"Content-Type": "application/json; charset=utf-8",
		};
		if (this.restNonce) headers["X-WP-Nonce"] = this.restNonce;
		if (session.kind === "guest")
			headers["X-Linker-Planner-Nonce"] = session.nonce;
		const response = await this.fetcher(
			new URL("rpc/assets/content", this.base),
			{
				method: "POST",
				headers,
				body: wire(
					{ schema_version: 1, project_id: projectId, asset_id: assetId },
					session.runtime.limits.max_json_depth,
					session.runtime.limits.max_body_bytes,
				),
				credentials: "same-origin",
				cache: "no-store",
				redirect: "error",
				...(signal ? { signal } : {}),
			},
		);
		this.checkGeneration(generation);
		if (response.status === 401 || response.status === 403) {
			this.invalidate();
			throw new ApiError(response.status, "session_changed");
		}
		if (!response.ok || !response.body)
			throw new ApiError(response.status, "report_download_failed");
		const reader = response.body.getReader(),
			parts: Uint8Array[] = [];
		let size = 0;
		try {
			while (true) {
				const chunk = await reader.read();
				if (chunk.done) break;
				size += chunk.value.byteLength;
				if (size > MAX_REPLY_BYTES) {
					await reader.cancel();
					throw new ApiError(502, "reply_too_large");
				}
				parts.push(chunk.value);
			}
		} finally {
			reader.releaseLock();
		}
		this.checkGeneration(generation);
		const bytes = new Uint8Array(size);
		let offset = 0;
		for (const part of parts) {
			bytes.set(part, offset);
			offset += part.byteLength;
		}
		if (
			format === "pdf" &&
			new TextDecoder().decode(bytes.subarray(0, 5)) !== "%PDF-"
		)
			throw new ApiError(502, "invalid_report_pdf");
		if (expectedSha256 !== undefined) {
			const digest = new Uint8Array(
				await crypto.subtle.digest("SHA-256", bytes.buffer),
			);
			const actual = Array.from(digest, (byte) =>
				byte.toString(16).padStart(2, "0"),
			).join("");
			this.checkGeneration(generation);
			if (actual !== expectedSha256)
				throw new ApiError(502, "report_download_failed");
		}
		return new Blob([bytes.buffer], {
			type: format === "pdf" ? "application/pdf" : "text/csv;charset=utf-8",
		});
	}

	invalidate(): void {
		this.generation++;
		this.session = null;
		this.restNonce = "";
	}

	/** Synchronous admission fence for callbacks that outlive an awaited local
	 * operation. React cleanup may occur after a different native scope is
	 * confirmed; an old component's props or lifetime are not current admission.
	 * The server still checks ownership on every request.
	 */
	isCurrentScope(scope: string): boolean {
		return Boolean(
			this.session?.cookie_confirmed && this.session.query_scope === scope,
		);
	}

	private requireSession(): Session {
		if (!this.session?.cookie_confirmed)
			throw new ApiError(401, "session_confirmation_required");
		return this.session;
	}

	/** Core wp_ajax_rest_nonce, inspected in the installed WordPress 7.1.3. */
	private async refreshNonce(
		generation: number,
		signal?: AbortSignal,
	): Promise<void> {
		const response = await this.fetcher(this.nonceUrl, {
			credentials: "same-origin",
			cache: "no-store",
			redirect: "error",
			...(signal ? { signal } : {}),
		});
		const text = (await boundedBody(response, 1024)).trim();
		this.checkGeneration(generation);
		if (response.status === 400 && text === "0") {
			this.restNonce = "";
			return;
		}
		if (!response.ok || !/^[a-zA-Z0-9]{10}$/.test(text))
			throw new ApiError(503, "session_unavailable");
		this.restNonce = text;
	}

	private async post(
		url: URL,
		body: string,
		signal?: AbortSignal,
	): Promise<unknown> {
		const generation = this.generation;
		if (
			new TextEncoder().encode(body).length >
			(this.session?.runtime.limits.max_body_bytes ?? INITIAL_BODY_BYTES)
		)
			throw new ApiError(413, "body_too_large");
		const headers: Record<string, string> = {
			"Content-Type": "application/json; charset=utf-8",
		};
		if (this.restNonce) headers["X-WP-Nonce"] = this.restNonce;
		if (this.session?.kind === "guest")
			headers["X-Linker-Planner-Nonce"] = this.session.nonce;
		const response = await this.fetcher(url, {
			method: "POST",
			body,
			headers,
			credentials: "same-origin",
			cache: "no-store",
			redirect: "error",
			...(signal ? { signal } : {}),
		});
		this.checkGeneration(generation);
		if (response.status === 401 || response.status === 403) this.invalidate();
		const text = await boundedBody(response, MAX_REPLY_BYTES);
		if (response.status !== 401 && response.status !== 403)
			this.checkGeneration(generation);
		let value: unknown;
		try {
			value = JSON.parse(text);
		} catch {
			throw new ApiError(502, "invalid_reply");
		}
		if (!response.ok) {
			const data = readObject(value);
			const nested =
				data.error !== null &&
				typeof data.error === "object" &&
				!Array.isArray(data.error)
					? (data.error as JsonObject)
					: null;
			const code = nested?.code ?? data.code;
			throw new ApiError(
				response.status,
				typeof code === "string" && /^[a-zA-Z0-9_]{1,128}$/.test(code)
					? code
					: "request_failed",
				readProfileIssue(nested?.profile_issue),
				readEvidenceIssue(nested?.details),
			);
		}
		if (
			!response.headers
				.get("content-type")
				?.toLowerCase()
				.startsWith("application/json")
		)
			throw new ApiError(502, "invalid_reply");
		return value;
	}

	private checkGeneration(generation: number): void {
		if (generation !== this.generation)
			throw new ApiError(409, "session_changed");
	}
}

export const initialWirePolicy = {
	maxBytes: INITIAL_BODY_BYTES,
	maxDepth: INITIAL_DEPTH,
} as const;
