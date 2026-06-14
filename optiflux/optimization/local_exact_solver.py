from __future__ import annotations

from itertools import permutations

from optiflux.config.defaults import LOCAL_EXACT_MAX_UNITS
from optiflux.domain.models import Route, TransportUnit
from optiflux.optimization.route_builder import RouteBuilder


def route_distance(route: Route) -> float:
    return sum(e.distance_km for e in route.events)


def optimize_route_order_exact(route: Route, units: dict[str, TransportUnit], builder: RouteBuilder, max_units: int = LOCAL_EXACT_MAX_UNITS) -> Route:
    """Solveur exact local par énumération sur petits sous-problèmes.

    Pour une tournée contenant peu d'unités, on teste toutes les permutations d'ordre de traitement.
    Cela ne prouve pas l'optimalité globale, mais donne un optimum exact dans le voisinage local testé.
    """
    route_units = [units[uid] for uid in route.unit_ids if uid in units]
    if len(route_units) <= 1 or len(route_units) > max_units:
        return route
    best = route
    best_score = route_distance(route) if route.feasible else float("inf")
    for perm in permutations(route_units):
        trial = builder.build_route(route.day, route.vehicle, route.shift, list(perm))
        if not trial.feasible:
            continue
        score = route_distance(trial)
        if score < best_score:
            best, best_score = trial, score
    return best
