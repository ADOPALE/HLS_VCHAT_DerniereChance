from __future__ import annotations

from optiflux.domain.models import Solution, ValidationItem
from optiflux.domain.enums import CheckStatus, Severity


class EventReplayer:
    """Rejoue une solution événement par événement pour contrôler les incohérences temporelles simples."""
    def replay(self, solution: Solution) -> list[ValidationItem]:
        items: list[ValidationItem] = []
        for route in solution.routes:
            prev_end = None
            location = route.shift.initial_site
            if not route.events:
                items.append(ValidationItem(solution.day, "Séquence", CheckStatus.KO.value, f"Route vide {route.vehicle.id}.", route.vehicle.id, Severity.BLOCKING.value, "Recalculer la tournée."))
                continue
            for e in sorted(route.events, key=lambda x: x.sequence):
                if prev_end is not None and e.start_min < prev_end:
                    items.append(ValidationItem(solution.day, "Séquence", CheckStatus.KO.value, f"Chevauchement temporel sur {route.vehicle.id}.", route.vehicle.id, Severity.BLOCKING.value, "Réordonner les événements."))
                if e.end_min < e.start_min:
                    items.append(ValidationItem(solution.day, "Séquence", CheckStatus.KO.value, f"Durée négative sur {e.event_type}.", route.vehicle.id, Severity.BLOCKING.value, "Corriger le calcul."))
                prev_end = e.end_min
            if route.events[0].site != route.shift.initial_site or route.events[-1].site != route.shift.initial_site:
                items.append(ValidationItem(solution.day, "Stationnement initial", CheckStatus.KO.value, f"{route.vehicle.id} ne commence/termine pas au dépôt.", route.vehicle.id, Severity.BLOCKING.value, "Forcer retour dépôt."))
        if not items:
            items.append(ValidationItem(solution.day, "Rejeu événements", CheckStatus.OK.value, "Séquences temporelles cohérentes.", "", Severity.INFO.value, ""))
        return items
