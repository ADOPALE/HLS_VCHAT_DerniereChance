from __future__ import annotations

from optiflux.domain.models import TransportUnit
from optiflux.optimization.scoring import can_mix


def sanitary_group_compatible(units: list[TransportUnit]) -> bool:
    for i, a in enumerate(units):
        for b in units[i+1:]:
            if not can_mix(a, b):
                return False
    return True
