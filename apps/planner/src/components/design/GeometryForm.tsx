import { useEffect, useId, useState, useRef } from "react";
import type { ReactNode, FormEvent } from "react";
import {
	formatDecimal,
	parseDecimal,
	decimalSeparator,
} from "../../domain/decimal.ts";
import { __ } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";

class InputError extends Error {
	readonly field: string;
	constructor(field: string, message: string) {
		super(message);
		this.field = field;
	}
}
export class GeometryValues {
	readonly data: FormData;
	readonly locale: string;
	constructor(form: HTMLFormElement, locale: string) {
		this.data = new window.FormData(form);
		this.locale = locale;
	}
	text(name: string): string {
		return String(this.data.get(name) ?? "").trim();
	}
	number(
		name: string,
		options: {
			optional?: boolean;
			min?: number;
			positive?: boolean;
			max?: number;
			maxExclusive?: number;
			integer?: boolean;
		} = {},
	): number | null {
		let value: number | null;
		try {
			value = parseDecimal(this.text(name), this.locale);
		} catch {
			throw new InputError(
				name,
				__(
					"A valid number is required. Thousands separators are not accepted.",
					"linker-tools",
				),
			);
		}
		if (value === null && options.optional) return null;
		if (
			value === null ||
			(options.positive && value <= 0) ||
			(options.min !== undefined && value < options.min) ||
			(options.max !== undefined && value > options.max) ||
			(options.maxExclusive !== undefined && value >= options.maxExclusive) ||
			(options.integer && !Number.isSafeInteger(value))
		)
			throw new InputError(
				name,
				__(
					"The value is outside this field's permitted range. The unit and range are shown beside the field.",
					"linker-tools",
				),
			);
		return value;
	}
	metric(
		name: string,
		options: Parameters<GeometryValues["number"]>[1] = {},
	): number {
		return this.number(name, options)!;
	}
	checked(name: string): boolean {
		return this.data.get(name) === "on";
	}
}

/** Staged properties are explicit. Apply creates one command; Cancel discards only this form. */
export function GeometryForm({
	title,
	locale,
	children,
	submit,
	cancel,
	onValidity,
}: {
	title: string;
	locale: string;
	children: ReactNode;
	submit: (values: GeometryValues) => boolean;
	cancel: () => void;
	onValidity: (valid: boolean) => void;
}) {
	const [error, setError] = useState("");
	const formRef = useRef<HTMLFormElement>(null);
	useEffect(() => {
		formRef.current?.querySelector<HTMLInputElement>("input")?.focus();
	}, []);
	function apply(event: FormEvent<HTMLFormElement>) {
		event.preventDefault();
		const form = event.currentTarget;
		try {
			if (submit(new GeometryValues(form, locale))) {
				onValidity(true);
				cancel();
			}
		} catch (error) {
			onValidity(false);
			if (error instanceof InputError) {
				const input = form.elements.namedItem(error.field);
				if (
					input instanceof window.HTMLInputElement ||
					input instanceof window.HTMLTextAreaElement
				) {
					input.setCustomValidity(error.message);
					input.setAttribute("aria-invalid", "true");
					input.reportValidity();
					input.focus();
				}
				setError(error.message);
			} else
				setError(
					__(
						"These properties could not be applied. The current design has been kept; the values remain available for correction.",
						"linker-tools",
					),
				);
		}
	}
	return (
		<form
			ref={formRef}
			className="lp-geometry-form"
			onSubmit={apply}
			onInput={(event) => {
				onValidity(false);
				setError("");
				const input = event.target;
				if (
					input instanceof window.HTMLInputElement ||
					input instanceof window.HTMLTextAreaElement
				) {
					input.setCustomValidity("");
					input.removeAttribute("aria-invalid");
				}
			}}
			onChange={() => onValidity(false)}
		>
			<h3>{title}</h3>
			<p className="lp-profile-help">
				{decimalSeparator(locale) === ","
					? __(
							"Lengths are in metres. Decimal comma; no thousands separators.",
							"linker-tools",
						)
					: __(
							"Lengths are in metres. Decimal point; no thousands separators.",
							"linker-tools",
						)}
			</p>
			{children}
			{error && <Notice error>{error}</Notice>}
			<div className="lp-inline-actions">
				<button className="lp-button" type="submit">
					{__("Apply properties", "linker-tools")}
				</button>
				<button
					className="lp-button lp-button-secondary"
					type="button"
					onClick={() => {
						onValidity(true);
						cancel();
					}}
				>
					{__("Cancel properties", "linker-tools")}
				</button>
			</div>
		</form>
	);
}

export function GeometryText({
	name,
	label,
	value = "",
	help,
	optional = false,
	multiline = false,
	readOnly = false,
}: {
	name: string;
	label: string;
	value?: string;
	help?: string;
	optional?: boolean;
	multiline?: boolean;
	readOnly?: boolean;
}) {
	const id = useId();
	return (
		<label className="lp-field" htmlFor={id}>
			<span>{label}</span>
			{multiline ? (
				<textarea
					id={id}
					name={name}
					defaultValue={value}
					readOnly={readOnly}
					required={!optional}
					maxLength={4096}
					rows={4}
				/>
			) : (
				<input
					id={id}
					name={name}
					defaultValue={value}
					readOnly={readOnly}
					required={!optional}
					maxLength={4096}
				/>
			)}
			{help && <small>{help}</small>}
		</label>
	);
}
export function GeometryNumber({
	name,
	label,
	value,
	locale,
	unit = "m",
	help,
	optional = false,
}: {
	name: string;
	label: string;
	value?: number | null | undefined;
	locale: string;
	unit?: string;
	help?: string;
	optional?: boolean;
}) {
	const id = useId();
	return (
		<label className="lp-field" htmlFor={id}>
			<span>
				{label}
				<small>{unit}</small>
			</span>
			<input
				id={id}
				name={name}
				defaultValue={formatDecimal(value ?? null, locale)}
				required={!optional}
				inputMode="decimal"
				autoComplete="off"
			/>
			{help && <small>{help}</small>}
		</label>
	);
}
