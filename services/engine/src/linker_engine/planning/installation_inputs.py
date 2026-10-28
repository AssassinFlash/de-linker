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


class ConnectionPoint(Document):
    id: Identifier
    name: Text
    position: RoutePoint


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


class InstallationCircuit(Document):
    id: Identifier
    name: Text
    kind: Literal["pv_dc", "battery_dc", "ac", "control", "protective_earth", "other"]
    start: Endpoint
    end: Endpoint


class InstallationRoute(Document):
    id: Identifier
    name: Text
    source_id: Identifier
    points: Annotated[list[RoutePoint], Field(min_length=2)]
    extra_length_m: Nonnegative | None
    extra_length_note: Text | None


class ConductorSpecification(Document):
    # The declared cross-section of this physical run. Ampacity, voltage drop,
    # protection and the manufacturer terminal rating are separate assessments.
    cross_section_mm2: Positive
    # Where the project's choice comes from; a declaration, not an approval.
    source_note: Text


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


class PvStringLink(Document):
    string_id: Identifier
    circuit_id: Identifier


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

    def project_document(self) -> Object:
        value = self.model_dump(mode="json")
        if "pv_string_links" not in self.model_fields_set:
            value.pop("pv_string_links")
        # A run without a declared conductor keeps its historical bytes, so the
        # frozen input hash of an unchanged project revision does not move.
        # Omitted and explicit null describe the same physical run, so both
        # drop the key instead of splitting one project into two input hashes.
        for run, dumped in zip(self.cable_runs, value["cable_runs"], strict=True):
            if run.conductor is None:
                dumped.pop("conductor")
        return value

    @model_validator(mode="after")
    def references(self) -> Self:
        for key in ("string_id", "circuit_id"):
            identities = [getattr(link, key) for link in self.pv_string_links]
            if len(identities) != len(set(identities)):
                raise ValueError("PV string links must not have competing assignments")
        for rows in (self.instances, self.circuits, self.routes, self.cable_runs):
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
