from __future__ import annotations

from collections import defaultdict
import pandas as pd

from optiflux.domain.models import Solution
from optiflux.utils.time_utils import min_to_hhmm, duration_label
from optiflux.validation.validation_report import validation_items_to_df


def synthese_flotte(solutions: list[Solution]) -> pd.DataFrame:
    rows = []
    for sol in solutions:
        by_type = defaultdict(list)
        for r in sol.routes:
            by_type[r.vehicle.vehicle_type.name].append(r)
        for vt, routes in by_type.items():
            veh_ids = {r.vehicle.id for r in routes}
            km = sum(e.distance_km for r in routes for e in r.events if e.event_type == "Trajet")
            km_full = sum(e.distance_km for r in routes for e in r.events if e.event_type == "Trajet" and e.loaded_unit_ids_after)
            rows.append({
                "jour": sol.day,
                "type de véhicule": vt,
                "nombre utilisé": len(veh_ids),
                "nombre maximal autorisé": "Illimité",
                "nombre de tournées": len(routes),
                "kilomètres totaux": km,
                "kilomètres à plein": km_full,
                "kilomètres à vide": km - km_full,
                "temps total d’utilisation": sum(r.shift.duration_min for r in routes),
                "taux d’utilisation": sol.metrics.driver_useful_occupancy,
                "taux de remplissage moyen": sol.metrics.avg_fill_rate,
                "taux de remplissage maximal": sol.metrics.max_fill_rate,
                "nombre de désinfections": sum(1 for r in routes for e in r.events if e.event_type == "Désinfection"),
                "coût estimé": sum(sum(e.distance_km for e in r.events if e.event_type == "Trajet") * r.vehicle.vehicle_type.cost_per_km for r in routes),
                "émissions carbone estimées": sum(sum(e.distance_km for e in r.events if e.event_type == "Trajet") * r.vehicle.vehicle_type.carbon_per_km for r in routes),
            })
    return pd.DataFrame(rows)


def synthese_chauffeurs(solutions: list[Solution]) -> pd.DataFrame:
    rows = []
    for sol in solutions:
        for r in sol.routes:
            rows.append({
                "jour": sol.day,
                "poste chauffeur": r.shift.id,
                "véhicule": r.vehicle.id,
                "heure de début": min_to_hhmm(r.shift.start_min),
                "heure de fin": min_to_hhmm(r.shift.end_min),
                "durée exacte du poste": duration_label(r.shift.duration_min),
                "temps de prise de poste": r.shift.pre_shift_min,
                "temps de fin de poste": r.shift.post_shift_min,
                "pause": r.shift.break_duration_min,
                "temps de conduite": sum(e.duration_min for e in r.events if e.event_type == "Trajet"),
                "temps de manutention": sum(e.duration_min for e in r.events if e.event_type in {"Chargement", "Déchargement"}),
                "temps de mise à quai": sum(e.duration_min for e in r.events if e.event_type == "Mise à quai"),
                "temps de désinfection": sum(e.duration_min for e in r.events if e.event_type == "Désinfection"),
                "temps d’attente": sum(e.duration_min for e in r.events if e.event_type == "Attente"),
                "temps inoccupé à la base": sum(e.duration_min for e in r.events if e.event_type == "Temps inoccupé à la base"),
                "taux d’occupation utile": (sum(e.duration_min for e in r.events if e.event_type in {"Trajet", "Chargement", "Déchargement", "Mise à quai", "Désinfection"}) / r.shift.duration_min) if r.shift.duration_min else 0,
            })
    return pd.DataFrame(rows)


def tournees_vehicules(solutions: list[Solution]) -> pd.DataFrame:
    rows = []
    for sol in solutions:
        for r in sol.routes:
            for e in r.events:
                rows.append({
                    "jour": sol.day,
                    "véhicule": r.vehicle.id,
                    "type de véhicule": r.vehicle.vehicle_type.name,
                    "ordre de séquence": e.sequence,
                    "heure début opération": min_to_hhmm(e.start_min),
                    "heure fin opération": min_to_hhmm(e.end_min),
                    "site de départ": e.origin,
                    "site d’arrivée": e.destination or e.site,
                    "type d’opération": e.event_type,
                    "flux concernés": ", ".join(e.unit_ids),
                    "contenants chargés": e.containers_loaded,
                    "contenants déchargés": e.containers_unloaded,
                    "volume/surface chargée après opération": e.floor_area_after_m2,
                    "poids chargé après opération": e.weight_after_t,
                    "taux de remplissage après opération": e.fill_rate_after,
                    "trajet à vide ou à plein": "plein" if e.loaded_unit_ids_after else "vide",
                    "distance": e.distance_km,
                    "durée": e.duration_min,
                    "état sanitaire véhicule": e.sanitary_state,
                    "désinfection réalisée oui/non": "oui" if e.event_type == "Désinfection" else "non",
                })
    return pd.DataFrame(rows)


def planning_chauffeurs(solutions: list[Solution]) -> pd.DataFrame:
    rows = []
    for sol in solutions:
        for r in sol.routes:
            for e in r.events:
                rows.append({
                    "jour": sol.day,
                    "poste chauffeur": r.shift.id,
                    "véhicule": r.vehicle.id,
                    "ordre de séquence": e.sequence,
                    "heure début": min_to_hhmm(e.start_min),
                    "heure fin": min_to_hhmm(e.end_min),
                    "opération": e.event_type,
                    "lieu": e.site or e.destination or e.origin,
                    "flux concernés": ", ".join(e.unit_ids),
                    "commentaire": e.comment,
                })
    return pd.DataFrame(rows)


def planning_quais(solutions: list[Solution]) -> pd.DataFrame:
    rows = []
    for sol in solutions:
        for r in sol.routes:
            for e in r.events:
                if e.event_type in {"Mise à quai", "Chargement", "Déchargement"}:
                    rows.append({
                        "jour": sol.day,
                        "site": e.site,
                        "quai ou capacité simultanée": "capacité site",
                        "heure arrivée": min_to_hhmm(e.start_min),
                        "heure début mise à quai": min_to_hhmm(e.start_min),
                        "heure fin mise à quai": min_to_hhmm(e.end_min),
                        "heure départ": min_to_hhmm(e.end_min),
                        "véhicule": r.vehicle.id,
                        "chauffeur": r.shift.id,
                        "opération": e.event_type,
                        "flux concernés": ", ".join(e.unit_ids),
                    })
    return pd.DataFrame(rows)


def flux_transportes(solutions: list[Solution]) -> pd.DataFrame:
    rows = []
    for sol in solutions:
        delivered = {}
        collected = {}
        veh_route = {}
        for r in sol.routes:
            for e in r.events:
                if e.event_type == "Chargement":
                    for uid in e.unit_ids:
                        collected[uid] = e.end_min
                        veh_route[uid] = (r.vehicle.id, r.shift.id)
                if e.event_type == "Déchargement":
                    for uid in e.unit_ids:
                        delivered[uid] = e.end_min
        for uid, u in sol.units.items():
            if uid in delivered:
                veh, route_id = veh_route.get(uid, ("", ""))
                rows.append({
                    "jour": sol.day,
                    "identifiant flux": uid,
                    "origine": u.origin,
                    "destination": u.destination,
                    "fonction support": u.support_function,
                    "nature du flux": u.nature,
                    "contenant": u.container_name,
                    "nombre de contenants prévu": u.quantity,
                    "nombre de contenants transporté": u.quantity,
                    "véhicule": veh,
                    "tournée": route_id,
                    "heure collecte": min_to_hhmm(collected.get(uid)),
                    "heure livraison": min_to_hhmm(delivered.get(uid)),
                    "conformité horaire oui/non": "oui" if delivered.get(uid, 10**9) <= u.delivery_max else "non",
                })
    return pd.DataFrame(rows)


def flux_non_servis(solutions: list[Solution]) -> pd.DataFrame:
    rows = []
    for sol in solutions:
        served = {uid for r in sol.routes for e in r.events if e.event_type == "Déchargement" for uid in e.unit_ids}
        for uid, u in sol.units.items():
            if uid not in served:
                rows.append({"jour": sol.day, "identifiant flux": uid, "origine": u.origin, "destination": u.destination, "contenant": u.container_name, "quantité": u.quantity})
    return pd.DataFrame(rows)


def indicateurs(solutions: list[Solution]) -> pd.DataFrame:
    rows = []
    for sol in solutions:
        served = {uid for r in sol.routes for e in r.events if e.event_type == "Déchargement" for uid in e.unit_ids}
        rows.append({
            "jour": sol.day,
            "nombre total de flux": len(sol.units),
            "nombre total de contenants": sum(u.quantity for u in sol.units.values()),
            "nombre de flux servis": len(served),
            "taux de service": len(served) / len(sol.units) if sol.units else 0,
            "kilomètres totaux": sol.metrics.total_km,
            "kilomètres à plein": sol.metrics.loaded_km,
            "kilomètres à vide": sol.metrics.empty_km,
            "taux de kilomètres à vide": sol.metrics.empty_km / sol.metrics.total_km if sol.metrics.total_km else 0,
            "temps total de conduite": sol.metrics.driving_min,
            "temps total de manutention": sol.metrics.handling_min,
            "temps total de quai": sol.metrics.dock_min,
            "temps total d’attente": sol.metrics.waiting_min,
            "nombre de désinfections": sol.metrics.disinfections,
            "nombre de véhicules": len({r.vehicle.id for r in sol.routes}),
            "nombre de postes chauffeurs": len(sol.routes),
            "occupation utile chauffeur": sol.metrics.driver_useful_occupancy,
            "solution conforme contraintes dures": sol.hard_valid,
            "solution acceptable performance": sol.performance_acceptable,
            "passes de ré-optimisation": sol.reoptimization_passes,
            "message statut": sol.status_message,
        })
    return pd.DataFrame(rows)


def controles(solutions: list[Solution]) -> pd.DataFrame:
    return validation_items_to_df([item for sol in solutions for item in sol.validation_items])


def all_export_tables(solutions: list[Solution], import_report=None, input_errors=None) -> dict[str, pd.DataFrame]:
    tables = {
        "Synthèse flotte": synthese_flotte(solutions),
        "Synthèse chauffeurs": synthese_chauffeurs(solutions),
        "Tournées véhicules": tournees_vehicules(solutions),
        "Planning chauffeurs": planning_chauffeurs(solutions),
        "Planning quais": planning_quais(solutions),
        "Flux transportés": flux_transportes(solutions),
        "Flux non servis": flux_non_servis(solutions),
        "Contrôles contraintes": controles(solutions),
        "Indicateurs": indicateurs(solutions),
        "Dérogations horaires": pd.DataFrame(columns=["jour", "flux", "dérogation", "pénalité"]),
    }
    if import_report is not None:
        tables["Rapport import"] = pd.DataFrame(import_report)
    if input_errors is not None:
        tables["Erreurs données source"] = pd.DataFrame(input_errors)
    return tables
