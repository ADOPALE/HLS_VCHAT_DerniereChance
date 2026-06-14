from __future__ import annotations
import pandas as pd
from optiflux.domain.models import ValidationItem


def validation_items_to_df(items: list[ValidationItem]) -> pd.DataFrame:
    return pd.DataFrame([{
        "jour": i.day,
        "type de contrôle": i.check_type,
        "statut": i.status,
        "détail": i.detail,
        "flux ou véhicule concerné": i.object_id,
        "gravité": i.severity,
        "action recommandée": i.action,
    } for i in items])
