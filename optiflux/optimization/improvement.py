from __future__ import annotations

from copy import deepcopy

from optiflux.config.defaults import DEFAULT_REOPTIMIZATION_PASSES, MIN_DRIVER_USEFUL_OCCUPANCY
from optiflux.domain.models import Solution, TransportUnit, VehicleInstance
from optiflux.optimization.route_builder import RouteBuilder
from optiflux.optimization.local_exact_solver import optimize_route_order_exact
from optiflux.validation.solution_validator import SolutionValidator


class SolutionImprover:
    def __init__(self, builder: RouteBuilder, validator: SolutionValidator, vehicles: dict, containers: dict, max_passes: int = DEFAULT_REOPTIMIZATION_PASSES):
        self.builder = builder
        self.validator = validator
        self.vehicles = vehicles
        self.containers = containers
        self.max_passes = max_passes

    def improve(self, solution: Solution) -> Solution:
        current = deepcopy(solution)
        for p in range(self.max_passes):
            changed = False
            # 1) exact local route order.
            new_routes = []
            for route in current.routes:
                opt = optimize_route_order_exact(route, current.units, self.builder)
                if opt.events != route.events:
                    changed = True
                new_routes.append(opt)
            current.routes = new_routes

            # 2) try absorbing least useful route into others.
            current.routes.sort(key=lambda r: self._route_useful_minutes(r))
            for route in list(current.routes):
                if len(current.routes) <= 1:
                    break
                if self._try_absorb_route(current, route):
                    changed = True
                    break

            # 3) try downgrade vehicles on each route.
            for i, route in enumerate(list(current.routes)):
                downgraded = self._try_downgrade_route(current, route)
                if downgraded is not None:
                    current.routes[i] = downgraded
                    changed = True

            current.reoptimization_passes = p + 1
            self.validator.validate(current)
            if not changed:
                break
        return current

    def _route_useful_minutes(self, route) -> float:
        return sum(e.duration_min for e in route.events if e.event_type in {"Trajet", "Mise à quai", "Chargement", "Déchargement", "Désinfection"})

    def _try_absorb_route(self, solution: Solution, source_route) -> bool:
        source_units = [solution.units[uid] for uid in source_route.unit_ids]
        for target in list(solution.routes):
            if target is source_route:
                continue
            merged_units = [solution.units[uid] for uid in target.unit_ids] + source_units
            trial_route = self.builder.build_route(target.day, target.vehicle, target.shift, merged_units)
            if not trial_route.feasible:
                continue
            trial_solution = deepcopy(solution)
            source_key = source_route.shift.id
            target_key = target.shift.id
            trial_solution.routes = [r for r in trial_solution.routes if r.shift.id not in {source_key, target_key}] + [trial_route]
            self.validator.validate(trial_solution)
            if trial_solution.hard_valid:
                solution.routes = trial_solution.routes
                solution.validation_items = trial_solution.validation_items
                solution.metrics = trial_solution.metrics
                solution.hard_valid = trial_solution.hard_valid
                solution.performance_acceptable = trial_solution.performance_acceptable
                return True
        return False

    def _try_downgrade_route(self, solution: Solution, route):
        route_units = [solution.units[uid] for uid in route.unit_ids]
        candidates = sorted(self.vehicles.values(), key=lambda v: (v.usable_floor_area, v.payload_t))
        for vt in candidates:
            if vt.name == route.vehicle.vehicle_type.name:
                return None
            if vt.usable_floor_area > route.vehicle.vehicle_type.usable_floor_area + 1e-9:
                continue
            vehicle = VehicleInstance(id=route.vehicle.id.replace(route.vehicle.vehicle_type.name, vt.name), vehicle_type=vt)
            shift = deepcopy(route.shift)
            shift.vehicle_id = vehicle.id
            shift.vehicle_type_name = vt.name
            shift.initial_site = vt.initial_site
            trial = self.builder.build_route(route.day, vehicle, shift, route_units)
            if not trial.feasible:
                continue
            trial_solution = deepcopy(solution)
            route_key = route.shift.id
            trial_solution.routes = [trial if r.shift.id == route_key else r for r in trial_solution.routes]
            self.validator.validate(trial_solution)
            if trial_solution.hard_valid:
                return trial
        return None
