import { useState } from "react";
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
					id: instance?.id ?? installationId("instance"),
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
					ports: ports.map((p) => ({
						id: p.id,
						name: v.text(p.id + "name"),
						position: position(v, p.id),
					})),
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
					defaultValue={
						instance
							? instance.product_id === null
								? "site"
								: String(instance.product_id)
							: ""
					}
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
			{ports.map((p) => (
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
			))}
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
				return submit({
					id: circuit?.id ?? installationId("circuit"),
					name: v.text("name"),
					kind: v.text("kind") as InstallationCircuit["kind"],
					start: { instance_id: a[0]!, port_id: a[1]! },
					end: { instance_id: b[0]!, port_id: b[1]! },
				});
			}}
		>
			<GeometryText
				name="name"
				label={__("Name", "linker-tools")}
				value={circuit?.name ?? ""}
			/>
			<label className="lp-field">
				<span>{__("Connection type", "linker-tools")}</span>
				<select name="kind" defaultValue={circuit?.kind ?? ""} required>
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
	submit,
}: { cable: CableRun | null; submit: (value: CableRun) => boolean } & Common) {
	const declared = cable?.conductor ?? null;
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
				return submit({
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
								},
							}
						: {}),
				});
			}}
		>
			<GeometryText
				name="name"
				label={__("Name", "linker-tools")}
				value={cable?.name ?? ""}
			/>
			<label className="lp-field">
				<span>{__("Circuit", "linker-tools")}</span>
				<select name="circuit" required defaultValue={cable?.circuit_id ?? ""}>
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
				<select name="route" required defaultValue={cable?.route_id ?? ""}>
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
		</GeometryForm>
	);
}
