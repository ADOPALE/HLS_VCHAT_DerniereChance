from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


def _json_default(obj: Any):
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, set):
        return list(obj)
    return str(obj)


def save_simulation(solutions, folder: str = "simulations", name: str | None = None) -> Path:
    path = Path(folder)
    path.mkdir(parents=True, exist_ok=True)
    name = name or datetime.now().strftime("simulation_%Y%m%d_%H%M%S.json")
    file = path / name
    with open(file, "w", encoding="utf-8") as f:
        json.dump(solutions, f, default=_json_default, ensure_ascii=False, indent=2)
    return file


def save_simulation_bytes(solutions) -> bytes:
    return json.dumps(solutions, default=_json_default, ensure_ascii=False, indent=2).encode("utf-8")
