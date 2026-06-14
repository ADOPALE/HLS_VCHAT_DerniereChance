from __future__ import annotations
import pandas as pd
import streamlit as st
from optiflux.domain.enums import Severity


def show_validation(solutions):
    st.subheader("Validation indépendante")
    rows = [i.__dict__ for s in solutions for i in s.validation_items]
    if not rows:
        st.info("Pas encore de validation.")
        return
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)
    blocking = df[(df["severity"] == Severity.BLOCKING.value) & (df["status"] == "KO")]
    if not blocking.empty:
        st.error("La solution contient des erreurs bloquantes. Elle ne doit pas être utilisée comme solution conforme.")
    elif all(s.performance_acceptable for s in solutions):
        st.success("Solution conforme et acceptable au regard du seuil d'occupation chauffeur.")
    else:
        st.warning("Solution conforme sur contraintes dures, mais non acceptable au regard du seuil de performance.")
