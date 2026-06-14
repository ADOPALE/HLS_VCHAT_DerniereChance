from __future__ import annotations

from collections import defaultdict
from copy import deepcopy

from optiflux.domain.models import TransportUnit, VehicleType, VehicleInstance, DriverShift, Route, RouteEvent
from optiflux.domain.enums import EventType
from optiflux.capacity.capacity_checker import can_units_fit
from optiflux.optimization.scoring import can_mix, group_compatibility_score
from optiflux.utils.matrix_utils import MatrixRepository


def handling_time(vehicle: VehicleType, site_has_quay: bool, quantity: int) -> float:
    per = vehicle.handling_with_quay_min_per_container if site_has_quay else vehicle.handling_no_quay_min_per_container
    return max(0.0, per * quantity)


def units_compatible_together(units: list[TransportUnit]) -> bool:
    for i, a in enumerate(units):
        for b in units[i+1:]:
            if not can_mix(a, b):
                return False
    groups = {u.mutualized_group for u in units if u.mutualized_group}
    if len(groups) > 1:
        return False
    return True


class RouteBuilder:
    def __init__(self, matrices: MatrixRepository, sites: dict, containers: dict, disinfection_site: str = "HSJ", disinfection_min: int = 15):
        self.matrices = matrices
        self.sites = sites
        self.containers = containers
        self.disinfection_site = disinfection_site
        self.disinfection_min = disinfection_min

    def _site_has_quay(self, site: str) -> bool:
        return bool(self.sites.get(site).has_quay) if site in self.sites else True

    def _add_event(self, route: Route, event_type: EventType, start: int, end: int, sequence_ref: list[int], **kwargs) -> None:
        route.events.append(RouteEvent(
            day=route.day,
            vehicle_id=route.vehicle.id,
            shift_id=route.shift.id,
            sequence=sequence_ref[0],
            event_type=event_type.value,
            start_min=int(round(start)),
            end_min=int(round(end)),
            duration_min=float(end - start),
            **kwargs,
        ))
        sequence_ref[0] += 1

    def build_route(self, day: str, vehicle: VehicleInstance, shift: DriverShift, units: list[TransportUnit]) -> Route:
        route = Route(day=day, vehicle=vehicle, shift=shift, unit_ids=[u.id for u in units])
        if not units:
            return route
        vt = vehicle.vehicle_type
        for u in units:
            if u.origin not in vt.compatible_sites or u.destination not in vt.compatible_sites:
                route.feasible = False
                route.infeasibility_reasons.append(f"{vt.name} incompatible avec {u.origin} ou {u.destination}.")
            if u.container_name not in vt.compatible_containers:
                route.feasible = False
                route.infeasibility_reasons.append(f"{vt.name} incompatible avec {u.container_name}.")
        if not units_compatible_together(units):
            route.feasible = False
            route.infeasibility_reasons.append("Unités incompatibles en transport mixte ou groupes mutualisés différents.")
            return route

        sequence = [1]
        time = shift.start_min
        location = shift.initial_site
        loaded: list[TransportUnit] = []
        unpicked = sorted(units, key=lambda u: (u.pickup_min, u.delivery_max))
        delivered: set[str] = set()
        sanitary_state = "NEUTRE"
        break_taken = False
        bw_start, bw_end = shift.break_window
        self._add_event(route, EventType.START_SHIFT, time, time + shift.pre_shift_min, sequence, site=location, sanitary_state=sanitary_state)
        time += shift.pre_shift_min

        def travel_to(dest: str, load_state: list[TransportUnit]):
            nonlocal time, location
            if location == dest:
                return
            dist = self.matrices.distance(location, dest)
            dur = self.matrices.duration(location, dest)
            self._add_event(route, EventType.TRAVEL, time, time + dur, sequence, origin=location, destination=dest, site=dest,
                            loaded_unit_ids_after=[u.id for u in load_state], distance_km=dist, sanitary_state=sanitary_state)
            time += int(round(dur))
            location = dest

        def maybe_break(force: bool = False) -> bool:
            nonlocal time, location, break_taken
            if break_taken:
                return True
            if not force and time < bw_start:
                return True
            if time > bw_end:
                route.feasible = False
                route.infeasibility_reasons.append("Pause impossible dans la fenêtre autorisée.")
                return False
            # retour au dépôt obligatoire pour pause, avec chargement conservé si nécessaire
            travel_to(shift.initial_site, loaded)
            start = max(time, bw_start)
            if start + shift.break_duration_min > bw_end:
                route.feasible = False
                route.infeasibility_reasons.append("Pause impossible dans la fenêtre autorisée après retour dépôt.")
                return False
            if start > time:
                self._add_event(route, EventType.WAIT, time, start, sequence, site=location, loaded_unit_ids_after=[u.id for u in loaded], sanitary_state=sanitary_state)
            self._add_event(route, EventType.BREAK, start, start + shift.break_duration_min, sequence, site=location, loaded_unit_ids_after=[u.id for u in loaded], sanitary_state=sanitary_state)
            time = start + shift.break_duration_min
            break_taken = True
            return True

        while unpicked or loaded:
            if time > shift.work_end_min:
                route.feasible = False
                route.infeasibility_reasons.append("La tournée dépasse la fin de temps productif du poste.")
                return route
            if time >= bw_start and not break_taken:
                # on essaye de prendre la pause dès que possible sauf livraison très urgente
                if not loaded or min(u.delivery_max for u in loaded) - time > 45:
                    maybe_break()

            # Livraison prioritaire si une unité chargée approche de son échéance ou si rien à collecter.
            if loaded and (not unpicked or min(u.delivery_max for u in loaded) <= time + 45):
                target = min(loaded, key=lambda u: u.delivery_max)
                travel_to(target.destination, loaded)
                dock = vt.dock_time_min
                self._add_event(route, EventType.DOCK, time, time + dock, sequence, site=location, unit_ids=[target.id], loaded_unit_ids_after=[u.id for u in loaded], sanitary_state=sanitary_state)
                time += int(round(dock))
                qty = target.quantity
                unload = handling_time(vt, self._site_has_quay(location), qty)
                loaded_after = [u for u in loaded if u.id != target.id]
                ok, reason, weight, area, fill = can_units_fit(loaded_after, self.containers, vt)
                self._add_event(route, EventType.UNLOAD, time, time + unload, sequence, site=location, unit_ids=[target.id],
                                containers_unloaded=qty, loaded_unit_ids_after=[u.id for u in loaded_after],
                                weight_after_t=weight, floor_area_after_m2=area, fill_rate_after=fill,
                                sanitary_state=sanitary_state)
                time += int(round(unload))
                if time > target.delivery_max:
                    route.feasible = False
                    route.infeasibility_reasons.append(f"Livraison hors délai pour {target.id}.")
                loaded = loaded_after
                delivered.add(target.id)
                if not loaded and sanitary_state == "SALE_EN_CHARGE":
                    sanitary_state = "SALE_APRES_DECHARGEMENT"
                continue

            if unpicked:
                # Choix look-forward : unité avec échéance proche, puis candidats groupables même origine/destination.
                candidate = min(unpicked, key=lambda u: (u.delivery_max, max(0, u.pickup_min - time), u.pickup_min))
                if sanitary_state == "SALE_APRES_DECHARGEMENT" and candidate.sanitary == "Propre":
                    travel_to(self.disinfection_site, loaded)
                    if location != self.disinfection_site:
                        route.feasible = False
                        route.infeasibility_reasons.append("Désinfection impossible hors HSJ.")
                        return route
                    self._add_event(route, EventType.DISINFECTION, time, time + self.disinfection_min, sequence, site=location, sanitary_state="DESINFECTE")
                    time += self.disinfection_min
                    sanitary_state = "DESINFECTE"
                travel_to(candidate.origin, loaded)
                if time < candidate.pickup_min:
                    # attendre un peu peut permettre de mieux grouper.
                    self._add_event(route, EventType.WAIT, time, candidate.pickup_min, sequence, site=location, loaded_unit_ids_after=[u.id for u in loaded], sanitary_state=sanitary_state)
                    time = candidate.pickup_min
                # Groupe de chargement sur même origine et compatible.
                same_origin = [u for u in unpicked if u.origin == candidate.origin and u.pickup_min <= time + 30]
                same_origin.sort(key=lambda u: (-group_compatibility_score(candidate, u), u.delivery_max))
                to_load: list[TransportUnit] = []
                for u in same_origin:
                    trial = loaded + to_load + [u]
                    if all(can_mix(x, y) for i, x in enumerate(trial) for y in trial[i+1:]):
                        ok, _, _, _, _ = can_units_fit(trial, self.containers, vt)
                        if ok:
                            to_load.append(u)
                if not to_load:
                    route.feasible = False
                    route.infeasibility_reasons.append(f"Impossible de charger {candidate.id} dans {vt.name}.")
                    return route
                dock = vt.dock_time_min
                self._add_event(route, EventType.DOCK, time, time + dock, sequence, site=location, unit_ids=[u.id for u in to_load], loaded_unit_ids_after=[u.id for u in loaded], sanitary_state=sanitary_state)
                time += int(round(dock))
                qty = sum(u.quantity for u in to_load)
                load_dur = handling_time(vt, self._site_has_quay(location), qty)
                loaded.extend(to_load)
                ok, reason, weight, area, fill = can_units_fit(loaded, self.containers, vt)
                self._add_event(route, EventType.LOAD, time, time + load_dur, sequence, site=location, unit_ids=[u.id for u in to_load],
                                containers_loaded=qty, loaded_unit_ids_after=[u.id for u in loaded],
                                weight_after_t=weight, floor_area_after_m2=area, fill_rate_after=fill,
                                sanitary_state=sanitary_state)
                time += int(round(load_dur))
                if not ok:
                    route.feasible = False
                    route.infeasibility_reasons.append(reason)
                    return route
                for u in to_load:
                    unpicked = [x for x in unpicked if x.id != u.id]
                if any(u.sanitary == "Sale" for u in to_load):
                    sanitary_state = "SALE_EN_CHARGE"
                elif sanitary_state in {"NEUTRE", "DESINFECTE"}:
                    sanitary_state = "PROPRE_EN_CHARGE"
                continue

        if not break_taken:
            maybe_break(force=True)
        travel_to(shift.initial_site, loaded)
        if time > shift.work_end_min:
            route.feasible = False
            route.infeasibility_reasons.append("Retour au dépôt trop tardif pour la fin de poste.")
            return route
        if time < shift.work_end_min:
            self._add_event(route, EventType.IDLE_BASE, time, shift.work_end_min, sequence, site=shift.initial_site, sanitary_state=sanitary_state)
            time = shift.work_end_min
        self._add_event(route, EventType.END_SHIFT, time, shift.end_min, sequence, site=shift.initial_site, sanitary_state=sanitary_state)
        return route
