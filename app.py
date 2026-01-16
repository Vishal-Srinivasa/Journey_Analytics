# app.py
import streamlit as st
import psycopg
import pandas as pd
from dotenv import load_dotenv
import os
from styles import load_styles
from sidebar import render_sidebar
from state import init_session_state, summarize_df

load_dotenv()
from llm import generate_sql, explain_result

DB_URL = os.getenv("DB_URL")

st.set_page_config(
    page_title="Netcore Journey AI",
    page_icon="🟧",
    layout="wide"
)

load_styles()
init_session_state()
render_sidebar()

# ---------- HEADER ----------
st.markdown(
    """
    <div style="display:flex; align-items:center; gap:14px;">
        <h1 style="margin-bottom:0;">Journey Analytics AI</h1>
        <span class="badge">Netcore</span>
    </div>
    <div class="subtitle">
        Natural language analytics for journeys, workflows, channels, and conversions
    </div>
    """,
    unsafe_allow_html=True
)

# ---------- LAYOUT ----------
chat_col, result_col = st.columns([1.1, 1.9])

# ---------- CHAT HISTORY ----------
with chat_col:
    st.markdown("### 💬 Ask your question")
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# ---------- INPUT ----------
user_input = st.chat_input(
    "Ask about journeys, triggers, splits, channels, conversions..."
)

if user_input:
    st.session_state.messages.append(
        {"role": "user", "content": user_input}
    )

    with chat_col:
        with st.chat_message("user"):
            st.markdown(user_input)

    with result_col:
        with st.spinner("🤖 Thinking and querying..."):
            try:
                sql_query = generate_sql()

                if not sql_query.lower().startswith("select"):
                    st.error("Only SELECT queries allowed")
                    st.stop()

                with st.expander("🔍 View Generated SQL"):
                    st.code(sql_query, language="sql")

                with psycopg.connect(DB_URL) as conn:
                    df = pd.read_sql(sql_query, conn)

                summary = summarize_df(df)

                # ---------- GENERATE EXPLANATION ----------
                explanation = explain_result(
                    user_question=user_input,
                    sql=sql_query,
                    result_summary=summary
                )

                # Add the full query entry (with explanation) at once
                st.session_state.query_history.append({
                    "sql": sql_query,
                    "summary": summary,
                    "explanation": explanation
                })

                st.session_state.last_sql = sql_query
                st.session_state.last_result_summary = summary

                tab1, tab2 = st.tabs(["📊 Results", "ℹ️ Summary"])

                with tab1:
                    st.dataframe(df, use_container_width=True)

                with tab2:
                    st.markdown(f"**Result Summary:**\n\nRows returned: {summary['row_count']}")
                    st.markdown(f"**Explanation:**\n\n{explanation}")


                assistant_reply = f"✅ **Query Successful**\n\nRows returned: **{len(df)}**"

            except Exception as e:
                st.error("Query execution failed")
                assistant_reply = f"❌ Error: {e}"

    st.session_state.messages.append(
        {"role": "assistant", "content": assistant_reply}
    )
