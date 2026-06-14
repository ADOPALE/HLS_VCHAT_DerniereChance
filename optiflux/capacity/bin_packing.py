from __future__ import annotations

from dataclasses import dataclass
import math

from optiflux.domain.models import ContainerType, VehicleType


@dataclass
class PackingResult:
    feasible: bool
    used_area: float
    fill_rate: float
    effective_items: int
    reason: str = ""


def effective_footprints(container: ContainerType, quantity: int) -> int:
    """Nombre d'empreintes au sol après empilement autorisé."""
    return int(math.ceil(quantity / max(1, container.max_stack)))


def _fits_rect(w: float, h: float, W: float, H: float) -> bool:
    return (w <= W and h <= H) or (h <= W and w <= H)


def shelf_pack_2d(container: ContainerType, vehicle: VehicleType, quantity: int) -> PackingResult:
    """Heuristique 2D first-fit shelf avec rotation 90° possible.

    Elle est volontairement conservative : si elle échoue, cela ne prouve pas que le chargement est impossible,
    mais elle évite de produire des solutions dont le chargement n'est pas crédible.
    """
    n = effective_footprints(container, quantity)
    if n <= 0:
        return PackingResult(True, 0.0, 0.0, 0)
    L, W = vehicle.length, vehicle.width
    a, b = container.length, container.width
    if not _fits_rect(a, b, L, W):
        return PackingResult(False, 0.0, 0.0, n, f"Le contenant {container.name} ne tient pas dans {vehicle.name}, même avec rotation.")

    shelves: list[dict[str, float]] = []  # y, height, used_width
    used_height = 0.0
    # Tous les items sont identiques; on essaie l'orientation qui maximise le nombre par étagère.
    orientations = [(a, b), (b, a)]
    orientations = sorted(orientations, key=lambda x: math.floor(L / x[0]) * math.floor(W / x[1]), reverse=True)
    for _ in range(n):
        placed = False
        for shelf in shelves:
            for iw, ih in orientations:
                if ih <= shelf["height"] and shelf["used_width"] + iw <= L:
                    shelf["used_width"] += iw
                    placed = True
                    break
            if placed:
                break
        if not placed:
            best = None
            for iw, ih in orientations:
                if iw <= L and used_height + ih <= W:
                    best = (iw, ih)
                    break
            if best is None:
                return PackingResult(False, n * container.footprint_area, min(1.0, n * container.footprint_area / max(vehicle.floor_area, 1e-9)), n, "Surface 2D insuffisante selon l'heuristique de placement.")
            iw, ih = best
            shelves.append({"height": ih, "used_width": iw})
            used_height += ih
    used_area = n * container.footprint_area
    fill = used_area / max(vehicle.floor_area, 1e-9)
    if fill > vehicle.occupancy_rate + 1e-9:
        return PackingResult(False, used_area, fill, n, f"Taux d'occupation {fill:.0%} supérieur au plafond {vehicle.occupancy_rate:.0%}.")
    return PackingResult(True, used_area, fill, n)


def pack_multiple(container_quantities: list[tuple[ContainerType, int]], vehicle: VehicleType) -> PackingResult:
    """Placement multi-contenants approximatif par répétition des empreintes; utile pour valider un chargement mixte."""
    rects: list[tuple[float, float, float]] = []
    used_area = 0.0
    for container, qty in container_quantities:
        n = effective_footprints(container, qty)
        for _ in range(n):
            rects.append((max(container.length, container.width), min(container.length, container.width), container.footprint_area))
            used_area += container.footprint_area
    rects.sort(reverse=True)
    if used_area / max(vehicle.floor_area, 1e-9) > vehicle.occupancy_rate + 1e-9:
        return PackingResult(False, used_area, used_area / max(vehicle.floor_area, 1e-9), len(rects), "Taux d'occupation surface dépassé.")
    shelves: list[dict[str, float]] = []
    used_height = 0.0
    for a, b, _ in rects:
        placed = False
        for shelf in shelves:
            for iw, ih in [(a, b), (b, a)]:
                if ih <= shelf["height"] and shelf["used_width"] + iw <= vehicle.length:
                    shelf["used_width"] += iw
                    placed = True
                    break
            if placed:
                break
        if not placed:
            for iw, ih in [(a, b), (b, a)]:
                if iw <= vehicle.length and used_height + ih <= vehicle.width:
                    shelves.append({"height": ih, "used_width": iw})
                    used_height += ih
                    placed = True
                    break
        if not placed:
            return PackingResult(False, used_area, used_area / max(vehicle.floor_area, 1e-9), len(rects), "Placement 2D multi-contenants impossible selon l'heuristique.")
    return PackingResult(True, used_area, used_area / max(vehicle.floor_area, 1e-9), len(rects))
