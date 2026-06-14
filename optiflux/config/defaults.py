from __future__ import annotations

DEFAULT_OCCUPANCY_RATE = 0.85
DEFAULT_QUAY_CAPACITY = 3
SPECIAL_QUAY_CAPACITY = {"HLS": 7}
DEFAULT_SHIFT_STARTS = ["06:00", "13:30"]
DEFAULT_SHIFT_DURATION_MIN = 450  # 7h30
DEFAULT_BREAK_DURATION_MIN = 30
DEFAULT_PRE_SHIFT_MIN = 15
DEFAULT_POST_SHIFT_MIN = 10
DEFAULT_DISINFECTION_MIN = 15
DEFAULT_MAX_WAIT_FOR_GROUPING_MIN = 30
DEFAULT_REOPTIMIZATION_PASSES = 6
MIN_DRIVER_USEFUL_OCCUPANCY = 0.80
LOCAL_EXACT_MAX_UNITS = 7
DAYS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
DAY_QUANTITY_COLUMNS = {day: f"Quantité {day}" for day in DAYS}
IGNORED_FLOW_COLUMNS = [
    "Plage horaire en semaine (Heure début)",
    "Plage horaire en semaine (Heure fin)",
    "Plage horaire en Week END (Heure début)",
    "Plage horaire en Week END (Heure fin)",
    "Fréquence (nb de passage par jour) et horaires en semaine2",
    "Fréquence (nb de passage par jour) et horaires en WE3",
    "Cadence de prod (nb de chariot par durée/ J1 - tous les chariots sont fait la veille et peuvent partir en même temps ou aléat)",
    "Urgence / flux prioritaire (Oui/Non)",
]
