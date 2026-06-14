from __future__ import annotations
import pandas as pd
import streamlit as st
from optiflux.domain.models import ValidationItem
from optiflux.domain.enums import Severity


def show_import_report(normalization_changes, validation_items: list[ValidationItem]):
    st.subheader("Rapport d'import")
    blocking = [i for i in validation_items if i.severity == Severity.BLOCKING.value]
    warnings = [i for i in validation_items if i.severity == Severity.WARNING.value]
    c1, c2, c3 = st.columns(3)
    c1.metric("Erreurs bloquantes", len(blocking))
    c2.metric("Alertes", len(warnings))
    c3.metric("Corrections automatiques", len(normalization_changes))
    if validation_items:
        st.dataframe(pd.DataFrame([i.__dict__ for i in validation_items]), use_container_width=True)
    if normalization_changes:
        with st.expander("Corrections de libellés réalisées automatiquement"):
            st.dataframe(pd.DataFrame(normalization_changes), use_container_width=True)
