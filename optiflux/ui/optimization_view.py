from __future__ import annotations
import streamlit as st


def progress_callback_factory():
    bar = st.progress(0)
    status = st.empty()
    def cb(step: int, total: int, message: str):
        total = max(total, 1)
        bar.progress(min(1.0, step / total))
        status.caption(message)
    return cb
