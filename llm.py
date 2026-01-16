# llm.py
from google import genai
import os
import streamlit as st

def get_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment")
    return genai.Client(api_key=api_key)

def generate_sql():
    client = get_client()   # ✅ created AFTER dotenv is loaded

    system_prompt = f"""
You are a PostgreSQL SQL generator.

You have conversational and analytical memory.

QUERY HISTORY (ordered oldest → newest):
{st.session_state.query_history}

LAST SQL QUERY (shortcut):
{st.session_state.last_sql}

LAST QUERY RESULT SUMMARY:
{st.session_state.last_result_summary}

INSTRUCTIONS:
- If the user explicitly refers to:
  • "first query" → use the first entry in QUERY HISTORY
  • "previous query" → use the second last entry in QUERY HISTORY
  • "earlier query" → choose the most relevant entry from QUERY HISTORY
- If the user uses refinement words like:
  "only", "filter", "breakdown", "sort", "this", "above"
  → MODIFY the most recent applicable query
- Otherwise, generate a NEW query

STRICT RULES:
- Output ONLY a single PostgreSQL SELECT query
- Query ONLY the tables: journey_xray, papi_automation

- Columns of journey_xray table:
    aid: bigint
    channel: text
    cid: bigint
    glreqid: text
    nid: bigint
    ts: timestamp without time zone
    uid: bigint

- Columns of papi_automation table:
    id: bigint
    name: text
    created_date: timestamp without time zone
    from_date: timestamp without time zone
    to_date: timestamp without time zone
    updated_date: timestamp without time zone
    journey_xray_enabled: bigint
    lp_content_parsed: jsonb
    linkdatarray: jsonb
    nodedatarray: jsonb

- NO markdown
- NO explanations
- NO comments
- NO semicolon
"""

    conversation = [{"role": "user", "parts": [{"text": system_prompt}]}]

    for msg in st.session_state.messages:
        role = "model" if msg["role"] == "assistant" else "user"
        conversation.append(
            {"role": role, "parts": [{"text": msg["content"]}]}
        )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=conversation,
    )
    return response.text.strip()


# Explaing the sql result function
def explain_result(user_question, sql, result_summary):
    """
    Uses Gemini to generate a plain-English explanation of the query result.
    """
    client = get_client()

    system_prompt = f"""
You are a data analyst explaining query results to a non-technical user.

User Question:
{user_question}

Executed SQL:
{sql}

Query Result Summary:
- Rows returned: {result_summary['row_count']}
- Columns: {result_summary['columns']}
- Sample rows: {result_summary['sample_rows']}

Explain:
- What this result represents
- Any obvious insights or patterns
- If result is empty, explain possible reasons

Rules:
- Do NOT output SQL
- Do NOT output markdown tables
- Plain English only
- Be concise
"""

    # Convert conversation history for Gemini
    conversation = [{"role": "user", "parts": [{"text": system_prompt}]}]

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=conversation,
    )

    return response.text.strip()
