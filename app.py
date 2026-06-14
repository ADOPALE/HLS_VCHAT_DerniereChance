from __future__ import annotations

import streamlit as st
import pandas as pd

from optiflux.data.excel_loader import load_workbook
from optiflux.data.input_validator import validate_input, has_blocking_errors
from optiflux.data.preprocessing import build_vehicles, build_sites, build_containers, build_flows, active_flows_for_day, create_units_for_day
from optiflux.optimization.fleet_search import FleetSearchEngine
from optiflux.export.excel_exporter import export_solutions_to_excel_bytes
from optiflux.reporting.ppt_exporter import export_solutions_to_pptx_bytes
from optiflux.storage.simulation_store import save_simulation_bytes
from optiflux.ui.sidebar import render_sidebar
from optiflux.ui.import_view import show_import_report
from optiflux.ui.flow_analysis_view import show_flow_analysis
from optiflux.ui.optimization_view import progress_callback_factory
from optiflux.ui.results_view import show_results
from optiflux.ui.validation_view import show_validation

st.set_page_config(page_title="OptiFLUX", page_icon="🚚", layout="wide")
st.title("🚚 OptiFLUX — Optimisation logistique hospitalière")
st.caption("Import Excel, contrôles de données, optimisation heuristique ré-optimisée, validation indépendante, exports Excel / PowerPoint.")

settings = render_sidebar()
uploaded = st.file_uploader("Importer le fichier Excel de paramétrage", type=["xlsx"])

if "solutions" not in st.session_state:
    st.session_state.solutions = []

if uploaded is None:
    st.info("Chargez un fichier Excel pour démarrer.")
    st.stop()

with st.spinner("Lecture et normalisation du classeur..."):
    workbook = load_workbook(uploaded, circulation_factor=settings["circulation_factor"])
    validation_items = validate_input(workbook)

show_import_report(workbook.normalization_report.changes, validation_items)

if has_blocking_errors(validation_items):
    st.error("Des erreurs bloquantes empêchent le lancement de l'optimisation. Corrigez le fichier source puis réimportez-le.")
    st.stop()

sheets = workbook.normalized_sheets
vehicle_names = [str(v).strip() for v in sheets["param Véhicules"]["Types"].dropna()]
containers = build_containers(sheets["param Contenants"])
vehicles = build_vehicles(sheets["param Véhicules"], sheets["param Sites"], occupancy_rate=settings["occupancy_rate"])
sites = build_sites(sheets["param Sites"], list(vehicles.keys()))
flows = build_flows(sheets["M flux"])

st.sidebar.subheader("Périmètre")
all_functions = sorted({f.support_function for f in flows if f.support_function})
selected_functions = st.sidebar.multiselect("Fonctions support à inclure", all_functions, default=all_functions)
all_vehicle_types = sorted(vehicles.keys())
selected_vehicle_types = st.sidebar.multiselect("Types de véhicules autorisés", all_vehicle_types, default=all_vehicle_types)
vehicles_selected = {k: v for k, v in vehicles.items() if k in selected_vehicle_types}

show_flow_analysis(flows)

st.divider()
st.subheader("Contrôles préalables de faisabilité")
if not selected_vehicle_types:
    st.error("Sélectionnez au moins un type de véhicule.")
    st.stop()
if not settings["days"]:
    st.error("Sélectionnez au moins un jour à optimiser.")
    st.stop()

pre_rows = []
for day in settings["days"]:
    day_flows = active_flows_for_day(flows, day, selected_functions)
    units = create_units_for_day(day_flows, day, containers, vehicles_selected)
    pre_rows.append({"jour": day, "flux actifs": len(day_flows), "unités de transport": len(units), "contenants": sum(u.quantity for u in units.values())})
st.dataframe(pd.DataFrame(pre_rows), use_container_width=True)

if st.button("Lancer l'optimisation", type="primary"):
    solutions = []
    for day in settings["days"]:
        st.markdown(f"### Optimisation — {day}")
        day_flows = active_flows_for_day(flows, day, selected_functions)
        units = create_units_for_day(day_flows, day, containers, vehicles_selected)
        if not units:
            st.warning(f"{day}: aucun flux actif dans le périmètre sélectionné.")
            continue
        progress_cb = progress_callback_factory()
        engine = FleetSearchEngine(vehicles_selected, containers, sites, workbook.matrices, settings=settings)
        with st.spinner(f"Recherche d'une solution pour {day}..."):
            sol = engine.solve_day(day, units, progress_cb=progress_cb)
        solutions.append(sol)
        if sol.performance_acceptable:
            st.success(f"{day}: solution validée et acceptable — occupation chauffeur {sol.metrics.driver_useful_occupancy:.0%}")
        elif sol.hard_valid:
            st.warning(f"{day}: contraintes dures validées mais occupation chauffeur insuffisante ({sol.metrics.driver_useful_occupancy:.0%}).")
        else:
            st.error(f"{day}: solution non conforme. Consultez les contrôles.")
    st.session_state.solutions = solutions

solutions = st.session_state.solutions
show_results(solutions)
show_validation(solutions)

if solutions:
    st.divider()
    st.subheader("Exports et sauvegarde")
    all_ok = all(s.performance_acceptable for s in solutions)
    if not all_ok:
        st.warning("Les exports sont fournis comme exports de diagnostic : au moins une solution est non conforme ou sous le seuil d'occupation chauffeur.")
    excel_bytes = export_solutions_to_excel_bytes(solutions, workbook.normalization_report.changes, [i.__dict__ for i in validation_items])
    excel_label = "Télécharger l'export Excel conforme" if all_ok else "Télécharger l'export Excel de diagnostic"
    st.download_button(excel_label, data=excel_bytes, file_name="OptiFLUX_resultats.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    pptx_bytes = export_solutions_to_pptx_bytes(solutions)
    ppt_label = "Télécharger l'export PowerPoint" if all_ok else "Télécharger l'export PowerPoint de diagnostic"
    st.download_button(ppt_label, data=pptx_bytes, file_name="OptiFLUX_synthese.pptx", mime="application/vnd.openxmlformats-officedocument.presentationml.presentation")
    json_bytes = save_simulation_bytes(solutions)
    st.download_button("Sauvegarder la simulation JSON", data=json_bytes, file_name="OptiFLUX_simulation.json", mime="application/json")
