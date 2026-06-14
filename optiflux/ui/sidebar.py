from __future__ import annotations
import streamlit as st
from optiflux.config.defaults import DAYS, DEFAULT_OCCUPANCY_RATE, DEFAULT_REOPTIMIZATION_PASSES, MIN_DRIVER_USEFUL_OCCUPANCY


def render_sidebar():
    st.sidebar.header("Paramètres de simulation")
    days = st.sidebar.multiselect("Jours à optimiser", DAYS, default=["Lundi"])
    circulation = st.sidebar.slider("Facteur circulation", min_value=0, max_value=100, value=0, step=5) / 100
    occupancy_rate = st.sidebar.slider("Taux d'occupation maximal surface véhicule", min_value=50, max_value=100, value=int(DEFAULT_OCCUPANCY_RATE * 100), step=5) / 100
    shift_duration = st.sidebar.number_input("Durée de poste chauffeur (minutes)", min_value=60, max_value=720, value=450, step=15)
    break_duration = st.sidebar.number_input("Durée de pause (minutes)", min_value=0, max_value=90, value=30, step=5)
    pre_shift = st.sidebar.number_input("Prise de poste (minutes)", min_value=0, max_value=60, value=15, step=5)
    post_shift = st.sidebar.number_input("Fin de poste (minutes)", min_value=0, max_value=60, value=10, step=5)
    disinfection = st.sidebar.number_input("Désinfection à HSJ (minutes)", min_value=0, max_value=120, value=15, step=5)
    reopt_passes = st.sidebar.slider("Passes de ré-optimisation", min_value=1, max_value=15, value=DEFAULT_REOPTIMIZATION_PASSES)
    min_driver_occupancy = st.sidebar.slider("Seuil occupation utile chauffeur acceptable", min_value=50, max_value=100, value=int(MIN_DRIVER_USEFUL_OCCUPANCY*100), step=5) / 100
    return {
        "days": days,
        "circulation_factor": circulation,
        "occupancy_rate": occupancy_rate,
        "shift_duration_min": int(shift_duration),
        "break_duration_min": int(break_duration),
        "pre_shift_min": int(pre_shift),
        "post_shift_min": int(post_shift),
        "disinfection_min": int(disinfection),
        "disinfection_site": "HSJ",
        "reoptimization_passes": int(reopt_passes),
        "min_driver_occupancy": min_driver_occupancy,
    }
