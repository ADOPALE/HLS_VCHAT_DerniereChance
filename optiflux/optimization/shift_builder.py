from __future__ import annotations

from optiflux.config.defaults import DEFAULT_SHIFT_STARTS, DEFAULT_SHIFT_DURATION_MIN, DEFAULT_PRE_SHIFT_MIN, DEFAULT_POST_SHIFT_MIN, DEFAULT_BREAK_DURATION_MIN
from optiflux.domain.models import DriverShift, VehicleInstance, VehicleType
from optiflux.utils.time_utils import parse_time_to_min


def make_shift(vehicle: VehicleInstance, start_min: int, duration_min: int = DEFAULT_SHIFT_DURATION_MIN,
               pre_shift_min: int = DEFAULT_PRE_SHIFT_MIN, post_shift_min: int = DEFAULT_POST_SHIFT_MIN,
               break_duration_min: int = DEFAULT_BREAK_DURATION_MIN, suffix: str = "") -> DriverShift:
    return DriverShift(
        id=f"P_{vehicle.id}_{start_min:04d}{suffix}",
        vehicle_id=vehicle.id,
        vehicle_type_name=vehicle.vehicle_type.name,
        start_min=start_min,
        end_min=start_min + duration_min,
        initial_site=vehicle.vehicle_type.initial_site,
        pre_shift_min=pre_shift_min,
        post_shift_min=post_shift_min,
        break_duration_min=break_duration_min,
    )


def standard_shift_starts() -> list[int]:
    return [parse_time_to_min(s) or 0 for s in DEFAULT_SHIFT_STARTS]


def candidate_shift_starts(unit_pickup_min: int, min_start: int = 6 * 60, max_end: int = 21 * 60,
                           duration_min: int = DEFAULT_SHIFT_DURATION_MIN) -> list[int]:
    starts = standard_shift_starts()
    # Horaires décalés si le flux tombe mal dans les deux postes standards.
    shifted = max(min_start, min(unit_pickup_min - 60, max_end - duration_min))
    starts.append(shifted)
    return sorted(set(s for s in starts if min_start <= s and s + duration_min <= max_end))


def vehicle_available_for_shift(routes, vehicle_id: str, start: int, end: int) -> bool:
    for route in routes:
        if route.vehicle.id != vehicle_id:
            continue
        if not (end <= route.shift.start_min or start >= route.shift.end_min):
            return False
    return True
