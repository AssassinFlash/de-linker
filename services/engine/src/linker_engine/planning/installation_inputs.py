"""Physical project connections and routes, without editable manufacturer facts."""

from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from .canonical import Object
from .energy_inputs import Document, SchemaVersion
from .equipment_inputs import Count
from .geometry_documents import Hash, Identifier, Nonnegative, Number, Positive, Text


class RoutePoint(Document):
    # Shared JSON/browser transport bounds, not a site-size assumption.
    east_m: Annotated[Number, Field(ge=-(2**53 - 1), le=2**53 - 1)]
    north_m: Annotated[Number, Field(ge=-(2**53 - 1), le=2**53 - 1)]
    height_m: Annotated[Number, Field(ge=-(2**53 - 1), le=2**53 - 1)] | None


class TerminalBinding(Document):
    """An exact selected Woo fact for one particular project instance."""

    instance_id: Identifier
    product_id: Count
    product_revision: Hash
    fact_id: Text
    terminal: Text
    document_id: Text
    document_revision: Hash


class ConnectionPoint(Document):
    id: Identifier
    name: Text
    position: RoutePoint
    terminal_binding: TerminalBinding | None = None


class DeviceInstance(Document):
    id: Identifier
    name: Text
    # Null identifies a measured site connection, not a new product identity.
    product_id: Count | None
    product_revision: Hash | None
    source_id: Identifier
    ports: Annotated[list[ConnectionPoint], Field(min_length=1)]

    @model_validator(mode="after")
    def identity(self) -> Self:
        if (self.product_id is None) != (self.product_revision is None):
            raise ValueError("a Woo instance needs both product ID and revision")
        if len({port.id for port in self.ports}) != len(self.ports):
            raise ValueError("connection point IDs must be distinct per instance")
        return self


class Endpoint(Document):
    instance_id: Identifier
    port_id: Identifier


class VoltageLimit(Document):
    maximum_percent: Nonnegative
    source_note: Text


class CircuitOperatingCondition(Document):
    """Declared steady load; cable manufacturer parameters cannot be entered here."""

    id: Identifier
    name: Text
    method: Literal["dc_resistive", "ac_two_wire", "ac_balanced_three_phase"]
    current_a: Nonnegative
    reference_voltage_v: Positive
    direction: Literal["start_to_end", "end_to_start"]
    conductor_temperature_c: Number
    frequency_hz: Positive | None
    power_factor: Annotated[Number, Field(ge=0, le=1)] | None
    reactive_direction: Literal["lagging", "leading"] | None
    balanced: bool | None
    sinusoidal: bool
    arrangement: Text | None
    source_note: Text
    voltage_limit: VoltageLimit | None


class InstallationCircuit(Document):
    id: Identifier
    name: Text
    kind: Literal["pv_dc", "battery_dc", "ac", "control", "protective_earth", "other"]
    start: Endpoint
    end: Endpoint
    communication_use: (
        Literal["external_communication", "internal_communication"] | None
    ) = None
    operating_conditions: list[CircuitOperatingCondition] = Field(default_factory=list)

    @model_validator(mode="after")
    def conditions(self) -> Self:
        if self.communication_use is not None and self.kind != "control":
            raise ValueError("communication use belongs to a control circuit")
        if len({row.id for row in self.operating_conditions}) != len(
            self.operating_conditions
        ):
            raise ValueError("operating condition IDs must be distinct per circuit")
        return self


class InstallationRoute(Document):
    id: Identifier
    name: Text
    source_id: Identifier
    points: Annotated[list[RoutePoint], Field(min_length=2)]
    extra_length_m: Nonnegative | None
    extra_length_note: Text | None


class CableReference(Document):
    product_id: Count
    product_revision: Hash


class ConductorSpecification(Document):
    # The declared cross-section of this physical run. Ampacity, voltage drop,
    # protection and the manufacturer terminal rating are separate assessments.
    cross_section_mm2: Positive
    # Where the project's choice comes from; a declaration, not an approval.
    source_note: Text
    cable_reference: CableReference | None = None


class ReferenceCurrentEndpoint(Document):
    instance_id: Identifier
    port_id: Identifier
    product_id: Count | None
    product_revision: Hash | None
    position: RoutePoint


class ReferenceCurrentCircuit(Document):
    id: Identifier
    kind: Literal["pv_dc", "battery_dc", "ac", "control", "protective_earth", "other"]
    start: ReferenceCurrentEndpoint
    end: ReferenceCurrentEndpoint


class ReferenceCurrentRoute(Document):
    id: Identifier
    points: Annotated[list[RoutePoint], Field(min_length=2)]
    extra_length_m: Nonnegative | None


class ReferenceCurrentRun(Document):
    id: Identifier
    construction: Literal["single_conductor", "multicore_cable", "unspecified"]
    core_roles: list[
        Literal[
            "dc_positive",
            "dc_negative",
            "line",
            "neutral",
            "l1",
            "l2",
            "l3",
            "pe",
            "unused",
        ]
    ]
    cross_section_mm2: Positive | None
    cable_reference: CableReference | None
    route: ReferenceCurrentRoute
    circuit: ReferenceCurrentCircuit


class ReferenceCurrentDeclaration(Document):
    rating_id: Identifier
    laying: Literal["single_in_air", "single_on_surface", "two_touching_on_surface"]
    ambient_temperature_c: Number
    touching_run_id: Identifier | None
    current_path: Literal["single_unbranched", "unknown"]


class ReferenceCurrentConfirmation(Document):
    """Owner-reviewed context, compared by value instead of number hashing."""

    declaration: ReferenceCurrentDeclaration
    run: ReferenceCurrentRun
    touching_run: ReferenceCurrentRun | None


class ReferenceCurrentInstallation(Document):
    """Owner's explicit match to a manufacturer table row, not a site rating."""

    rating_id: Identifier
    laying: Literal["single_in_air", "single_on_surface", "two_touching_on_surface"]
    ambient_temperature_c: Number
    touching_run_id: Identifier | None
    current_path: Literal["single_unbranched", "unknown"]
    conditions_confirmed: bool
    source_note: Text
    # Absent in historical projects; a new comparison needs confirmation.
    confirmation_context: ReferenceCurrentConfirmation | None = None

    def project_document(self) -> Object:
        value = self.model_dump(mode="json")
        if self.confirmation_context is None:
            value.pop("confirmation_context")
        return value


class CableRun(Document):
    id: Identifier
    name: Text
    circuit_id: Identifier
    route_id: Identifier
    # Each row is one physical length. No core-count multiplier is inferred.
    construction: Literal["single_conductor", "multicore_cable", "unspecified"]
    # Absent leaves the specification explicitly open; it never inherits a
    # neighbouring run, a module count or a manufacturer package quantity.
    conductor: ConductorSpecification | None = None
    # Each role names one physical core, never a purchase-length multiplier.
    core_roles: list[
        Literal[
            "dc_positive",
            "dc_negative",
            "line",
            "neutral",
            "l1",
            "l2",
            "l3",
            "pe",
            "unused",
        ]
    ] = Field(default_factory=list)
    reference_current_installation: ReferenceCurrentInstallation | None = None

    @model_validator(mode="after")
    def roles(self) -> Self:
        active = [role for role in self.core_roles if role != "unused"]
        if len(active) != len(set(active)):
            raise ValueError("core roles must be distinct in a physical cable")
        return self


class PvStringLink(Document):
    string_id: Identifier
    circuit_id: Identifier


class MaterialComparisonCircuit(Document):
    id: Identifier
    kind: Literal["pv_dc", "battery_dc", "ac", "control", "protective_earth", "other"]
    start: Endpoint
    end: Endpoint


class MaterialFactComparison(Document):
    instance_id: Identifier
    product_id: Count
    product_revision: Hash
    fact_id: Text
    document_id: Text
    document_revision: Hash
    cross_section_mm2: Positive | None
    rated_current_a: Positive | None
    rated_voltage_v: Positive | None
    conditions_confirmed: bool
    circuit_context: MaterialComparisonCircuit


class InstallationMaterial(Document):
    """A project declaration, not a manufacturer fact or a sales product."""

    id: Identifier
    name: Text
    kind: Literal["connector", "protection", "earthing", "mounting", "other"]
    circuit_id: Identifier | None
    quantity: Annotated[Positive, Field(le=2**53 - 1)] | None
    unit: Literal["piece", "m"]
    specification: Text
    source_note: Text
    comparison: MaterialFactComparison | None = None

    @model_validator(mode="after")
    def physical_quantity(self) -> Self:
        if self.unit == "piece" and self.quantity is not None:
            if not float(self.quantity).is_integer():
                raise ValueError("piece quantity must be a whole number")
        return self


class InstallationInputs(Document):
    schema_version: SchemaVersion
    geometry_sha256: Hash | None
    instances: list[DeviceInstance]
    circuits: list[InstallationCircuit]
    routes: list[InstallationRoute]
    cable_runs: list[CableRun]
    # Absent retains the historical routing scope; [] explicitly requests a
    # review with no declared links. Cross-document stale IDs remain saveable.
    pv_string_links: list[PvStringLink] = Field(default_factory=list)
    # User-declared physical items. Absence preserves historic project bytes.
    materials: list[InstallationMaterial] = Field(default_factory=list)

    def project_document(self) -> Object:
        value = self.model_dump(mode="json")
        if "pv_string_links" not in self.model_fields_set:
            value.pop("pv_string_links")
        if "materials" not in self.model_fields_set:
            value.pop("materials")
        else:
            for item, dumped in zip(self.materials, value["materials"], strict=True):
                if item.comparison is None:
                    dumped.pop("comparison")
        # A run without a declared conductor keeps its historical bytes, so the
        # frozen input hash of an unchanged project revision does not move.
        # Omitted and explicit null describe the same physical run, so both
        # drop the key instead of splitting one project into two input hashes.
        for run, dumped in zip(self.cable_runs, value["cable_runs"], strict=True):
            if run.conductor is None:
                dumped.pop("conductor")
            elif run.conductor.cable_reference is None:
                dumped["conductor"].pop("cable_reference")
            if "core_roles" not in run.model_fields_set:
                dumped.pop("core_roles")
            if run.reference_current_installation is None:
                dumped.pop("reference_current_installation")
            else:
                dumped["reference_current_installation"] = (
                    run.reference_current_installation.project_document()
                )
        for circuit, dumped in zip(self.circuits, value["circuits"], strict=True):
            if "operating_conditions" not in circuit.model_fields_set:
                dumped.pop("operating_conditions")
            if "communication_use" not in circuit.model_fields_set:
                dumped.pop("communication_use")
        for instance, dumped in zip(self.instances, value["instances"], strict=True):
            for port, dumped_port in zip(instance.ports, dumped["ports"], strict=True):
                if "terminal_binding" not in port.model_fields_set:
                    dumped_port.pop("terminal_binding")
        return value

    @model_validator(mode="after")
    def references(self) -> Self:
        for key in ("string_id", "circuit_id"):
            identities = [getattr(link, key) for link in self.pv_string_links]
            if len(identities) != len(set(identities)):
                raise ValueError("PV string links must not have competing assignments")
        for rows in (
            self.instances,
            self.circuits,
            self.routes,
            self.cable_runs,
            self.materials,
        ):
            if len({row.id for row in rows}) != len(rows):
                raise ValueError("installation IDs must be distinct in their scope")
        ports = {(d.id, p.id) for d in self.instances for p in d.ports}
        for circuit in self.circuits:
            start = (circuit.start.instance_id, circuit.start.port_id)
            end = (circuit.end.instance_id, circuit.end.port_id)
            if start not in ports or end not in ports or start == end:
                raise ValueError("a circuit needs two distinct saved connection points")
        circuits, routes = {c.id for c in self.circuits}, {r.id for r in self.routes}
        if any(
            c.circuit_id not in circuits or c.route_id not in routes
            for c in self.cable_runs
        ):
            raise ValueError("each physical cable needs a saved circuit and route")
        return self


def validate_installation_project(inputs: Object) -> None:
    if "installation" in inputs:
        InstallationInputs.read(inputs["installation"])
