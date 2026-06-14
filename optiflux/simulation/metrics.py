from __future__ import annotations

from statistics import mean
from optiflux.domain.models import Solution, Metrics


def compute_metrics(solution: Solution) -> Metrics:
    m = Metrics()
    fill_rates = []
    useful = 0.0
    total_shift = 0.0
    for route in solution.routes:
        total_shift += route.shift.duration_min
        for e in route.events:
            if e.event_type == "Trajet":
                m.total_km += e.distance_km
                m.driving_min += e.duration_min
                if e.loaded_unit_ids_after:
                    m.loaded_km += e.distance_km
                else:
                    m.empty_km += e.distance_km
            elif e.event_type in {"Chargement", "Déchargement"}:
                m.handling_min += e.duration_min
            elif e.event_type == "Mise à quai":
                m.dock_min += e.duration_min
            elif e.event_type == "Attente":
                m.waiting_min += e.duration_min
            elif e.event_type == "Désinfection":
                m.disinfection_min += e.duration_min
                m.disinfections += 1
            elif e.event_type == "Temps inoccupé à la base":
                m.idle_base_min += e.duration_min
            if e.fill_rate_after:
                fill_rates.append(e.fill_rate_after)
        m.cost += sum(e.distance_km for e in route.events if e.event_type == "Trajet") * route.vehicle.vehicle_type.cost_per_km
        m.carbon += sum(e.distance_km for e in route.events if e.event_type == "Trajet") * route.vehicle.vehicle_type.carbon_per_km
    useful = m.driving_min + m.handling_min + m.dock_min + m.disinfection_min
    m.driver_useful_occupancy = useful / total_shift if total_shift else 0.0
    m.avg_fill_rate = mean(fill_rates) if fill_rates else 0.0
    m.max_fill_rate = max(fill_rates) if fill_rates else 0.0
    return m
