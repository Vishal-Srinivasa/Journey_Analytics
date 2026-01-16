# sidebar.py
import streamlit as st

def render_sidebar():
    with st.sidebar:
        st.markdown("### 💡 Example Questions")
        st.markdown(
            """
            ----- HERE'S AN EXAMPLE SEQUENCE OF QUESTIONS -----
            - list all users for aid=129.
            - for aid=210.
            - count users.
            - get all the nodes for id 10
            """
        )
        st.divider()
        st.markdown("### ⚙️ System Status")
        st.success("UI Loaded")
        st.info("Model: Gemini 2.5 Flash")

        if st.button("🔄 Reset Conversation"):
            st.session_state.messages = []
            st.session_state.last_sql = None
            st.session_state.last_result_summary = None
            st.session_state.query_history = []
            st.rerun()
