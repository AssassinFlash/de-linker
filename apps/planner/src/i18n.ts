declare global {
	interface Window {
		wp?: {
			i18n?: {
				__(message: string, domain: string): string;
				sprintf(format: string, ...values: (string | number)[]): string;
			};
		};
		/** Resolves when the footer catalog request settled; the inline shell
		 * subset remains the fallback, so failure is not a rejection. */
		linkerToolsCatalog?: Promise<unknown>;
	}
}

/** Uses the installed native @wordpress/i18n; React remains fully isolated. */
export function __(message: string, domain: string): string {
	if (!window.wp?.i18n)
		throw new Error("native_translation_runtime_unavailable");
	return window.wp.i18n.__(message, domain);
}
export function sprintf(
	format: string,
	...values: (string | number)[]
): string {
	if (!window.wp?.i18n)
		throw new Error("native_translation_runtime_unavailable");
	return window.wp.i18n.sprintf(format, ...values);
}
