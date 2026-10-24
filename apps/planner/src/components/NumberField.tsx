import { useEffect, useId, useState } from "react";
import { __, sprintf } from "../i18n.ts";
import {
	decimalSeparator,
	formatDecimal,
	parseDecimal,
} from "../domain/decimal.ts";

function invalidNumberText(
	integer: boolean,
	min: number | undefined,
	max: number | undefined,
	locale: string,
): string {
	if (min !== undefined && max !== undefined)
		return sprintf(
			integer
				? __(
						"A whole number between %1$s and %2$s is required.",
						"linker-tools",
					)
				: __("A number between %1$s and %2$s is required.", "linker-tools"),
			formatDecimal(min, locale),
			formatDecimal(max, locale),
		);
	if (min !== undefined)
		return sprintf(
			integer
				? __("A whole number of %s or greater is required.", "linker-tools")
				: __("A number of %s or greater is required.", "linker-tools"),
			formatDecimal(min, locale),
		);
	return integer
		? __("A valid whole number is required.", "linker-tools")
		: __("A valid number is required.", "linker-tools");
}

export function NumberField({
	label,
	value,
	unit,
	locale,
	min,
	max,
	integer = false,
	onChange,
	onValidity,
}: {
	label: string;
	value: number | null;
	unit: string;
	locale: string;
	min?: number;
	max?: number;
	integer?: boolean;
	onChange: (value: number | null) => void;
	onValidity: (valid: boolean) => void;
}) {
	const id = useId();
	const [text, setText] = useState(formatDecimal(value, locale));
	const [valid, setValid] = useState(true);
	useEffect(() => {
		setText(formatDecimal(value, locale));
		setValid(true);
		onValidity(true);
	}, [value, locale, onValidity]);
	function update(raw: string) {
		setText(raw);
		let number: number | null = null;
		let allowed = true;
		try {
			number = parseDecimal(raw, locale);
			allowed =
				number === null ||
				((!integer || Number.isSafeInteger(number)) &&
					(min === undefined || number >= min) &&
					(max === undefined || number <= max));
		} catch {
			allowed = false;
		}
		setValid(allowed);
		onValidity(allowed);
		if (allowed) onChange(number);
	}
	return (
		<label className="lp-field" htmlFor={id}>
			<span id={id + "-label"}>
				{label} <small>{unit}</small>
			</span>
			<input
				id={id}
				type="text"
				inputMode={integer ? "numeric" : "decimal"}
				autoComplete="off"
				value={text}
				aria-invalid={!valid}
				aria-labelledby={id + "-label"}
				aria-describedby={id + "-format" + (!valid ? " " + id + "-error" : "")}
				onChange={(event) => update(event.currentTarget.value)}
				onKeyDown={(event) => {
					if (event.key !== "Escape") return;
					setText(formatDecimal(value, locale));
					setValid(true);
					onValidity(true);
				}}
			/>
			<small id={id + "-format"}>
				{integer
					? __("Whole numbers; no thousands separators.", "linker-tools")
					: decimalSeparator(locale) === ","
						? __("Decimal comma; no thousands separators.", "linker-tools")
						: __("Decimal point; no thousands separators.", "linker-tools")}
			</small>
			{!valid && (
				<small className="lp-field-error" id={id + "-error"}>
					{invalidNumberText(integer, min, max, locale)}
				</small>
			)}
		</label>
	);
}
