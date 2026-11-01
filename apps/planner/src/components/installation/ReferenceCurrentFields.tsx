import { GeometryText } from "../design/GeometryForm.tsx";
import type { GeometryValues } from "../design/GeometryForm.tsx";
import type {
	CableReference,
	CableReferenceCurrentRating,
} from "../../data/cableReferences.ts";
import type {
	CableRun,
	InstallationInputs,
	ReferenceCurrentInstallation,
} from "../../domain/installation.ts";
import { sameJson } from "../../domain/draft.ts";
import { referenceCurrentContext } from "../../domain/installationReferenceCurrent.ts";
import { formatDecimal } from "../../domain/decimal.ts";
import { CableSource } from "./CableReferenceFacts.tsx";
import {
	ElectricalChoice,
	electricalText,
} from "./ElectricalConditionFields.tsx";

export type ReferenceCurrentChoice =
	| { kind: "none" }
	| { kind: "saved"; declaration: ReferenceCurrentInstallation }
	| {
			kind: "current";
			rating: CableReferenceCurrentRating;
			referenceKey: string;
	  };

export function layingLabel(
	laying: ReferenceCurrentInstallation["laying"],
	locale: string,
): string {
	const t = (en: string, de: string) => electricalText(locale, en, de);
	return {
		single_in_air: t("One cable in air", "Eine Leitung in Luft"),
		single_on_surface: t(
			"One cable on a surface",
			"Eine Leitung auf einer Oberfläche",
		),
		two_touching_on_surface: t(
			"Two touching cables on a surface",
			"Zwei sich berührende Leitungen auf einer Oberfläche",
		),
	}[laying];
}

export function selectedReferenceCurrent(
	choice: ReferenceCurrentChoice,
	reference: CableReference | undefined,
	referenceKey: string,
	savedReferenceKey: string,
	values: GeometryValues,
	confirmed: boolean,
): ReferenceCurrentInstallation | null {
	if (choice.kind === "none") return null;
	if (
		(choice.kind === "saved" && referenceKey !== savedReferenceKey) ||
		(choice.kind === "current" &&
			(choice.referenceKey !== referenceKey ||
				!reference?.cable_facts.reference_current_ratings?.some((rating) =>
					sameJson(rating, choice.rating),
				)))
	)
		throw new Error("reference_current_requires_explicit_selection");
	const currentPath = values.text("reference_current_path"),
		note = String(values.data.get("reference_current_note") ?? "");
	if (
		(!note.trim() &&
			!(choice.kind === "saved" && note === choice.declaration.source_note)) ||
		!["single_unbranched", "unknown"].includes(currentPath)
	)
		throw new Error("reference_current_conditions_required");
	const selected = choice.kind === "saved" ? choice.declaration : choice.rating;
	const laying = selected.laying;
	const touching =
		laying === "two_touching_on_surface" ||
		(choice.kind === "saved" && choice.declaration.touching_run_id !== null)
			? values.text("reference_current_touching") || null
			: null;
	return {
		rating_id:
			choice.kind === "saved" ? choice.declaration.rating_id : choice.rating.id,
		laying,
		ambient_temperature_c: selected.ambient_temperature_c,
		touching_run_id: touching,
		current_path: currentPath as ReferenceCurrentInstallation["current_path"],
		conditions_confirmed: confirmed,
		source_note: note,
		...(choice.kind === "saved" && choice.declaration.confirmation_context
			? { confirmation_context: choice.declaration.confirmation_context }
			: {}),
	};
}

export function ReferenceCurrentFields({
	locale,
	plan,
	cable,
	reference,
	referenceKey,
	savedReferenceKey,
	choice,
	setChoice,
	confirmed,
	setConfirmed,
	confirmationNeedsReview,
	invalidateConfirmation,
	confirmedThisEdit,
}: {
	locale: string;
	plan: InstallationInputs;
	cable: CableRun | null;
	reference: CableReference | undefined;
	referenceKey: string;
	savedReferenceKey: string;
	choice: ReferenceCurrentChoice;
	setChoice: (choice: ReferenceCurrentChoice) => void;
	confirmed: boolean;
	setConfirmed: (value: boolean) => void;
	confirmationNeedsReview: boolean;
	invalidateConfirmation: () => void;
	confirmedThisEdit: boolean;
}) {
	const t = (en: string, de: string) => electricalText(locale, en, de),
		n = (value: number) => formatDecimal(value, locale),
		saved = cable?.reference_current_installation ?? null,
		ratings = reference?.cable_facts.reference_current_ratings ?? [],
		isCurrent =
			choice.kind === "current" &&
			choice.referenceKey === referenceKey &&
			ratings.some((rating) => sameJson(rating, choice.rating)),
		value =
			choice.kind === "none"
				? ""
				: isCurrent
					? "current:" + choice.rating.id
					: "retained",
		declaration =
			choice.kind === "saved"
				? choice.declaration
				: choice.kind === "current"
					? choice.rating
					: null,
		rating =
			choice.kind === "current" && isCurrent
				? choice.rating
				: choice.kind === "saved" && referenceKey === savedReferenceKey
					? ratings.find(
							(row) =>
								row.id === choice.declaration.rating_id &&
								row.laying === choice.declaration.laying &&
								row.ambient_temperature_c ===
									choice.declaration.ambient_temperature_c,
						)
					: undefined,
		showPair =
			declaration?.laying === "two_touching_on_surface" ||
			(choice.kind === "saved" && choice.declaration.touching_run_id !== null),
		otherRuns = plan.cable_runs.filter((row) => row.id !== cable?.id);
	let savedContextCurrent = false;
	if (saved?.confirmation_context && cable) {
		try {
			savedContextCurrent = sameJson(
				saved.confirmation_context,
				referenceCurrentContext(plan, cable, saved),
			);
		} catch {
			// A stale physical reference remains editable but cannot be reconfirmed silently.
		}
	}
	const visibleConfirmed =
		confirmed &&
		(confirmedThisEdit || (choice.kind === "saved" && savedContextCurrent));

	return (
		<fieldset>
			<legend>
				{t(
					"Manufacturer reference current (optional)",
					"Hersteller-Referenzstrom (optional)",
				)}
			</legend>
			<p>
				{t(
					"Choose a documented table row for this physical conductor. The 120 °C conductor temperature is the manufacturer's table condition, not a measured site temperature. The comparison is not a cable sizing or installation approval.",
					"Wählen Sie eine dokumentierte Tabellenzeile für diesen physischen Leiter. Die Leitertemperatur von 120 °C ist eine Bedingung der Herstellertabelle und kein vor Ort gemessener Wert. Der Vergleich ist keine Kabelauslegung oder Installationsfreigabe.",
				)}
			</p>
			<label className="lp-field">
				<span>
					{t("Manufacturer table row", "Zeile der Herstellertabelle")}
				</span>
				<select
					name="reference_current_rating"
					value={value}
					onChange={(event) => {
						const selected = event.currentTarget.value;
						if (!selected) {
							setChoice({ kind: "none" });
							setConfirmed(false);
							return;
						}
						if (selected === "retained") {
							if (saved) {
								setChoice({ kind: "saved", declaration: saved });
								invalidateConfirmation();
							}
							return;
						}
						const found = ratings.find(
							(row) => "current:" + row.id === selected,
						);
						if (found) {
							setChoice({ kind: "current", rating: found, referenceKey });
							invalidateConfirmation();
						}
					}}
				>
					<option value="">
						{t(
							"No reference-current comparison",
							"Kein Referenzstromvergleich",
						)}
					</option>
					{(saved || value === "retained") && (
						<option value="retained">
							{t(
								"Saved selection · retained for review",
								"Gespeicherte Auswahl · zur Prüfung beibehalten",
							)}
						</option>
					)}
					{ratings.map((row) => (
						<option key={row.id} value={"current:" + row.id}>
							{layingLabel(row.laying, locale)} · {n(row.current_a)} A ·{" "}
							{n(row.ambient_temperature_c)} °C {t("ambient", "Umgebung")} ·{" "}
							{n(row.rated_conductor_temperature_c)} °C{" "}
							{t("table conductor", "Tabellen-Leiter")}
						</option>
					))}
				</select>
			</label>
			{choice.kind !== "none" && !rating && (
				<p>
					{t(
						"The saved table row is retained. Select a current documented row or clear the selection to change the cable reference.",
						"Die gespeicherte Tabellenzeile bleibt erhalten. Wählen Sie eine aktuell dokumentierte Zeile oder löschen Sie die Auswahl, um die Kabelreferenz zu ändern.",
					)}
				</p>
			)}
			{rating && (
				<div>
					<p>
						{layingLabel(rating.laying, locale)} · {n(rating.current_a)} A ·{" "}
						{n(rating.ambient_temperature_c)} °C {t("ambient", "Umgebung")} ·{" "}
						{n(rating.rated_conductor_temperature_c)} °C{" "}
						{t(
							"manufacturer table conductor temperature",
							"Leitertemperatur der Herstellertabelle",
						)}
					</p>
					<CableSource source={rating.source} locale={locale} />
				</div>
			)}
			{choice.kind !== "none" && (
				<>
					<ElectricalChoice
						name="reference_current_path"
						label={t("Current path", "Strompfad")}
						value={saved?.current_path}
						onChange={invalidateConfirmation}
						options={[
							[
								"single_unbranched",
								t(
									"One unbranched positive/negative pair",
									"Ein unverzweigtes Plus-/Minus-Leiterpaar",
								),
							],
							["unknown", t("Not confirmed", "Nicht bestätigt")],
						]}
					/>
					{showPair && (
						<label className="lp-field">
							<span>
								{t(
									"Other touching conductor",
									"Anderer sich berührender Leiter",
								)}
							</span>
							<select
								name="reference_current_touching"
								defaultValue={saved?.touching_run_id ?? ""}
								onChange={invalidateConfirmation}
							>
								<option value="">
									{t("Not selected", "Nicht ausgewählt")}
								</option>
								{saved?.touching_run_id &&
									!otherRuns.some(
										(row) => row.id === saved.touching_run_id,
									) && (
										<option value={saved.touching_run_id}>
											{t(
												"Saved conductor unavailable",
												"Gespeicherter Leiter nicht verfügbar",
											)}{" "}
											· {saved.touching_run_id}
										</option>
									)}
								{otherRuns.map((row) => (
									<option key={row.id} value={row.id}>
										{row.name}
									</option>
								))}
							</select>
							<small>
								{t(
									"Both conductors must explicitly select each other, the same cable and table row, and the same route.",
									"Beide Leiter müssen einander, dasselbe Kabel, dieselbe Tabellenzeile und denselben Leitungsweg ausdrücklich auswählen.",
								)}
							</small>
						</label>
					)}
					<label className="lp-field">
						<span>
							<input
								type="checkbox"
								name="reference_current_confirmed"
								checked={visibleConfirmed}
								onChange={(event) => setConfirmed(event.currentTarget.checked)}
							/>{" "}
							{t(
								"I confirm that these project conditions match the selected table row.",
								"Ich bestätige, dass diese Projektbedingungen zur gewählten Tabellenzeile passen.",
							)}
						</span>
					</label>
					{(confirmationNeedsReview ||
						(choice.kind === "saved" && !savedContextCurrent)) &&
						!visibleConfirmed && (
							<p role="status">
								{t(
									"Review the current project conditions and confirm them again.",
									"Prüfen und bestätigen Sie die aktuellen Projektbedingungen erneut.",
								)}
							</p>
						)}
					<GeometryText
						name="reference_current_note"
						label={t(
							"Basis for these project conditions",
							"Grundlage dieser Projektbedingungen",
						)}
						value={saved?.source_note ?? ""}
						multiline
					/>
				</>
			)}
		</fieldset>
	);
}
