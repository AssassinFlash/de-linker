import { useEffect, useId, useState } from "react";
import { __ } from "../i18n.ts";
import {
	calendarDate,
	publicSourceUrl,
	emptyGridConnection,
	readGridConnection,
	type GridConnection,
} from "../domain/gridConnection.ts";

export function GridConnectionForm({
	value,
	onChange,
	onValidity,
}: {
	value: GridConnection | undefined;
	onChange: (value: GridConnection | undefined) => void;
	onValidity: (valid: boolean) => void;
}) {
	const id = useId();
	const [editing, setEditing] = useState(value);
	const [invalid, setInvalid] = useState(false);
	useEffect(() => {
		setEditing(value);
		setInvalid(false);
		onValidity(true);
	}, [value, onValidity]);
	function change(next: GridConnection | undefined) {
		setEditing(next);
		try {
			readGridConnection(next);
			setInvalid(false);
			onValidity(true);
			onChange(next);
		} catch {
			setInvalid(true);
			onValidity(false);
		}
	}
	function field(
		label: string,
		key:
			| "dso_name"
			| "dso_source_url"
			| "title"
			| "source_url"
			| "edition"
			| "date",
		tab = false,
	) {
		if (!editing) return null;
		const raw = tab
			? editing.tab[key as keyof GridConnection["tab"]]
			: editing[key];
		return (
			<label className="lp-field">
				<span>{label}</span>
				<input
					type="text"
					value={typeof raw === "string" ? raw : ""}
					maxLength={key === "date" ? 10 : 4096}
					aria-invalid={
						(invalid &&
							typeof raw === "string" &&
							((key.includes("url") && !publicSourceUrl(raw)) ||
								(key === "date" && !calendarDate(raw)))) ||
						undefined
					}
					aria-describedby={invalid ? id + "-error" : undefined}
					onChange={(event) => {
						const text = event.currentTarget.value;
						const val = text.trim() ? text : null;
						change(
							tab
								? { ...editing, tab: { ...editing.tab, [key]: val } }
								: { ...editing, [key]: val },
						);
					}}
				/>
			</label>
		);
	}
	return (
		<section className="lp-section" aria-labelledby={id + "-heading"}>
			<h2 id={id + "-heading"}>
				{__("Grid connection information", "linker-tools")}
			</h2>
			<p>
				{__(
					"Project-provided information can be saved in stages. The responsible operator, connection voltage and applicable requirements need independent verification; recording them does not establish connection permission.",
					"linker-tools",
				)}
			</p>
			{!editing ? (
				<button
					type="button"
					className="lp-button"
					onClick={() => change(emptyGridConnection())}
				>
					{__("Add grid connection information", "linker-tools")}
				</button>
			) : (
				<>
					<div className="grid gap-5 md:grid-cols-2">
						{field(
							__(
								"Responsible distribution system operator (DSO)",
								"linker-tools",
							),
							"dso_name",
						)}
						{field(__("DSO source URL", "linker-tools"), "dso_source_url")}
						<label className="lp-field">
							<span>
								{__(
									"Voltage level at the grid connection point",
									"linker-tools",
								)}
							</span>
							<select
								value={editing.voltage_level ?? ""}
								onChange={(event) =>
									change({
										...editing,
										voltage_level:
											(event.currentTarget
												.value as GridConnection["voltage_level"]) || null,
									})
								}
							>
								<option value="">{__("Not specified", "linker-tools")}</option>
								<option value="low">{__("Low voltage", "linker-tools")}</option>
								<option value="medium">
									{__("Medium voltage", "linker-tools")}
								</option>
								<option value="high">
									{__("High voltage", "linker-tools")}
								</option>
							</select>
							<small>
								{__(
									"This is the connection point's voltage level, separate from the equipment's terminal voltage.",
									"linker-tools",
								)}
							</small>
						</label>
					</div>
					<fieldset>
						<legend>
							{__(
								"Technical connection requirements (TAB or local equivalent)",
								"linker-tools",
							)}
						</legend>
						<div className="grid gap-5 md:grid-cols-2">
							{field(__("Document title", "linker-tools"), "title", true)}
							{field(
								__("Requirements source URL", "linker-tools"),
								"source_url",
								true,
							)}
							{field(__("Edition or version", "linker-tools"), "edition", true)}
							{field(
								__("Document date (YYYY-MM-DD)", "linker-tools"),
								"date",
								true,
							)}
						</div>
					</fieldset>
					{invalid && (
						<p role="alert" id={id + "-error"}>
							{__(
								"Use a complete HTTP(S) source URL without login details and a valid calendar date in YYYY-MM-DD format. Your entries remain available for correction.",
								"linker-tools",
							)}
						</p>
					)}
					<button
						type="button"
						className="lp-button"
						onClick={() => change(undefined)}
					>
						{__("Remove grid connection information", "linker-tools")}
					</button>
				</>
			)}
		</section>
	);
}
