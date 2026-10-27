/** Locale-explicit input; grouping is rejected rather than guessed. */
export function decimalSeparator(locale: string): string {
	return (
		new Intl.NumberFormat(locale)
			.formatToParts(1.5)
			.find((part) => part.type === "decimal")?.value ?? "."
	);
}

/** Shift the number's declared decimal representation at the %/fraction boundary.
 * Multiplication such as 0.57 * 100 creates display artifacts. Exponent shifting
 * avoids that extra binary operation without rounding away declared digits. */
function shiftPercent(value: number | null, exponent: 2 | -2): number | null {
	if (value === null || Object.is(value, -0)) return value;
	const [coefficient, power = "0"] = String(value).split("e");
	return Number(`${coefficient}e${Number(power) + exponent}`);
}
export const toPercent = (value: number | null): number | null =>
	shiftPercent(value, 2);
export const fromPercent = (value: number | null): number | null =>
	shiftPercent(value, -2);
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
