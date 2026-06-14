from __future__ import annotations

from collections import defaultdict
from optiflux.domain.models import Solution, ValidationItem, TransportUnit
from optiflux.domain.enums import CheckStatus, Severity
from optiflux.capacity.capacity_checker import can_units_fit
from optiflux.simulation.metrics import compute_metrics
from optiflux.simulation.quay_calendar import QuayCalendar
from optiflux.simulation.event_replayer import EventReplayer
from optiflux.optimization.scoring import can_mix


class SolutionValidator:
    def __init__(self, sites: dict, containers: dict, matrices, min_driver_occupancy: float = 0.80):
        self.sites = sites
        self.containers = containers
        self.matrices = matrices
        self.min_driver_occupancy = min_driver_occupancy

    def validate(self, solution: Solution) -> Solution:
        items: list[ValidationItem] = []
        events = [e for r in solution.routes for e in r.events]
        served = set()
        collected = defaultdict(list)
        delivered = defaultdict(list)
        for e in events:
            if e.event_type == "Chargement":
                for uid in e.unit_ids:
                    collected[uid].append(e)
            if e.event_type == "Déchargement":
                for uid in e.unit_ids:
                    delivered[uid].append(e)
                    served.add(uid)

        for uid, unit in solution.units.items():
            if uid not in served:
                items.append(ValidationItem(solution.day, "Service des flux", CheckStatus.KO.value, f"Unité non servie : {uid}.", uid, Severity.BLOCKING.value, "Créer ou réparer une tournée."))
                continue
            if len(collected[uid]) != 1 or len(delivered[uid]) != 1:
                items.append(ValidationItem(solution.day, "Service des flux", CheckStatus.KO.value, f"Unité {uid} collectée/livrée un nombre incorrect de fois.", uid, Severity.BLOCKING.value, "Corriger la séquence."))
                continue
            if collected[uid][0].start_min < unit.pickup_min:
                items.append(ValidationItem(solution.day, "Fenêtre collecte", CheckStatus.KO.value, f"{uid} collectée avant l'heure minimale.", uid, Severity.BLOCKING.value, "Décaler la collecte."))
            if delivered[uid][0].end_min > unit.delivery_max:
                items.append(ValidationItem(solution.day, "Fenêtre livraison", CheckStatus.KO.value, f"{uid} livrée après l'heure maximale.", uid, Severity.BLOCKING.value, "Avancer la livraison ou élargir la fenêtre."))

        # Mutualisation obligatoire : toutes les unités d'un même groupe doivent être dans la même route.
        groups = defaultdict(set)
        for route in solution.routes:
            for uid in route.unit_ids:
                unit = solution.units.get(uid)
                if unit and unit.mutualized_group:
                    groups[unit.mutualized_group].add(route.vehicle.id + "/" + route.shift.id)
        for group, route_keys in groups.items():
            if len(route_keys) > 1:
                items.append(ValidationItem(solution.day, "Tournée mutualisée", CheckStatus.KO.value, f"Groupe {group} réparti sur plusieurs tournées.", group, Severity.BLOCKING.value, "Regrouper les flux mutualisés."))

        # Routes : horaires, pauses, capacités, mixité, compatibilités.
        for route in solution.routes:
            vt = route.vehicle.vehicle_type
            route_units = [solution.units[uid] for uid in route.unit_ids if uid in solution.units]
            for unit in route_units:
                if unit.origin not in vt.compatible_sites or unit.destination not in vt.compatible_sites:
                    items.append(ValidationItem(solution.day, "Compatibilité site", CheckStatus.KO.value, f"{vt.name} incompatible avec {unit.origin} ou {unit.destination}.", unit.id, Severity.BLOCKING.value, "Changer de type de véhicule."))
                if unit.container_name not in vt.compatible_containers:
                    items.append(ValidationItem(solution.day, "Compatibilité contenant", CheckStatus.KO.value, f"{vt.name} incompatible avec {unit.container_name}.", unit.id, Severity.BLOCKING.value, "Changer de type de véhicule."))
            for i, a in enumerate(route_units):
                for b in route_units[i+1:]:
                    if not can_mix(a, b):
                        items.append(ValidationItem(solution.day, "Transport mixte", CheckStatus.KO.value, f"Incompatibilité de mixité entre {a.id} et {b.id}.", route.vehicle.id, Severity.BLOCKING.value, "Séparer les flux."))
            # Capacité après chaque chargement.
            for e in route.events:
                loaded_units = [solution.units[uid] for uid in e.loaded_unit_ids_after if uid in solution.units]
                ok, reason, *_ = can_units_fit(loaded_units, self.containers, vt)
                if not ok:
                    items.append(ValidationItem(solution.day, "Capacité", CheckStatus.KO.value, f"{route.vehicle.id}: {reason}", route.vehicle.id, Severity.BLOCKING.value, "Réduire le groupage ou changer de véhicule."))
            if route.shift.duration_min <= 0:
                items.append(ValidationItem(solution.day, "Poste chauffeur", CheckStatus.KO.value, "Durée de poste invalide.", route.shift.id, Severity.BLOCKING.value, "Corriger param RH."))
            if route.events and (route.events[0].start_min != route.shift.start_min or route.events[-1].end_min != route.shift.end_min):
                items.append(ValidationItem(solution.day, "Durée poste", CheckStatus.KO.value, f"Le poste {route.shift.id} ne couvre pas exactement la durée paramétrée.", route.shift.id, Severity.BLOCKING.value, "Ajouter attente à la base ou corriger la séquence."))
            break_events = [e for e in route.events if e.event_type == "Pause"]
            if len(break_events) != 1:
                items.append(ValidationItem(solution.day, "Pause", CheckStatus.KO.value, f"Le poste {route.shift.id} doit contenir exactement une pause.", route.shift.id, Severity.BLOCKING.value, "Insérer une pause au dépôt."))
            else:
                b = break_events[0]
                bw_start, bw_end = route.shift.break_window
                if b.site != route.shift.initial_site or b.start_min < bw_start or b.end_min > bw_end:
                    items.append(ValidationItem(solution.day, "Pause", CheckStatus.KO.value, f"Pause du poste {route.shift.id} hors dépôt ou hors fenêtre.", route.shift.id, Severity.BLOCKING.value, "Repositionner la pause."))

        site_cap = {name: s.quay_capacity for name, s in self.sites.items()}
        items.extend(QuayCalendar(site_cap).validate(solution.day, events))
        items.extend(EventReplayer().replay(solution))

        solution.metrics = compute_metrics(solution)
        if solution.metrics.driver_useful_occupancy < self.min_driver_occupancy:
            items.append(ValidationItem(solution.day, "Acceptabilité performance", CheckStatus.WARNING.value,
                                        f"Occupation utile moyenne chauffeur {solution.metrics.driver_useful_occupancy:.1%} < seuil {self.min_driver_occupancy:.0%}.",
                                        "", Severity.WARNING.value, "Relancer avec plus de passes de ré-optimisation, revoir fenêtres ou mutualisation."))
        else:
            items.append(ValidationItem(solution.day, "Acceptabilité performance", CheckStatus.OK.value,
                                        f"Occupation utile moyenne chauffeur {solution.metrics.driver_useful_occupancy:.1%} >= seuil {self.min_driver_occupancy:.0%}.",
                                        "", Severity.INFO.value, ""))

        blocking = [i for i in items if i.severity == Severity.BLOCKING.value and i.status == CheckStatus.KO.value]
        solution.hard_valid = len(blocking) == 0
        solution.performance_acceptable = solution.hard_valid and solution.metrics.driver_useful_occupancy >= self.min_driver_occupancy
        if not any(i.status == CheckStatus.OK.value for i in items):
            items.append(ValidationItem(solution.day, "Validation", CheckStatus.OK.value, "Validation terminée.", "", Severity.INFO.value, ""))
        solution.validation_items = items
        return solution
