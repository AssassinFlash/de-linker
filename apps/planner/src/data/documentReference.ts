import { ApiError } from "./protocol.ts";
import { readObject } from "./readProtocol.ts";

export function documentReference(value: unknown, requirePage = false) {
	const source = readObject(value);
	if (
		typeof source.url !== "string" ||
		((requirePage || source.page != null) &&
			(typeof source.page !== "number" ||
				!Number.isSafeInteger(source.page) ||
				source.page < 1))
	)
		throw new ApiError(502, "invalid_run_result");
	let url: URL;
	try {
		url = new URL(source.url);
	} catch {
		throw new ApiError(502, "invalid_run_result");
	}
	if (
		url.protocol !== "https:" ||
		!["de-linker.com", "www.de-linker.com"].includes(url.hostname) ||
		url.username ||
		url.password
	)
		throw new ApiError(502, "invalid_run_result");
}
