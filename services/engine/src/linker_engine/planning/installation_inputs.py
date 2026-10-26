"""Physical project connections and routes, without editable manufacturer facts."""

from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from .canonical import Object
from .energy_inputs import Document, SchemaVersion
from .equipment_inputs import Count
from .geometry_documents import Hash, Identifier, Nonnegative, Number, Text


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


class CableRun(Document):
    id: Identifier
    name: Text
    circuit_id: Identifier
    route_id: Identifier
    # Each row is one physical length. No core-count multiplier is inferred.
    construction: Literal["single_conductor", "multicore_cable", "unspecified"]


class InstallationInputs(Document):
    schema_version: SchemaVersion
    geometry_sha256: Hash | None
    instances: list[DeviceInstance]
    circuits: list[InstallationCircuit]
    routes: list[InstallationRoute]
    cable_runs: list[CableRun]

    @model_validator(mode="after")
    def references(self) -> Self:
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
