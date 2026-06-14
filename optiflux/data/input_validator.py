from __future__ import annotations

import pandas as pd
from optiflux.config.columns import REQUIRED_SHEETS, FLOW, SITE, VEHICLE, CONTAINER
from optiflux.config.defaults import DAY_QUANTITY_COLUMNS, SPECIAL_QUAY_CAPACITY, DEFAULT_QUAY_CAPACITY
from optiflux.domain.models import ValidationItem
from optiflux.domain.enums import Severity, CheckStatus
from optiflux.utils.time_utils import parse_time_to_min
from optiflux.data.excel_loader import WorkbookData


def _missing_columns(df: pd.DataFrame, required: list[str]) -> list[str]:
    return [c for c in required if c not in df.columns]


def validate_input(workbook: WorkbookData) -> list[ValidationItem]:
    items: list[ValidationItem] = []
    sheets = workbook.normalized_sheets
    for sheet in REQUIRED_SHEETS:
        if sheet not in sheets:
            items.append(ValidationItem("", "Onglet attendu", CheckStatus.KO.value, f"Onglet absent : {sheet}", sheet, Severity.BLOCKING.value, "Ajouter ou renommer l'onglet."))
    if any(i.severity == Severity.BLOCKING.value for i in items):
        return items

    flow_df = sheets["M flux"]
    sites_df = sheets["param Sites"]
    vehicles_df = sheets["param Véhicules"]
    containers_df = sheets["param Contenants"]

    required_flow = list(FLOW.values()) + list(DAY_QUANTITY_COLUMNS.values())
    required_site = list(SITE.values())
    required_vehicle = list(VEHICLE.values())
    required_container = list(CONTAINER.values())

    for sheet, df, required in [
        ("M flux", flow_df, required_flow),
        ("param Sites", sites_df, required_site),
        ("param Véhicules", vehicles_df, required_vehicle),
        ("param Contenants", containers_df, required_container),
    ]:
        for col in _missing_columns(df, required):
            items.append(ValidationItem("", "Colonne obligatoire", CheckStatus.KO.value, f"Colonne absente dans {sheet} : {col}", col, Severity.BLOCKING.value, "Compléter le fichier source."))

    if any(i.severity == Severity.BLOCKING.value for i in items):
        return items

    sites = {str(v).strip() for v in sites_df[SITE["name"]].dropna()}
    containers = {str(v).strip() for v in containers_df[CONTAINER["name"]].dropna()}
    matrix_sites = {a for a, _ in workbook.matrices.durations.keys()} | {b for _, b in workbook.matrices.durations.keys()}

    for idx, row in flow_df.iterrows():
        row_no = int(idx) + 2
        origin = str(row.get(FLOW["origin"], "")).strip()
        dest = str(row.get(FLOW["destination"], "")).strip()
        container = str(row.get(FLOW["container"], "")).strip()
        pickup = parse_time_to_min(row.get(FLOW["pickup_min"]))
        delivery = parse_time_to_min(row.get(FLOW["delivery_max"]))
        if origin not in sites:
            items.append(ValidationItem("", "Site flux", CheckStatus.KO.value, f"Ligne {row_no}: site de départ inconnu : {origin}", str(row_no), Severity.BLOCKING.value, "Corriger le libellé du site ou param Sites."))
        if dest not in sites:
            items.append(ValidationItem("", "Site flux", CheckStatus.KO.value, f"Ligne {row_no}: site de destination inconnu : {dest}", str(row_no), Severity.BLOCKING.value, "Corriger le libellé du site ou param Sites."))
        if origin and origin not in matrix_sites:
            items.append(ValidationItem("", "Matrice durée", CheckStatus.KO.value, f"Ligne {row_no}: site absent des matrices : {origin}", str(row_no), Severity.BLOCKING.value, "Compléter les matrices durée et distance."))
        if dest and dest not in matrix_sites:
            items.append(ValidationItem("", "Matrice durée", CheckStatus.KO.value, f"Ligne {row_no}: site absent des matrices : {dest}", str(row_no), Severity.BLOCKING.value, "Compléter les matrices durée et distance."))
        if container not in containers:
            items.append(ValidationItem("", "Contenant", CheckStatus.KO.value, f"Ligne {row_no}: contenant inconnu : {container}", str(row_no), Severity.BLOCKING.value, "Corriger la nature de contenant."))
        active = False
        for col in DAY_QUANTITY_COLUMNS.values():
            try:
                active = active or float(row.get(col, 0) or 0) > 0
            except Exception:
                pass
        if active and (pickup is None or delivery is None):
            items.append(ValidationItem("", "Fenêtre horaire", CheckStatus.KO.value, f"Ligne {row_no}: flux actif sans heure min de départ ou heure max de livraison.", str(row_no), Severity.BLOCKING.value, "Renseigner les deux colonnes horaires; les colonnes plage/fréquence sont ignorées."))
        if pickup is not None and delivery is not None and pickup >= delivery:
            items.append(ValidationItem("", "Fenêtre horaire", CheckStatus.KO.value, f"Ligne {row_no}: heure min de départ >= heure max de livraison.", str(row_no), Severity.BLOCKING.value, "Élargir ou corriger la fenêtre horaire."))

    for idx, row in vehicles_df.iterrows():
        row_no = int(idx) + 2
        name = str(row.get(VEHICLE["name"], "")).strip()
        initial = str(row.get(VEHICLE["initial_site"], "")).strip()
        payload = row.get(VEHICLE["payload"])
        length = row.get(VEHICLE["length"])
        width = row.get(VEHICLE["width"])
        if not initial or initial.lower() == "nan":
            items.append(ValidationItem("", "Véhicule", CheckStatus.KO.value, f"Ligne {row_no}: véhicule {name} sans stationnement initial.", name, Severity.BLOCKING.value, "Renseigner le stationnement initial."))
        if initial and initial not in sites:
            items.append(ValidationItem("", "Véhicule", CheckStatus.KO.value, f"Ligne {row_no}: stationnement initial inconnu : {initial}.", name, Severity.BLOCKING.value, "Corriger param Véhicules ou param Sites."))
        try:
            if float(payload) <= 0 or float(length) <= 0 or float(width) <= 0:
                raise ValueError
        except Exception:
            items.append(ValidationItem("", "Capacité véhicule", CheckStatus.KO.value, f"Ligne {row_no}: capacité ou dimensions invalides pour {name}.", name, Severity.BLOCKING.value, "Renseigner longueur, largeur et charge utile."))

    for idx, row in containers_df.iterrows():
        row_no = int(idx) + 2
        name = str(row.get(CONTAINER["name"], "")).strip()
        try:
            if float(row.get(CONTAINER["length"])) <= 0 or float(row.get(CONTAINER["width"])) <= 0:
                raise ValueError
        except Exception:
            items.append(ValidationItem("", "Dimensions contenant", CheckStatus.KO.value, f"Ligne {row_no}: dimensions invalides pour {name}.", name, Severity.BLOCKING.value, "Renseigner longueur et largeur."))

    if not items:
        items.append(ValidationItem("", "Contrôle import", CheckStatus.OK.value, "Aucune erreur bloquante détectée.", "", Severity.INFO.value, ""))
    return items


def has_blocking_errors(items: list[ValidationItem]) -> bool:
    return any(i.severity == Severity.BLOCKING.value and i.status == CheckStatus.KO.value for i in items)
