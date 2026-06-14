from __future__ import annotations
import pandas as pd
import plotly.express as px
import streamlit as st
from optiflux.config.defaults import DAYS


def show_flow_analysis(flows):
    st.subheader("Analyse des flux")
    rows = []
    for f in flows:
        for day in DAYS:
            qty = f.quantity_by_day.get(day, 0)
            if qty > 0:
                rows.append({"jour": day, "fonction support": f.support_function, "contenant": f.container_name, "origine": f.origin, "destination": f.destination, "quantité": qty})
    df = pd.DataFrame(rows)
    if df.empty:
        st.info("Aucun flux actif détecté.")
        return
    functions = sorted(df["fonction support"].dropna().unique())
    selected = st.multiselect("Filtrer par fonction support", functions, default=functions)
    df_f = df[df["fonction support"].isin(selected)] if selected else df
    fig = px.bar(df_f, x="jour", y="quantité", color="fonction support", barmode="stack", title="Volumes quotidiens par fonction support")
    st.plotly_chart(fig, use_container_width=True)
    fig2 = px.bar(df_f, x="jour", y="quantité", color="origine", barmode="stack", title="Volumes par jour et site collecté")
    st.plotly_chart(fig2, use_container_width=True)
    st.dataframe(df_f, use_container_width=True)
