from __future__ import annotations

from collections import defaultdict
from optiflux.domain.models import RouteEvent, ValidationItem
from optiflux.domain.enums import CheckStatus, Severity


class QuayCalendar:
    def __init__(self, site_capacities: dict[str, int]):
        self.site_capacities = site_capacities

    def validate(self, day: str, events: list[RouteEvent]) -> list[ValidationItem]:
        items: list[ValidationItem] = []
        by_site: dict[str, list[tuple[int, int, str]]] = defaultdict(list)
        for e in events:
            if e.event_type in {"Mise à quai", "Chargement", "Déchargement"} and e.site:
                by_site[e.site].append((e.start_min, e.end_min, e.vehicle_id))
        for site, intervals in by_site.items():
            cap = self.site_capacities.get(site, 3)
            points = sorted({t for a, b, _ in intervals for t in (a, b)})
            for t in points:
                concurrent = {v for a, b, v in intervals if a <= t < b}
                if len(concurrent) > cap:
                    items.append(ValidationItem(day, "Capacité quais", CheckStatus.KO.value, f"{site}: {len(concurrent)} véhicules simultanés pour une capacité de {cap}.", site, Severity.BLOCKING.value, "Décaler une opération de quai."))
        if not items:
            items.append(ValidationItem(day, "Capacité quais", CheckStatus.OK.value, "Capacités simultanées respectées.", "", Severity.INFO.value, ""))
        return items
