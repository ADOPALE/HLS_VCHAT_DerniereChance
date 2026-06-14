from __future__ import annotations
import pandas as pd
import streamlit as st
from optiflux.export.export_tables import synthese_flotte, synthese_chauffeurs, indicateurs, tournees_vehicules, controles


def show_results(solutions):
    st.subheader("Résultats")
    if not solutions:
        st.info("Aucune simulation lancée.")
        return
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Jours simulés", len(solutions))
    c2.metric("Postes chauffeurs", sum(len(s.routes) for s in solutions))
    c3.metric("Km totaux", f"{sum(s.metrics.total_km for s in solutions):.1f}")
    avg_occ = sum(s.metrics.driver_useful_occupancy for s in solutions) / len(solutions)
    c4.metric("Occupation chauffeur", f"{avg_occ:.0%}")
    st.dataframe(indicateurs(solutions), use_container_width=True)
    with st.expander("Synthèse flotte"):
        st.dataframe(synthese_flotte(solutions), use_container_width=True)
    with st.expander("Synthèse chauffeurs"):
        st.dataframe(synthese_chauffeurs(solutions), use_container_width=True)
    with st.expander("Tournées véhicules"):
        st.dataframe(tournees_vehicules(solutions), use_container_width=True)
    with st.expander("Contrôles contraintes"):
        st.dataframe(controles(solutions), use_container_width=True)
