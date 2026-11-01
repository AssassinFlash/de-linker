import type { EquipmentProduct } from "../data/equipmentProducts.ts";
import type { CableEvidence } from "../data/cableReferences.ts";
import { isHash, isText } from "../data/cableReferences.ts";
import { documentReference } from "../data/documentReference.ts";
import { ApiError } from "../data/protocol.ts";
import type { JsonObject } from "../data/protocol.ts";
import { readObject } from "../data/readProtocol.ts";
import { sameJson } from "./draft.ts";
import type {
	InstallationInputs,
	InstallationCircuit,
} from "./installation.ts";

export interface TerminalBinding extends JsonObject {
	instance_id: string;
	product_id: number;
	product_revision: string;
	fact_id: string;
	terminal: string;
	document_id: string;
	document_revision: string;
}
export type CommunicationUse =
	"external_communication" | "internal_communication";
export type TerminalDomain =
	"ac" | "pe" | "battery_dc" | "pv_dc" | "communication";
export interface TerminalFact extends JsonObject {
	id: string;
	label: { en: string; de: string };
	basis: "manufacturer_terminal_map";
	specification: JsonObject & {
		terminal_domain: TerminalDomain;
		terminals: string[];
		terminal_use?: CommunicationUse;
	};
	source: CableEvidence;
}
export interface TerminalCandidate {
	binding: TerminalBinding;
	fact: TerminalFact;
}
export type TerminalStatus =
	| "not_bound"
	| "instance_mismatch"
	| "product_unavailable"
	| "product_revision_changed"
	| "fact_unavailable"
	| "document_changed"
	| "terminal_unavailable"
	| "invalid_evidence"
	| "documented";
export type DomainStatus = "not_assessed" | "matches" | "mismatch";
export type UseStatus =
	"not_assessed" | "not_declared" | "not_documented" | "matches" | "mismatch";
export interface TerminalEndpoint {
	side: "start" | "end";
	instance_id: string;
	port_id: string;
	status: TerminalStatus;
	binding: TerminalBinding | null;
	fact: TerminalFact | null;
	domain_status: DomainStatus;
	use_status: UseStatus;
}
export interface TerminalAssessment {
	schema_version: 1;
	scope: "manufacturer_one_end_mapping";
	qualified: false;
	circuits: {
		circuit_id: string;
		name: string;
		kind: InstallationCircuit["kind"];
		communication_use: CommunicationUse | null;
		endpoints: TerminalEndpoint[];
	}[];
}
const domains = ["ac", "pe", "battery_dc", "pv_dc", "communication"];
const uses = ["external_communication", "internal_communication"];
const statuses = [
	"not_bound",
	"instance_mismatch",
	"product_unavailable",
	"product_revision_changed",
	"fact_unavailable",
	"document_changed",
	"terminal_unavailable",
	"invalid_evidence",
	"documented",
];
const fail = (): never => {
	throw new ApiError(502, "invalid_installation_review");
};

/** Only structured manufacturer maps with a complete hosted source yield choices. */
function terminalFact(value: unknown, productId: number): TerminalFact {
	const fact = readObject(value),
		spec = readObject(fact.specification),
		label = readObject(fact.label),
		source = readObject(fact.source);
	documentReference(source, true);
	if (
		!isText(fact.id) ||
		fact.basis !== "manufacturer_terminal_map" ||
		!isText(label.en) ||
		!isText(label.de) ||
		!domains.includes(String(spec.terminal_domain)) ||
		!Array.isArray(spec.terminals) ||
		!spec.terminals.length ||
		spec.terminals.some((term) => !isText(term)) ||
		new Set(spec.terminals).size !== spec.terminals.length ||
		(spec.terminal_use !== undefined &&
			(!uses.includes(String(spec.terminal_use)) ||
				spec.terminal_domain !== "communication")) ||
		!isText(source.document_id) ||
		!isHash(source.document_revision) ||
		!isHash(source.blob_sha256) ||
		source.product_id !== productId ||
		!String(source.url).startsWith(
			"https://de-linker.com/wp-content/uploads/",
		) ||
		!isText(source.quote)
	)
		return fail();
	return fact as TerminalFact;
}

export function terminalCandidates(
	product: EquipmentProduct | undefined,
	instanceId: string,
): TerminalCandidate[] {
	if (!product) return [];
	try {
		const facts = readObject(product.installation_facts);
		if (facts.status !== "documented" || !Array.isArray(facts.items)) return [];
		const ids = facts.items.map((item) => {
			try {
				return readObject(item).id;
			} catch {
				return null;
			}
		});
		const items = facts.items
			.map((raw) => {
				try {
					return terminalFact(raw, product.id);
				} catch {
					return null;
				}
			})
			.filter((item): item is TerminalFact => item !== null);
		return items.flatMap((fact) => {
			// Duplicate identities cannot identify an exact manufacturer fact.
			if (ids.filter((id) => id === fact.id).length !== 1) return [];
			return fact.specification.terminals.map((terminal) => ({
				fact,
				binding: {
					instance_id: instanceId,
					product_id: product.id,
					product_revision: product.product_revision,
					fact_id: fact.id,
					terminal,
					document_id: fact.source.document_id,
					document_revision: fact.source.document_revision,
				},
			}));
		});
	} catch {
		return [];
	}
}

export function hasTerminalFeature(plan: InstallationInputs): boolean {
	return (
		plan.circuits.some((c) => c.communication_use !== undefined) ||
		plan.instances.some((d) =>
			d.ports.some((p) => p.terminal_binding !== undefined),
		)
	);
}

/** Include a terminal-only circuit or a recorded cable run in a report. */
export function hasReportableInstallation(plan: InstallationInputs): boolean {
	return (
		plan.cable_runs.length > 0 ||
		plan.circuits.some(
			(circuit) =>
				(circuit.kind === "control" &&
					circuit.communication_use !== undefined) ||
				[circuit.start, circuit.end].some(
					(endpoint) =>
						plan.instances
							.find((instance) => instance.id === endpoint.instance_id)
							?.ports.find((port) => port.id === endpoint.port_id)
							?.terminal_binding != null,
				),
		)
	);
}

/** Bind every returned end to the requested circuit; never infer a whole-circuit approval. */
export function readTerminalAssessment(
	value: unknown,
	plan: InstallationInputs,
): TerminalAssessment | undefined {
	if (!hasTerminalFeature(plan)) {
		if (value !== undefined) fail();
		return undefined;
	}
	try {
		const row = readObject(value);
		if (
			row.schema_version !== 1 ||
			row.scope !== "manufacturer_one_end_mapping" ||
			row.qualified !== false ||
			!Array.isArray(row.circuits) ||
			row.circuits.length !== plan.circuits.length
		)
			return fail();
		for (const [index, raw] of row.circuits.entries()) {
			const result = readObject(raw),
				circuit = plan.circuits[index]!;
			if (
				result.circuit_id !== circuit.id ||
				result.name !== circuit.name ||
				result.kind !== circuit.kind ||
				result.communication_use !== (circuit.communication_use ?? null) ||
				!Array.isArray(result.endpoints) ||
				result.endpoints.length !== 2
			)
				return fail();
			for (const [i, endpointRaw] of result.endpoints.entries()) {
				const end = readObject(endpointRaw),
					side = i === 0 ? "start" : "end",
					input = circuit[side],
					instance = plan.instances.find((d) => d.id === input.instance_id),
					port = instance?.ports.find((p) => p.id === input.port_id),
					binding = port?.terminal_binding ?? null;
				if (
					!instance ||
					!port ||
					end.side !== side ||
					end.instance_id !== input.instance_id ||
					end.port_id !== input.port_id ||
					!sameJson(end.binding, binding) ||
					!statuses.includes(String(end.status))
				)
					return fail();
				const mismatched =
					binding !== null &&
					(binding.instance_id !== instance.id ||
						binding.product_id !== instance.product_id ||
						binding.product_revision !== instance.product_revision);
				if (
					(binding === null) !== (end.status === "not_bound") ||
					mismatched !== (end.status === "instance_mismatch")
				)
					return fail();
				let domain = "not_assessed",
					use = "not_assessed";
				if (end.status === "documented") {
					if (!binding) return fail();
					const fact = terminalFact(end.fact, binding.product_id);
					if (
						fact.id !== binding.fact_id ||
						!fact.specification.terminals.includes(binding.terminal) ||
						fact.source.document_id !== binding.document_id ||
						fact.source.document_revision !== binding.document_revision
					)
						return fail();
					const expected = (
						{
							ac: "ac",
							pv_dc: "pv_dc",
							battery_dc: "battery_dc",
							protective_earth: "pe",
							control: "communication",
						} as Record<string, string>
					)[circuit.kind];
					if (expected)
						domain =
							fact.specification.terminal_domain === expected
								? "matches"
								: "mismatch";
					if (circuit.kind === "control" && domain === "matches")
						use =
							circuit.communication_use == null
								? "not_declared"
								: fact.specification.terminal_use === undefined
									? "not_documented"
									: fact.specification.terminal_use ===
										  circuit.communication_use
										? "matches"
										: "mismatch";
				} else if (end.fact !== null) return fail();
				if (end.domain_status !== domain || end.use_status !== use)
					return fail();
			}
		}
		return row as unknown as TerminalAssessment;
	} catch {
		return fail();
	}
}
