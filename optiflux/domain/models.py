from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Site:
    name: str
    address: str = ""
    has_quay: bool = True
    quay_capacity: int = 3
    compatible_vehicle_types: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class VehicleType:
    name: str
    initial_site: str
    length: float
    width: float
    height: float | None
    payload_t: float
    has_lift: bool
    dock_time_min: float
    handling_no_quay_min_per_container: float
    handling_with_quay_min_per_container: float
    compatible_containers: set[str]
    compatible_sites: set[str]
    cost_per_km: float = 0.0
    carbon_per_km: float = 0.0
    occupancy_rate: float = 0.85

    @property
    def floor_area(self) -> float:
        return max(0.0, self.length * self.width)

    @property
    def usable_floor_area(self) -> float:
        return self.floor_area * self.occupancy_rate


@dataclass(frozen=True)
class ContainerType:
    name: str
    length: float
    width: float
    empty_weight_t: float
    full_weight_t: float

    @property
    def stackable(self) -> bool:
        return "caisse" in self.name.lower() or "caisses" in self.name.lower()

    @property
    def max_stack(self) -> int:
        return 3 if self.stackable else 1

    @property
    def footprint_area(self) -> float:
        return max(0.0, self.length * self.width)


@dataclass
class Flow:
    id: str
    row_number: int
    origin: str
    destination: str
    support_function: str
    nature: str
    container_name: str
    quantity_by_day: dict[str, int]
    pickup_min: int | None
    delivery_max: int | None
    sanitary: str
    full_empty: str = ""
    mixed_allowed: bool = True
    exclusions: set[str] = field(default_factory=set)
    mutualized_name: str | None = None
    original: dict[str, Any] = field(default_factory=dict)


@dataclass
class TransportUnit:
    id: str
    source_flow_ids: list[str]
    row_numbers: list[int]
    origin: str
    destination: str
    support_function: str
    nature: str
    container_name: str
    quantity: int
    pickup_min: int
    delivery_max: int
    sanitary: str
    mixed_allowed: bool
    exclusions: set[str]
    mutualized_group: str | None = None
    preferred_vehicle_type: str | None = None
    groupable: bool = True


@dataclass
class VehicleInstance:
    id: str
    vehicle_type: VehicleType


@dataclass
class DriverShift:
    id: str
    vehicle_id: str
    vehicle_type_name: str
    start_min: int
    end_min: int
    initial_site: str
    pre_shift_min: int
    post_shift_min: int
    break_duration_min: int

    @property
    def duration_min(self) -> int:
        return self.end_min - self.start_min

    @property
    def work_start_min(self) -> int:
        return self.start_min + self.pre_shift_min

    @property
    def work_end_min(self) -> int:
        return self.end_min - self.post_shift_min

    @property
    def break_window(self) -> tuple[int, int]:
        mid = (self.start_min + self.end_min) // 2
        return mid - 60, mid + 60


@dataclass
class RouteEvent:
    day: str
    vehicle_id: str
    shift_id: str
    sequence: int
    event_type: str
    start_min: int
    end_min: int
    site: str = ""
    origin: str = ""
    destination: str = ""
    unit_ids: list[str] = field(default_factory=list)
    loaded_unit_ids_after: list[str] = field(default_factory=list)
    containers_loaded: int = 0
    containers_unloaded: int = 0
    weight_after_t: float = 0.0
    floor_area_after_m2: float = 0.0
    fill_rate_after: float = 0.0
    distance_km: float = 0.0
    duration_min: float = 0.0
    sanitary_state: str = "NEUTRE"
    comment: str = ""


@dataclass
class Route:
    day: str
    vehicle: VehicleInstance
    shift: DriverShift
    events: list[RouteEvent] = field(default_factory=list)
    unit_ids: list[str] = field(default_factory=list)
    feasible: bool = True
    infeasibility_reasons: list[str] = field(default_factory=list)


@dataclass
class ValidationItem:
    day: str
    check_type: str
    status: str
    detail: str
    object_id: str = ""
    severity: str = "Information"
    action: str = ""


@dataclass
class Metrics:
    total_km: float = 0.0
    loaded_km: float = 0.0
    empty_km: float = 0.0
    driving_min: float = 0.0
    handling_min: float = 0.0
    dock_min: float = 0.0
    waiting_min: float = 0.0
    disinfection_min: float = 0.0
    idle_base_min: float = 0.0
    disinfections: int = 0
    driver_useful_occupancy: float = 0.0
    avg_fill_rate: float = 0.0
    max_fill_rate: float = 0.0
    cost: float = 0.0
    carbon: float = 0.0


@dataclass
class Solution:
    day: str
    routes: list[Route]
    units: dict[str, TransportUnit]
    validation_items: list[ValidationItem] = field(default_factory=list)
    metrics: Metrics = field(default_factory=Metrics)
    hard_valid: bool = False
    performance_acceptable: bool = False
    status_message: str = ""
    reoptimization_passes: int = 0
