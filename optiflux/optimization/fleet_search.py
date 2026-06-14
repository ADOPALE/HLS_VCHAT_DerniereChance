from __future__ import annotations

from collections import defaultdict
from copy import deepcopy

from optiflux.config.defaults import DEFAULT_SHIFT_DURATION_MIN, DEFAULT_PRE_SHIFT_MIN, DEFAULT_POST_SHIFT_MIN, DEFAULT_BREAK_DURATION_MIN, MIN_DRIVER_USEFUL_OCCUPANCY
from optiflux.domain.models import TransportUnit, VehicleType, VehicleInstance, Solution, Route
from optiflux.optimization.route_builder import RouteBuilder
from optiflux.optimization.shift_builder import make_shift, candidate_shift_starts, vehicle_available_for_shift
from optiflux.optimization.scoring import unit_priority, can_mix
from optiflux.capacity.capacity_checker import can_units_fit
from optiflux.validation.solution_validator import SolutionValidator
from optiflux.optimization.improvement import SolutionImprover


class FleetSearchEngine:
    def __init__(self, vehicles: dict[str, VehicleType], containers: dict, sites: dict, matrices, settings: dict | None = None):
        self.vehicles = vehicles
        self.containers = containers
        self.sites = sites
        self.matrices = matrices
        self.settings = settings or {}
        self.builder = RouteBuilder(matrices, sites, containers,
                                    disinfection_site=self.settings.get("disinfection_site", "HSJ"),
                                    disinfection_min=self.settings.get("disinfection_min", 15))
        self.validator = SolutionValidator(sites, containers, matrices, min_driver_occupancy=self.settings.get("min_driver_occupancy", MIN_DRIVER_USEFUL_OCCUPANCY))

    def solve_day(self, day: str, units: dict[str, TransportUnit], progress_cb=None) -> Solution:
        unassigned = sorted(units.values(), key=unit_priority)
        routes: list[Route] = []
        vehicle_counters: defaultdict[str, int] = defaultdict(int)
        step = 0
        while unassigned:
            step += 1
            if progress_cb:
                progress_cb(step, max(step, len(units)), f"Affectation des unités restantes : {len(unassigned)}")
            unit = unassigned[0]
            group = self._mandatory_group(unit, unassigned)
            route = self._create_new_route(day, group, routes, vehicle_counters)
            if route is None:
                # Dernier recours : on arrête; le validateur signalera les unités non servies.
                break
            # Look-forward : essayer d'ajouter tout de suite des petits flux compatibles au même poste.
            self._fill_route_with_look_forward(route, list(group), [u for u in unassigned if u not in group])
            routes.append(route)
            used_ids = set(route.unit_ids)
            unassigned = [u for u in unassigned if u.id not in used_ids]

        sol = Solution(day=day, routes=routes, units=units)
        self.validator.validate(sol)
        improver = SolutionImprover(self.builder, self.validator, self.vehicles, self.containers,
                                    max_passes=self.settings.get("reoptimization_passes", 6))
        sol = improver.improve(sol)
        self.validator.validate(sol)
        if sol.hard_valid and not sol.performance_acceptable:
            sol.status_message = "Solution techniquement faisable mais non acceptable : occupation utile moyenne chauffeur < seuil paramétré."
        elif sol.hard_valid:
            sol.status_message = "Solution faisable et validée."
        else:
            sol.status_message = "Aucune solution conforme trouvée."
        return sol

    def _mandatory_group(self, unit: TransportUnit, pool: list[TransportUnit]) -> list[TransportUnit]:
        if not unit.mutualized_group:
            return [unit]
        return [u for u in pool if u.mutualized_group == unit.mutualized_group]

    def _candidate_vehicles(self, units: list[TransportUnit]) -> list[VehicleType]:
        cands = []
        for vt in self.vehicles.values():
            if any(u.origin not in vt.compatible_sites or u.destination not in vt.compatible_sites for u in units):
                continue
            ok, _, _, _, _ = can_units_fit(units, self.containers, vt)
            if ok:
                cands.append(vt)
        # Préférence : plus petit véhicule suffisant, sauf unité pleine pré-affectée.
        preferred = {u.preferred_vehicle_type for u in units if u.preferred_vehicle_type}
        cands.sort(key=lambda v: (0 if v.name in preferred else 1, v.usable_floor_area, v.payload_t))
        return cands

    def _create_new_route(self, day: str, units: list[TransportUnit], routes: list[Route], counters: defaultdict[str, int]) -> Route | None:
        for vt in self._candidate_vehicles(units):
            for start in candidate_shift_starts(min(u.pickup_min for u in units),
                                                duration_min=self.settings.get("shift_duration_min", DEFAULT_SHIFT_DURATION_MIN)):
                # Réutilisation prioritaire d'un véhicule existant du même type si poste non chevauchant.
                existing_vehicle_ids = sorted({r.vehicle.id for r in routes if r.vehicle.vehicle_type.name == vt.name})
                vehicle = None
                for vid in existing_vehicle_ids:
                    if vehicle_available_for_shift(routes, vid, start, start + self.settings.get("shift_duration_min", DEFAULT_SHIFT_DURATION_MIN)):
                        vehicle = VehicleInstance(id=vid, vehicle_type=vt)
                        break
                if vehicle is None:
                    counters[vt.name] += 1
                    vehicle = VehicleInstance(id=f"{vt.name}_{counters[vt.name]:02d}", vehicle_type=vt)
                shift = make_shift(vehicle, start,
                                   duration_min=self.settings.get("shift_duration_min", DEFAULT_SHIFT_DURATION_MIN),
                                   pre_shift_min=self.settings.get("pre_shift_min", DEFAULT_PRE_SHIFT_MIN),
                                   post_shift_min=self.settings.get("post_shift_min", DEFAULT_POST_SHIFT_MIN),
                                   break_duration_min=self.settings.get("break_duration_min", DEFAULT_BREAK_DURATION_MIN))
                route = self.builder.build_route(day, vehicle, shift, units)
                if route.feasible:
                    return route
        return None

    def _fill_route_with_look_forward(self, route: Route, route_units: list[TransportUnit], pool: list[TransportUnit]) -> None:
        current_units = list(route_units)
        changed = True
        while changed:
            changed = False
            for candidate in sorted(pool, key=unit_priority):
                if candidate.id in route.unit_ids or candidate.mutualized_group:
                    continue
                trial_units = current_units + [candidate]
                if not all(can_mix(a, b) for i, a in enumerate(trial_units) for b in trial_units[i+1:]):
                    continue
                rebuilt = self.builder.build_route(route.day, route.vehicle, route.shift, trial_units)
                if rebuilt.feasible and len(rebuilt.unit_ids) > len(route.unit_ids):
                    route.events = rebuilt.events
                    route.unit_ids = rebuilt.unit_ids
                    current_units.append(candidate)
                    changed = True
                    break
