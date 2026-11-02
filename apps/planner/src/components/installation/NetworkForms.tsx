import {
	ElectricalConditionFields,
	operatingCondition,
	ElectricalChoice,
	electricalText,
} from "./ElectricalConditionFields.tsx";
import {
	CableReferenceFacts,
	cableReferenceLabel,
	CableSource,
	RevisionCode,
} from "./CableReferenceFacts.tsx";
import type { CableReference } from "../../data/cableReferences.ts";
import {
	ReferenceCurrentFields,
	selectedReferenceCurrent,
} from "./ReferenceCurrentFields.tsx";
import type { ReferenceCurrentChoice } from "./ReferenceCurrentFields.tsx";
import type { CoreRole } from "../../domain/installationElectrical.ts";
import { referenceCurrentContext } from "../../domain/installationReferenceCurrent.ts";
import { conductorCandidates } from "../../domain/installationConductorComparison.ts";
import { useRef, useState } from "react";
import type { GeometryDocument } from "../../domain/geometry.ts";
import type {
	DeviceInstance,
	ConnectionPoint,
	InstallationCircuit,
	InstallationRoute,
	CableRun,
	InstallationInputs,
	RoutePoint,
	Endpoint,
} from "../../domain/installation.ts";
import { installationId } from "../../domain/installation.ts";
import { sameJson } from "../../domain/draft.ts";
import { parseDecimal } from "../../domain/decimal.ts";
import { terminalCandidates } from "../../domain/installationTerminals.ts";
import type { TerminalBinding } from "../../domain/installationTerminals.ts";
import {
	communicationUseLabel,
	terminalDomainLabel,
} from "./installationLabels.ts";
import type { EquipmentProduct } from "../../data/equipmentProducts.ts";
import {
	GeometryForm,
	GeometryText,
	GeometryNumber,
} from "../design/GeometryForm.tsx";
import type { GeometryValues } from "../design/GeometryForm.tsx";
import { NetworkViewport } from "./NetworkViewport.tsx";
import { __ } from "../../i18n.ts";

interface Common {
	locale: string;
	geometry: GeometryDocument;
	plan: InstallationInputs;
	cancel: () => void;
	onValidity: (valid: boolean) => void;
}
function SourceChoice({
	geometry,
	value,
}: {
	geometry: GeometryDocument;
	value?: string;
}) {
	return (
		<label className="lp-field">
			<span>{__("Source reference", "linker-tools")}</span>
			<select name="source" defaultValue={value ?? ""} required>
				<option value="">{__("Choose a source", "linker-tools")}</option>
				{geometry.sources.map((s) => (
					<option key={s.id} value={s.id}>
						{s.note}
					</option>
				))}
			</select>
		</label>
	);
}
function Position({
	prefix,
	value,
	locale,
}: {
	prefix: string;
	value: RoutePoint | null;
	locale: string;
}) {
	return (
		<div className="lp-scenario-fields">
			<GeometryNumber
				name={prefix + "east"}
				label={__("East", "linker-tools")}
				locale={locale}
				value={value?.east_m ?? null}
			/>
			<GeometryNumber
				name={prefix + "north"}
				label={__("North", "linker-tools")}
				locale={locale}
				value={value?.north_m ?? null}
			/>
			<GeometryNumber
				name={prefix + "height"}
				label={__("Height above project origin", "linker-tools")}
				locale={locale}
				value={value?.height_m ?? null}
				optional
			/>
		</div>
	);
}
function position(values: GeometryValues, prefix: string): RoutePoint {
	return {
		east_m: values.metric(prefix + "east"),
		north_m: values.metric(prefix + "north"),
		height_m: values.number(prefix + "height", { optional: true }),
	};
}
export function InstanceForm({
	locale,
	geometry,
	plan,
	cancel,
	onValidity,
	instance,
	products,
	submit,
}: {
	instance: DeviceInstance | null;
	products: readonly EquipmentProduct[];
	submit: (value: DeviceInstance) => boolean;
} & Common) {
	const [instanceId] = useState(
		() => instance?.id ?? installationId("instance"),
	);
	const [productId, setProductId] = useState(
		instance
			? instance.product_id === null
				? "site"
				: String(instance.product_id)
			: "",
	);
	const [bindingEdits, setBindingEdits] = useState<
		Record<string, TerminalBinding | null>
	>({});
	const [ports, setPorts] = useState<
		{ id: string; before: ConnectionPoint | null }[]
	>(
		instance?.ports.map((p) => ({ id: p.id, before: p })) ?? [
			{ id: installationId("point"), before: null },
		],
	);
	const locked = new Set(
		plan.circuits
			.flatMap((c) => [c.start, c.end])
			.filter((p) => p.instance_id === instance?.id)
			.map((p) => p.port_id),
	);
	const selectedProduct = products.find((p) => String(p.id) === productId);
	const sameProduct =
		instance?.product_id != null && String(instance.product_id) === productId;
	const revision = sameProduct
		? instance!.product_revision
		: selectedProduct?.product_revision;
	const candidates =
		selectedProduct?.product_revision === revision
			? terminalCandidates(selectedProduct, instanceId)
			: [];
	const t = (en: string, de: string) => electricalText(locale, en, de);
	return (
		<GeometryForm
			title={__("Device instance or site connection", "linker-tools")}
			locale={locale}
			cancel={cancel}
			onValidity={onValidity}
			submit={(v) => {
				const raw = v.text("product");
				if (!raw) return false;
				const selected = products.find((p) => String(p.id) === raw);
				const same =
					instance?.product_id !== null && String(instance?.product_id) === raw;
				if (raw !== "site" && !selected && !same) return false;
				return submit({
					...(instance ?? {}),
					id: instanceId,
					name: v.text("name"),
					product_id:
						raw === "site" ? null : same ? instance!.product_id : selected!.id,
					product_revision:
						raw === "site"
							? null
							: same
								? instance!.product_revision
								: selected!.product_revision,
					source_id: v.text("source"),
					ports: ports.map((p) => {
						const port: ConnectionPoint = {
							...(p.before ?? {}),
							id: p.id,
							name: v.text(p.id + "name"),
							position: position(v, p.id),
						};
						if (Object.hasOwn(bindingEdits, p.id)) {
							const binding = bindingEdits[p.id];
							if (binding) port.terminal_binding = binding;
							else delete port.terminal_binding;
						}
						return port;
					}),
				});
			}}
		>
			<GeometryText
				name="name"
				label={__("Name", "linker-tools")}
				value={instance?.name ?? ""}
			/>
			<label className="lp-field">
				<span>{__("Device or site connection", "linker-tools")}</span>
				<select
					name="product"
					required
					value={productId}
					onChange={(event) => setProductId(event.currentTarget.value)}
				>
					<option value="">
						{__("Choose a product or site connection", "linker-tools")}
					</option>
					<option value="site">{__("Site connection", "linker-tools")}</option>
					{instance?.product_id &&
						!products.some((p) => p.id === instance.product_id) && (
							<option value={instance.product_id}>
								{__("Saved device · current data unavailable", "linker-tools")}
							</option>
						)}
					{products.map((p) => (
						<option key={p.id} value={p.id}>
							{p.brand} {p.model}
						</option>
					))}
				</select>
			</label>
			<SourceChoice
				geometry={geometry}
				{...(instance ? { value: instance.source_id } : {})}
			/>
			<p className="lp-profile-help">
				{__(
					"Give each physical device its own name. Connection point names and positions describe your site; manufacturer ratings remain in the product data.",
					"linker-tools",
				)}
			</p>
			{ports.map((p) => {
				const binding = Object.hasOwn(bindingEdits, p.id)
					? (bindingEdits[p.id] ?? null)
					: (p.before?.terminal_binding ?? null);
				const candidate = candidates.find((c) => sameJson(c.binding, binding));
				const candidateIndex = candidates.findIndex((c) =>
					sameJson(c.binding, binding),
				);
				const choice =
					binding === null
						? "none"
						: sameJson(binding, p.before?.terminal_binding)
							? "saved"
							: candidateIndex >= 0
								? `candidate:${candidateIndex}`
								: "retained";
				return (
					<fieldset key={p.id}>
						<GeometryText
							name={p.id + "name"}
							label={__("Connection point name", "linker-tools")}
							value={p.before?.name ?? ""}
						/>
						<Position
							prefix={p.id}
							value={p.before?.position ?? null}
							locale={locale}
						/>
						<label className="lp-field">
							<span>
								{t(
									"Manufacturer terminal (optional)",
									"Herstelleranschluss (optional)",
								)}
							</span>
							<select
								name={p.id + "terminal"}
								value={choice}
								onChange={(event) => {
									const value = event.currentTarget.value;
									const next =
										value === "saved"
											? (p.before?.terminal_binding ?? null)
											: value.startsWith("candidate:")
												? (candidates[Number(value.slice(10))]?.binding ?? null)
												: null;
									setBindingEdits((old) => ({ ...old, [p.id]: next }));
								}}
							>
								<option value="none">
									{t(
										"No manufacturer terminal selected",
										"Kein Herstelleranschluss ausgewählt",
									)}
								</option>
								{p.before?.terminal_binding && (
									<option value="saved">
										{t("Saved selection", "Gespeicherte Auswahl")} ·{" "}
										{p.before.terminal_binding.terminal} ·{" "}
										{p.before.terminal_binding.fact_id}
									</option>
								)}
								{choice === "retained" && binding && (
									<option value="retained">
										{t(
											"Selection kept from another product",
											"Auswahl eines anderen Produkts beibehalten",
										)}{" "}
										· {binding.terminal} · {binding.fact_id}
									</option>
								)}
								{candidates.map((c, index) => (
									<option
										key={JSON.stringify(c.binding)}
										value={`candidate:${index}`}
									>
										{c.binding.terminal} ·{" "}
										{locale.startsWith("de")
											? c.fact.label.de
											: c.fact.label.en}
									</option>
								))}
							</select>
						</label>
						{!candidates.length && (
							<p className="lp-profile-help">
								{t(
									"No documented terminal choices are available for the selected product revision. A saved selection remains until you change or clear it.",
									"Für die ausgewählte Produktrevision sind keine dokumentierten Anschlussoptionen verfügbar. Eine gespeicherte Auswahl bleibt erhalten, bis Sie sie ändern oder entfernen.",
								)}
							</p>
						)}
						{binding && !candidate && (
							<p className="lp-profile-help">
								{t("Saved source", "Gespeicherte Quelle")}:{" "}
								<RevisionCode value={binding.document_id} /> ·{" "}
								<RevisionCode value={binding.document_revision} />
							</p>
						)}
						{candidate && (
							<>
								<p>
									{t(
										"Documented terminal domain",
										"Dokumentierter Anschlussbereich",
									)}
									:{" "}
									{terminalDomainLabel(
										candidate.fact.specification.terminal_domain,
										locale,
									)}{" "}
									· {t("Documented use", "Dokumentierter Verwendungszweck")}:{" "}
									{candidate.fact.specification.terminal_use
										? communicationUseLabel(
												candidate.fact.specification.terminal_use,
												locale,
											)
										: t("Not documented", "Nicht dokumentiert")}
								</p>
								<CableSource source={candidate.fact.source} locale={locale} />
							</>
						)}
						<button
							type="button"
							className="lp-text-button"
							disabled={ports.length === 1 || locked.has(p.id)}
							onClick={() =>
								setPorts((old) => old.filter((row) => row.id !== p.id))
							}
						>
							{__("Remove connection point", "linker-tools")}
						</button>
					</fieldset>
				);
			})}
			<button
				type="button"
				className="lp-button lp-button-secondary"
				onClick={() =>
					setPorts((old) => [
						...old,
						{ id: installationId("point"), before: null },
					])
				}
			>
				{__("Add connection point", "linker-tools")}
			</button>
		</GeometryForm>
	);
}
const endpointValue = (e: Endpoint) => e.instance_id + ":" + e.port_id;
function EndpointChoice({
	plan,
	name,
	value,
}: {
	plan: InstallationInputs;
	name: string;
	value?: Endpoint;
}) {
	return (
		<label className="lp-field">
			<span>
				{name === "start"
					? __("From connection point", "linker-tools")
					: __("To connection point", "linker-tools")}
			</span>
			<select
				required
				name={name}
				defaultValue={value ? endpointValue(value) : ""}
			>
				<option value="">
					{__("Choose a connection point", "linker-tools")}
				</option>
				{plan.instances.flatMap((d) =>
					d.ports.map((p) => (
						<option key={d.id + ":" + p.id} value={d.id + ":" + p.id}>
							{d.name} · {p.name}
						</option>
					)),
				)}
			</select>
		</label>
	);
}
export function CircuitForm({
	locale,
	plan,
	cancel,
	onValidity,
	circuit,
	submit,
}: {
	circuit: InstallationCircuit | null;
	submit: (value: InstallationCircuit) => boolean;
} & Common) {
	const [kind, setKind] = useState<InstallationCircuit["kind"] | "">(
		circuit?.kind ?? "",
	);
	const [communicationUse, setCommunicationUse] = useState<
		NonNullable<InstallationCircuit["communication_use"]> | ""
	>(circuit?.communication_use ?? "");
	const [communicationTouched, setCommunicationTouched] = useState(false);
	const [conditions, setConditions] = useState<
		{
			id: string;
			before:
				| import("../../domain/installationElectrical.ts").CircuitOperatingCondition
				| null;
		}[]
	>(
		() =>
			circuit?.operating_conditions?.map((before) => ({
				id: before.id,
				before,
			})) ?? [],
	);
	const [conditionsTouched, setConditionsTouched] = useState(false);
	const t = (en: string, de: string) => electricalText(locale, en, de);
	return (
		<GeometryForm
			title={__("Circuit", "linker-tools")}
			locale={locale}
			cancel={cancel}
			onValidity={onValidity}
			submit={(v) => {
				const a = v.text("start").split(":"),
					b = v.text("end").split(":");
				if (a.length !== 2 || b.length !== 2) return false;
				const next: InstallationCircuit = {
					...(circuit ?? {}),
					...(conditionsTouched || circuit?.operating_conditions !== undefined
						? {
								operating_conditions: conditions.map((row) =>
									operatingCondition(v, row.id),
								),
							}
						: {}),
					id: circuit?.id ?? installationId("circuit"),
					name: v.text("name"),
					kind: kind as InstallationCircuit["kind"],
					start: { instance_id: a[0]!, port_id: a[1]! },
					end: { instance_id: b[0]!, port_id: b[1]! },
				};
				if (kind !== "control" && next.communication_use != null)
					delete next.communication_use;
				else if (kind === "control" && communicationTouched) {
					if (communicationUse) next.communication_use = communicationUse;
					else delete next.communication_use;
				}
				return submit(next);
			}}
		>
			<GeometryText
				name="name"
				label={__("Name", "linker-tools")}
				value={circuit?.name ?? ""}
			/>
			<label className="lp-field">
				<span>{__("Connection type", "linker-tools")}</span>
				<select
					name="kind"
					value={kind}
					onChange={(event) =>
						setKind(
							event.currentTarget.value as InstallationCircuit["kind"] | "",
						)
					}
					required
				>
					<option value="">
						{__("Choose connection type", "linker-tools")}
					</option>
					{[
						["pv_dc", __("PV DC", "linker-tools")],
						["battery_dc", __("Battery DC", "linker-tools")],
						["ac", __("AC", "linker-tools")],
						["control", __("Control / communication", "linker-tools")],
						["protective_earth", __("Protective earthing", "linker-tools")],
						["other", __("Other", "linker-tools")],
					].map(([key, label]) => (
						<option key={key} value={key}>
							{label}
						</option>
					))}
				</select>
			</label>
			{kind === "control" && (
				<label className="lp-field">
					<span>
						{t(
							"Communication use (optional)",
							"Kommunikationszweck (optional)",
						)}
					</span>
					<select
						name="communication_use"
						value={communicationUse}
						onChange={(event) => {
							setCommunicationTouched(true);
							setCommunicationUse(
								event.currentTarget.value as typeof communicationUse,
							);
						}}
					>
						<option value="">{t("Not declared", "Nicht angegeben")}</option>
						<option value="external_communication">
							{t("External communication", "Externe Kommunikation")}
						</option>
						<option value="internal_communication">
							{t("Internal communication", "Interne Kommunikation")}
						</option>
					</select>
				</label>
			)}
			<EndpointChoice
				plan={plan}
				name="start"
				{...(circuit ? { value: circuit.start } : {})}
			/>
			<EndpointChoice
				plan={plan}
				name="end"
				{...(circuit ? { value: circuit.end } : {})}
			/>
			<p className="lp-profile-help">
				{t(
					"Operating conditions are optional. Enter the actual current, voltage, temperature and source. No electrical assumptions are supplied.",
					"Betriebsbedingungen sind optional. Geben Sie tatsächlichen Strom, Spannung, Temperatur und Quelle an. Elektrische Annahmen werden nicht ergänzt.",
				)}
			</p>
			{conditions.map((row) => (
				<div key={row.id}>
					<ElectricalConditionFields
						id={row.id}
						before={row.before}
						locale={locale}
					/>
					<button
						type="button"
						className="lp-text-button"
						onClick={() => {
							setConditionsTouched(true);
							setConditions((old) => old.filter((r) => r.id !== row.id));
						}}
					>
						{t("Remove operating condition", "Betriebszustand entfernen")}
					</button>
				</div>
			))}
			<button
				type="button"
				className="lp-button lp-button-secondary"
				onClick={() => {
					setConditionsTouched(true);
					setConditions((old) => [
						...old,
						{ id: installationId("condition"), before: null },
					]);
				}}
			>
				{t("Add operating condition", "Betriebszustand hinzufügen")}
			</button>
		</GeometryForm>
	);
}
export function RouteForm({
	locale,
	geometry,
	plan,
	cancel,
	onValidity,
	route,
	submit,
}: {
	route: InstallationRoute | null;
	submit: (value: InstallationRoute) => boolean;
} & Common) {
	const [points, setPoints] = useState<
			{ id: string; before: RoutePoint | null }[]
		>(
			route?.points.map((p) => ({ id: installationId("vertex"), before: p })) ??
				[],
		),
		[drawing, setDrawing] = useState(false);
	function endpoints(id: string) {
		const circuit = plan.circuits.find((c) => c.id === id);
		if (!circuit) return;
		const get = (e: Endpoint) =>
			plan.instances
				.find((d) => d.id === e.instance_id)!
				.ports.find((p) => p.id === e.port_id)!.position;
		setPoints((old) => [
			{ id: installationId("vertex"), before: get(circuit.start) },
			...old.slice(1, -1),
			{ id: installationId("vertex"), before: get(circuit.end) },
		]);
	}
	return (
		<GeometryForm
			title={__("Recorded route", "linker-tools")}
			locale={locale}
			cancel={cancel}
			onValidity={onValidity}
			submit={(v) =>
				submit({
					id: route?.id ?? installationId("route"),
					name: v.text("name"),
					source_id: v.text("source"),
					points: points.map((p) => position(v, p.id)),
					extra_length_m: v.number("extra", { optional: true, min: 0 }),
					extra_length_note: v.text("extra_note") || null,
				})
			}
			submitDisabled={points.length < 2}
		>
			<GeometryText
				name="name"
				label={__("Name", "linker-tools")}
				value={route?.name ?? ""}
			/>
			<SourceChoice
				geometry={geometry}
				{...(route ? { value: route.source_id } : {})}
			/>
			<label className="lp-field">
				<span>{__("Use current circuit endpoints", "linker-tools")}</span>
				<select value="" onChange={(e) => endpoints(e.currentTarget.value)}>
					<option value="">
						{__("Choose a circuit to set the endpoints", "linker-tools")}
					</option>
					{plan.circuits.map((c) => (
						<option key={c.id} value={c.id}>
							{c.name}
						</option>
					))}
				</select>
			</label>
			<p className="lp-profile-help">
				{__(
					"Record every bend and vertical section in project metres. A blank height keeps the complete cable length unconfirmed.",
					"linker-tools",
				)}
			</p>
			<NetworkViewport
				geometry={geometry}
				plan={plan}
				draftPoints={points.flatMap((p) => (p.before ? [p.before] : []))}
				pick={
					drawing
						? (p) => {
								setPoints((old) =>
									old.length >= 2
										? [
												...old.slice(0, -1),
												{ id: installationId("vertex"), before: p },
												old.at(-1)!,
											]
										: [...old, { id: installationId("vertex"), before: p }],
								);
								setDrawing(false);
							}
						: undefined
				}
			/>
			<div className="lp-inline-actions">
				<button
					type="button"
					className="lp-button lp-button-secondary"
					onClick={() => setDrawing((v) => !v)}
				>
					{drawing
						? __("Cancel", "linker-tools")
						: __("Pick a bend in plan view", "linker-tools")}
				</button>
				<button
					type="button"
					className="lp-text-button"
					onClick={() =>
						setPoints((old) =>
							old.length >= 2
								? [
										...old.slice(0, -1),
										{ id: installationId("vertex"), before: null },
										old.at(-1)!,
									]
								: [...old, { id: installationId("vertex"), before: null }],
						)
					}
				>
					{__("Add route point", "linker-tools")}
				</button>
			</div>
			{points.map((p, i) => (
				<fieldset key={p.id}>
					<legend>{i + 1}</legend>
					<Position prefix={p.id} value={p.before} locale={locale} />
					<button
						type="button"
						className="lp-text-button"
						onClick={() =>
							setPoints((old) => old.filter((_, index) => index !== i))
						}
					>
						{__("Remove route point", "linker-tools")}
					</button>
				</fieldset>
			))}
			<GeometryNumber
				name="extra"
				label={__("Additional length (m)", "linker-tools")}
				locale={locale}
				value={route?.extra_length_m ?? null}
				optional
			/>
			<GeometryText
				name="extra_note"
				label={__("Basis for additional length", "linker-tools")}
				value={route?.extra_length_note ?? ""}
				optional
				multiline
			/>
			<p className="lp-profile-help">
				{__(
					"Enter 0 and its basis when the recorded path already includes all required length. No allowance is added automatically.",
					"linker-tools",
				)}
			</p>
		</GeometryForm>
	);
}
export function CableForm({
	locale,
	plan,
	cancel,
	onValidity,
	cable,
	cableReferences = [],
	products = [],
	submit,
}: {
	cable: CableRun | null;
	cableReferences?: readonly CableReference[];
	products?: readonly EquipmentProduct[];
	submit: (value: CableRun) => boolean;
} & Common) {
	const declared = cable?.conductor ?? null;
	const t = (en: string, de: string) => electricalText(locale, en, de);
	const [circuitId, setCircuitId] = useState(cable?.circuit_id ?? "");
	const [manufacturerChoice, setManufacturerChoice] = useState(
		cable?.manufacturer_comparison ? "saved" : "none",
	);
	const [manufacturerConfirmed, setManufacturerConfirmed] = useState(
		cable?.manufacturer_comparison?.conditions_confirmed ?? false,
	);
	const [manufacturerConfirmedHere, setManufacturerConfirmedHere] =
		useState(false);
	const candidates = conductorCandidates(plan, products, locale);
	const eligible = candidates.filter((candidate) => {
		const circuit = plan.circuits.find((item) => item.id === circuitId);
		return (
			circuit?.kind === candidate.kind &&
			[circuit.start.instance_id, circuit.end.instance_id].includes(
				candidate.instanceId,
			)
		);
	});
	const activeManufacturer =
		manufacturerChoice === "saved"
			? candidates.find(
					(candidate) =>
						candidate.instanceId ===
							cable?.manufacturer_comparison?.instance_id &&
						candidate.product.id === cable.manufacturer_comparison.product_id &&
						candidate.product.product_revision ===
							cable.manufacturer_comparison.product_revision &&
						candidate.factId === cable.manufacturer_comparison.fact_id &&
						candidate.documentId ===
							cable.manufacturer_comparison.document_id &&
						candidate.documentRevision ===
							cable.manufacturer_comparison.document_revision,
				)
			: manufacturerChoice.startsWith("candidate:")
				? candidates[Number(manufacturerChoice.slice(10))]
				: undefined;
	const savedReference = declared?.cable_reference;
	const savedReferenceKey = savedReference
		? String(savedReference.product_id) + ":" + savedReference.product_revision
		: "";
	const [referenceKey, setReferenceKey] = useState(savedReferenceKey);
	const [referenceCurrent, setReferenceCurrent] =
		useState<ReferenceCurrentChoice>(() =>
			cable?.reference_current_installation
				? { kind: "saved", declaration: cable.reference_current_installation }
				: { kind: "none" },
		);
	const [currentConfirmed, setCurrentConfirmed] = useState(
		cable?.reference_current_installation?.conditions_confirmed ?? false,
	);
	const [confirmationNeedsReview, setConfirmationNeedsReview] = useState(false);
	const [confirmedThisEdit, setConfirmedThisEdit] = useState(false);
	const lastCrossSection = useRef<number | null | undefined>(
		declared?.cross_section_mm2 ?? null,
	);
	const invalidateCurrentConfirmation = () => {
		setCurrentConfirmed(false);
		setConfirmedThisEdit(false);
		setConfirmationNeedsReview(true);
		setManufacturerConfirmed(false);
		setManufacturerConfirmedHere(false);
	};
	const [roles, setRoles] = useState(() =>
		(cable?.core_roles ?? []).map((role) => ({
			id: installationId("core"),
			role,
		})),
	);
	const [rolesTouched, setRolesTouched] = useState(false);
	const selectedReference = cableReferences.find(
		(r) =>
			String(r.canonical_product_id) + ":" + r.product_revision ===
			referenceKey,
	);

	return (
		<GeometryForm
			title={__("Physical cable or conductor", "linker-tools")}
			locale={locale}
			cancel={cancel}
			onValidity={onValidity}
			submit={(v) => {
				// A declared section and its basis are one declaration: neither
				// half is stored without the other, and neither is invented.
				const conductor = v.paired("cross_section", "conductor_note", {
					positive: true,
				});
				if (referenceKey && !conductor)
					throw new Error("cable_reference_requires_declaration");
				const reference = selectedReference
					? {
							product_id: selectedReference.canonical_product_id,
							product_revision: selectedReference.product_revision,
						}
					: savedReference &&
						  referenceKey ===
								String(savedReference.product_id) +
									":" +
									savedReference.product_revision
						? savedReference
						: null;
				if (referenceKey && !reference)
					throw new Error("cable_reference_unavailable");
				const current = selectedReferenceCurrent(
					referenceCurrent,
					selectedReference,
					referenceKey,
					savedReferenceKey,
					v,
					currentConfirmed,
				);
				const next = {
					...(cable ?? {}),
					...(rolesTouched || cable?.core_roles !== undefined
						? { core_roles: roles.map((r) => v.text(r.id) as CoreRole) }
						: {}),
					id: cable?.id ?? installationId("cable"),
					name: v.text("name"),
					circuit_id: v.text("circuit"),
					route_id: v.text("route"),
					construction: v.text("construction") as CableRun["construction"],
					...(conductor
						? {
								conductor: {
									cross_section_mm2: conductor.value,
									source_note: conductor.basis,
									...(reference ? { cable_reference: reference } : {}),
								},
							}
						: {}),
				};
				if (!conductor) delete next.conductor;
				if (manufacturerChoice === "none") delete next.manufacturer_comparison;
				else {
					const saved =
						manufacturerChoice === "saved"
							? cable?.manufacturer_comparison
							: undefined;
					const selected = manufacturerChoice.startsWith("candidate:")
						? candidates[Number(manufacturerChoice.slice(10))]
						: undefined;
					const circuit = plan.circuits.find(
						(item) => item.id === next.circuit_id,
					);
					if (!saved && (!selected || !circuit || !next.conductor))
						throw new Error("manufacturer_comparison_requires_conductor");
					if (
						selected &&
						(!circuit ||
							circuit.kind !== selected.kind ||
							![circuit.start.instance_id, circuit.end.instance_id].includes(
								selected.instanceId,
							))
					)
						throw new Error("manufacturer_comparison_requires_circuit");
					const identity = saved ?? {
						instance_id: selected!.instanceId,
						product_id: selected!.product.id,
						product_revision: selected!.product.product_revision,
						fact_id: selected!.factId,
						document_id: selected!.documentId,
						document_revision: selected!.documentRevision,
					};
					let context = saved?.confirmation_context;
					if (!context || manufacturerConfirmedHere) {
						if (!next.conductor || !circuit)
							throw new Error("manufacturer_comparison_requires_conductor");
						context = {
							circuit: {
								id: circuit.id,
								kind: circuit.kind,
								start: circuit.start,
								end: circuit.end,
							},
							construction: next.construction,
							conductor: {
								...next.conductor,
								cable_reference: next.conductor.cable_reference ?? null,
							},
							core_roles: next.core_roles ?? [],
						};
					}
					next.manufacturer_comparison = {
						...identity,
						conditions_confirmed: manufacturerConfirmed,
						confirmation_context: context,
					};
				}
				if (current) {
					next.reference_current_installation = current;
					if (currentConfirmed && confirmedThisEdit) {
						const cableRuns = cable
							? plan.cable_runs.map((row) => (row.id === cable.id ? next : row))
							: [...plan.cable_runs, next];
						current.confirmation_context = referenceCurrentContext(
							{ ...plan, cable_runs: cableRuns },
							next,
							current,
						);
					}
				} else delete next.reference_current_installation;
				return submit(next);
			}}
		>
			<GeometryText
				name="name"
				label={__("Name", "linker-tools")}
				value={cable?.name ?? ""}
			/>
			<label className="lp-field">
				<span>{__("Circuit", "linker-tools")}</span>
				<select
					name="circuit"
					required
					defaultValue={cable?.circuit_id ?? ""}
					onChange={(event) => {
						setCircuitId(event.currentTarget.value);
						invalidateCurrentConfirmation();
					}}
				>
					<option value="">{__("Choose a circuit", "linker-tools")}</option>
					{plan.circuits.map((c) => (
						<option key={c.id} value={c.id}>
							{c.name}
						</option>
					))}
				</select>
			</label>
			<label className="lp-field">
				<span>{__("Recorded route", "linker-tools")}</span>
				<select
					name="route"
					required
					defaultValue={cable?.route_id ?? ""}
					onChange={invalidateCurrentConfirmation}
				>
					<option value="">{__("Choose a route", "linker-tools")}</option>
					{plan.routes.map((r) => (
						<option key={r.id} value={r.id}>
							{r.name}
						</option>
					))}
				</select>
			</label>
			<label className="lp-field">
				<span>{__("Physical construction", "linker-tools")}</span>
				<select
					name="construction"
					required
					defaultValue={cable?.construction ?? ""}
					onChange={invalidateCurrentConfirmation}
				>
					<option value="">{__("Choose construction", "linker-tools")}</option>
					<option value="single_conductor">
						{__("One separate conductor", "linker-tools")}
					</option>
					<option value="multicore_cable">
						{__("One multicore cable", "linker-tools")}
					</option>
					<option value="unspecified">
						{__("Not yet specified", "linker-tools")}
					</option>
				</select>
			</label>
			<p className="lp-profile-help">
				{__(
					"Add one row for each physical length. Two separate DC conductors need two rows; one multicore cable needs one row.",
					"linker-tools",
				)}
			</p>
			<div
				onInput={(event) => {
					const input = event.target;
					if (!(input instanceof window.HTMLInputElement)) return;
					try {
						const value = parseDecimal(input.value, locale);
						if (value !== lastCrossSection.current)
							invalidateCurrentConfirmation();
						lastCrossSection.current = value;
					} catch {
						lastCrossSection.current = undefined;
						invalidateCurrentConfirmation();
					}
				}}
			>
				<GeometryNumber
					name="cross_section"
					label={__("Declared cross-section", "linker-tools")}
					locale={locale}
					unit="mm²"
					value={declared?.cross_section_mm2 ?? null}
					optional
					help={__(
						"Leave empty while the cross-section is still open. This is the project's own declaration, not a sizing result.",
						"linker-tools",
					)}
				/>
			</div>
			<div
				onInput={() => {
					setManufacturerConfirmed(false);
					setManufacturerConfirmedHere(false);
				}}
			>
				<GeometryText
					name="conductor_note"
					label={__("Basis for the declared cross-section", "linker-tools")}
					value={declared?.source_note ?? ""}
					optional
					multiline
					help={__(
						"Required together with the cross-section, for example the project cable list or the installer's instruction.",
						"linker-tools",
					)}
				/>
			</div>
			<label className="lp-field">
				<span>
					{t(
						"Cable manufacturer reference (optional)",
						"Kabelherstellerreferenz (optional)",
					)}
				</span>
				<select
					name="cable_reference"
					value={referenceKey}
					onChange={(e) => {
						setReferenceKey(e.currentTarget.value);
						invalidateCurrentConfirmation();
					}}
				>
					<option value="">
						{t(
							"No manufacturer reference selected",
							"Keine Herstellerreferenz ausgewählt",
						)}
					</option>
					{savedReference &&
						!cableReferences.some(
							(r) =>
								r.canonical_product_id === savedReference.product_id &&
								r.product_revision === savedReference.product_revision,
						) && (
							<option
								value={
									String(savedReference.product_id) +
									":" +
									savedReference.product_revision
								}
							>
								{t(
									"Saved reference · current data unavailable",
									"Gespeicherte Referenz · aktuelle Daten nicht verfügbar",
								)}
							</option>
						)}
					{cableReferences.map((r) => (
						<option
							key={r.canonical_product_id}
							value={String(r.canonical_product_id) + ":" + r.product_revision}
						>
							{cableReferenceLabel(r, locale)}
						</option>
					))}
				</select>
			</label>
			<p className="lp-profile-help">
				{t(
					"Selecting a reference does not change your declared cross-section or construction. They must match the manufacturer's facts. A saved revision is retained until you explicitly select a current one.",
					"Die Auswahl ändert Ihren erklärten Querschnitt oder Aufbau nicht. Beide müssen den Herstellerdaten entsprechen. Eine gespeicherte Revision bleibt erhalten, bis Sie ausdrücklich eine aktuelle auswählen.",
				)}
			</p>
			{selectedReference && (
				<CableReferenceFacts reference={selectedReference} locale={locale} />
			)}
			<label className="lp-field">
				<span>
					{t(
						"Equipment manufacturer cross-section instruction (optional)",
						"Herstellerangabe zum Leiterquerschnitt (optional)",
					)}
				</span>
				<select
					name="manufacturer_conductor"
					value={manufacturerChoice}
					onChange={(event) => {
						setManufacturerChoice(event.currentTarget.value);
						setManufacturerConfirmed(false);
						setManufacturerConfirmedHere(false);
					}}
				>
					<option value="none">
						{t("No manufacturer comparison", "Kein Herstellervergleich")}
					</option>
					{cable?.manufacturer_comparison && (
						<option value="saved">
							{t("Saved selection", "Gespeicherte Auswahl")} ·{" "}
							{cable.manufacturer_comparison.fact_id}
						</option>
					)}
					{eligible.map((candidate) => (
						<option
							key={candidate.instanceId + candidate.factId}
							value={`candidate:${candidates.indexOf(candidate)}`}
						>
							{candidate.product.brand} {candidate.product.model} ·{" "}
							{candidate.label} · p. {candidate.page}
						</option>
					))}
				</select>
			</label>
			{manufacturerChoice !== "none" && (
				<>
					{activeManufacturer ? (
						<details open>
							<summary>{t("Manufacturer source", "Herstellerquelle")}</summary>
							<a
								href={`${activeManufacturer.url}#page=${activeManufacturer.page}`}
								target="_blank"
								rel="noreferrer"
							>
								{t("Document · page", "Dokument · Seite")}{" "}
								{activeManufacturer.page}
							</a>
							<blockquote>{activeManufacturer.quote}</blockquote>
							<p>
								{t("Document revision", "Dokumentrevision")}:{" "}
								<RevisionCode value={activeManufacturer.documentRevision} />
							</p>
						</details>
					) : (
						<p>
							{t(
								"The saved manufacturer source is unavailable. Select a current source or remove the comparison.",
								"Die gespeicherte Herstellerquelle ist nicht verfügbar. Wählen Sie eine aktuelle Quelle oder entfernen Sie den Vergleich.",
							)}
						</p>
					)}
					<p>
						{t(
							"Check that the manufacturer's instruction applies to this device and circuit, then compare the conductor cross-section.",
							"Prüfen Sie, ob die Herstellerangabe für dieses Gerät und diesen Stromkreis gilt. Vergleichen Sie anschließend den Leiterquerschnitt.",
						)}
					</p>
					<label>
						<input
							type="checkbox"
							name="manufacturer_confirmed"
							disabled={!activeManufacturer}
							checked={manufacturerConfirmed}
							onChange={(event) => {
								setManufacturerConfirmed(event.currentTarget.checked);
								setManufacturerConfirmedHere(event.currentTarget.checked);
							}}
						/>{" "}
						{t(
							"I confirm that this manufacturer instruction applies to this conductor and circuit.",
							"Ich bestätige, dass diese Herstellerangabe für diesen Leiter und Stromkreis gilt.",
						)}
					</label>
				</>
			)}
			<ReferenceCurrentFields
				locale={locale}
				plan={plan}
				cable={cable}
				reference={selectedReference}
				referenceKey={referenceKey}
				savedReferenceKey={savedReferenceKey}
				choice={referenceCurrent}
				setChoice={setReferenceCurrent}
				confirmed={currentConfirmed}
				confirmationNeedsReview={confirmationNeedsReview}
				invalidateConfirmation={invalidateCurrentConfirmation}
				confirmedThisEdit={confirmedThisEdit}
				setConfirmed={(value) => {
					setCurrentConfirmed(value);
					setConfirmedThisEdit(value);
					if (value) setConfirmationNeedsReview(false);
				}}
			/>
			<fieldset>
				<legend>
					{t("Physical core roles", "Funktionen der physischen Adern")}
				</legend>
				<p>
					{t(
						"Assign every physical core explicitly. Each row is one core; PE and unused cores carry no current in this calculation. Core count never multiplies purchased cable length.",
						"Ordnen Sie jede physische Ader ausdrücklich zu. Jede Zeile steht für eine Ader; PE und unbenutzte Adern führen in dieser Berechnung keinen Strom. Die Aderzahl vervielfacht die Kabellänge nicht.",
					)}
				</p>
				{roles.map((r) => (
					<div key={r.id}>
						<ElectricalChoice
							name={r.id}
							label={t("Core role", "Aderfunktion")}
							value={r.role}
							onChange={invalidateCurrentConfirmation}
							options={[
								["dc_positive", "DC +"],
								["dc_negative", "DC −"],
								["line", t("Line", "Außenleiter")],
								["neutral", t("Neutral", "Neutralleiter")],
								["l1", "L1"],
								["l2", "L2"],
								["l3", "L3"],
								["pe", "PE"],
								["unused", t("Unused", "Unbenutzt")],
							]}
						/>
						<button
							type="button"
							className="lp-text-button"
							onClick={() => {
								invalidateCurrentConfirmation();
								setRolesTouched(true);
								setRoles((old) => old.filter((row) => row.id !== r.id));
							}}
						>
							{t("Remove core", "Ader entfernen")}
						</button>
					</div>
				))}
				<button
					type="button"
					className="lp-text-button"
					onClick={() => {
						invalidateCurrentConfirmation();
						setRolesTouched(true);
						setRoles((old) => [
							...old,
							{ id: installationId("core"), role: "" as CoreRole },
						]);
					}}
				>
					{t("Add core", "Ader hinzufügen")}
				</button>
			</fieldset>
		</GeometryForm>
	);
}
