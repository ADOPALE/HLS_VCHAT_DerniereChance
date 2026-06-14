from __future__ import annotations

from collections import defaultdict

from optiflux.domain.models import ContainerType, VehicleType, TransportUnit
from optiflux.capacity.bin_packing import shelf_pack_2d, pack_multiple


def unit_weight_t(unit: TransportUnit, container: ContainerType) -> float:
    # Le fichier distingue poids vide / plein; on retient poids plein par prudence.
    return unit.quantity * container.full_weight_t


def max_quantity_for_vehicle(container: ContainerType, vehicle: VehicleType, upper_bound: int = 10_000) -> int:
    lo, hi = 0, max(0, int(upper_bound))
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if can_quantity_fit(container, vehicle, mid):
            lo = mid
        else:
            hi = mid - 1
    return lo


def can_quantity_fit(container: ContainerType, vehicle: VehicleType, quantity: int) -> bool:
    if quantity <= 0:
        return True
    if quantity * container.full_weight_t > vehicle.payload_t + 1e-9:
        return False
    return shelf_pack_2d(container, vehicle, quantity).feasible


def can_units_fit(units: list[TransportUnit], containers: dict[str, ContainerType], vehicle: VehicleType) -> tuple[bool, str, float, float, float]:
    by_container: dict[str, int] = defaultdict(int)
    total_weight = 0.0
    for unit in units:
        if unit.container_name not in vehicle.compatible_containers:
            return False, f"Contenant incompatible avec {vehicle.name}: {unit.container_name}", 0, 0, 0
        c = containers[unit.container_name]
        by_container[unit.container_name] += unit.quantity
        total_weight += unit_weight_t(unit, c)
    if total_weight > vehicle.payload_t + 1e-9:
        return False, f"Poids chargé {total_weight:.2f} T > charge utile {vehicle.payload_t:.2f} T", total_weight, 0, 0
    result = pack_multiple([(containers[name], qty) for name, qty in by_container.items()], vehicle)
    if not result.feasible:
        return False, result.reason, total_weight, result.used_area, result.fill_rate
    return True, "", total_weight, result.used_area, result.fill_rate
