import { ApiError } from "./protocol.ts";

/** Enforce the native gateway's 32 MiB response policy even without a length header. */
export async function boundedBody(
	response: Response,
	maxBytes: number,
): Promise<string> {
	if (!Number.isSafeInteger(maxBytes) || maxBytes < 1)
		throw new Error("invalid_response_policy");
	const declared = response.headers.get("content-length");
	if (
		declared !== null &&
		(!/^\d+$/.test(declared) || Number(declared) > maxBytes)
	) {
		await response.body?.cancel();
		throw new ApiError(502, "reply_too_large");
	}
	if (!response.body) throw new ApiError(502, "invalid_reply");
	const reader = response.body.getReader();
	const decoder = new TextDecoder("utf-8", { fatal: true });
	let total = 0;
	let text = "";
	try {
		for (;;) {
			const next = await reader.read();
			if (next.done) break;
			total += next.value.byteLength;
			if (total > maxBytes) {
				await reader.cancel();
				throw new ApiError(502, "reply_too_large");
			}
			text += decoder.decode(next.value, { stream: true });
		}
		return text + decoder.decode();
	} catch (error) {
		if (
			error instanceof ApiError ||
			(error instanceof DOMException && error.name === "AbortError")
		)
			throw error;
		throw new ApiError(502, "invalid_reply_encoding");
	} finally {
		reader.releaseLock();
	}
}
