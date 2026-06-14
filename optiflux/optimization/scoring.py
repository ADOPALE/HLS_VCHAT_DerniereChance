from __future__ import annotations

from optiflux.domain.models import TransportUnit


def unit_priority(unit: TransportUnit) -> tuple:
    return (unit.delivery_max, unit.pickup_min, unit.origin, unit.destination, -unit.quantity)


def group_compatibility_score(a: TransportUnit, b: TransportUnit) -> float:
    score = 0.0
    if a.origin == b.origin:
        score += 40
    if a.destination == b.destination:
        score += 40
    if a.support_function == b.support_function:
        score += 10
    if abs(a.pickup_min - b.pickup_min) <= 30:
        score += 15
    if abs(a.delivery_max - b.delivery_max) <= 30:
        score += 10
    if a.sanitary == b.sanitary:
        score += 15
    return score


def can_mix(a: TransportUnit, b: TransportUnit) -> bool:
    if a.mutualized_group and b.mutualized_group and a.mutualized_group != b.mutualized_group:
        return False
    if not a.mixed_allowed or not b.mixed_allowed:
        return a.sanitary == b.sanitary and a.origin == b.origin and a.destination == b.destination
    if b.sanitary in a.exclusions or a.sanitary in b.exclusions:
        return False
    return True
