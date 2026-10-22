/** Locale-explicit input; grouping is rejected rather than guessed. */
export function decimalSeparator(locale: string): string {
	return (
		new Intl.NumberFormat(locale)
			.formatToParts(1.5)
			.find((part) => part.type === "decimal")?.value ?? "."
	);
}
export function formatDecimal(value: number | null, locale: string): string {
	return value === null
		? ""
		: new Intl.NumberFormat(locale, {
				useGrouping: false,
				maximumSignificantDigits: 21,
			}).format(value);
}
export function parseDecimal(text: string, locale: string): number | null {
	const raw = text.trim();
	if (!raw) return null;
	const separator = decimalSeparator(locale);
	if (separator !== "." && raw.includes("."))
		throw new Error("invalid_decimal");
	if (separator !== "," && raw.includes(","))
		throw new Error("invalid_decimal");
	const normalized = raw.replace(separator, ".");
	if (!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(normalized))
		throw new Error("invalid_decimal");
	const value = Number(normalized);
	if (!Number.isFinite(value) || Math.abs(value) > Number.MAX_SAFE_INTEGER)
		throw new Error("invalid_decimal");
	return value;
}
