# state.py
import streamlit as st
import pandas as pd

def init_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "last_sql" not in st.session_state:
        st.session_state.last_sql = None

    if "last_result_summary" not in st.session_state:
        st.session_state.last_result_summary = None

    if "query_history" not in st.session_state:
        st.session_state.query_history = []

def summarize_df(df: pd.DataFrame):
    return {
        "row_count": len(df),
        "columns": list(df.columns),
        "sample_rows": df.head(3).to_dict(orient="records")
    }