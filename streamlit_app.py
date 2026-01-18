import asyncio
import os
import threading
from concurrent.futures import Future
from typing import Any, Dict, Optional

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from gemini_neon_bridge import GeminiNeonBridge


load_dotenv()


st.set_page_config(page_title="Neon MCP Chat", page_icon="💬", layout="wide")


class _AsyncRunner:
    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def run(self, coro):
        future: Future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()


def _extract_table(response: Any) -> Optional[pd.DataFrame]:
    if response is None:
        return None

    if isinstance(response, dict):
        # Common MCP formats
        if "rows" in response and "columns" in response:
            rows = response.get("rows") or []
            cols = response.get("columns") or []
            return pd.DataFrame(rows, columns=cols)
        if "data" in response and isinstance(response.get("data"), list):
            return pd.DataFrame(response.get("data"))
        if "result" in response and isinstance(response.get("result"), list):
            return pd.DataFrame(response.get("result"))
        if "result" in response and isinstance(response.get("result"), dict):
            return _extract_table(response.get("result"))
        if "parsed" in response:
            return _extract_table(response.get("parsed"))
        if "raw_text" in response:
            try:
                parsed = pd.read_json(response.get("raw_text"))
                return parsed
            except Exception:
                pass
        if "response" in response and isinstance(response.get("response"), dict):
            return _extract_table(response.get("response"))
        # Fallback: normalize dict to single-row table
        try:
            return pd.json_normalize(response)
        except Exception:
            return None
    if isinstance(response, list):
        return pd.DataFrame(response)

    return None


def _render_tool_call(tool_call: Dict[str, Any], idx: int):
    tool_name = tool_call.get("name", "tool")
    response = tool_call.get("response")
    sql_text = tool_call.get("sql")
    arguments = tool_call.get("arguments")

    st.caption(f"Tool call {idx + 1}: {tool_name}")

    if sql_text:
        st.markdown("**SQL executed:**")
        st.code(sql_text, language="sql")
    elif arguments:
        with st.expander("Tool arguments"):
            st.json(arguments)

    df = _extract_table(response)
    if df is None or df.empty:
        st.caption("No tabular result detected for this tool call.")

    with st.expander("Raw tool response"):
        raw_df = _extract_table(response)
        if raw_df is not None and not raw_df.empty:
            st.dataframe(raw_df, use_container_width=True)
        else:
            st.json(response)


st.title("Neon MCP Chat")

neon_api_key = os.getenv("NEON_API_KEY")
gemini_api_key = os.getenv("GEMINI_API_KEY")
project_id = os.getenv("NEON_PROJECT_ID")

if not neon_api_key or not gemini_api_key or not project_id:
    st.error("Missing environment variables: NEON_API_KEY, GEMINI_API_KEY, NEON_PROJECT_ID")
    st.stop()

if "bridge" not in st.session_state:
    st.session_state.bridge = GeminiNeonBridge(
        neon_api_key=neon_api_key,
        gemini_api_key=gemini_api_key,
        project_id=project_id,
    )

if "messages" not in st.session_state:
    st.session_state.messages = []

if "async_runner" not in st.session_state:
    st.session_state.async_runner = _AsyncRunner()

if st.button("Reset chat"):
    st.session_state.bridge.reset_conversation()
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("tool_calls"):
            for idx, tool_call in enumerate(message["tool_calls"]):
                _render_tool_call(tool_call, idx)

user_prompt = st.chat_input("Ask about your Neon database...")
if user_prompt:
    st.session_state.messages.append({"role": "user", "content": user_prompt})

    with st.chat_message("user"):
        st.markdown(user_prompt)

    with st.chat_message("assistant"):
        with st.spinner("Querying Neon MCP..."):
            result = st.session_state.async_runner.run(
                st.session_state.bridge.chat_with_gemini_with_tools(user_prompt)
            )

        assistant_text = result.get("text", "")
        tool_calls = result.get("tool_calls", [])

        st.markdown(assistant_text)

        if tool_calls:
            for idx, tool_call in enumerate(tool_calls):
                _render_tool_call(tool_call, idx)

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": assistant_text,
                "tool_calls": tool_calls,
            }
        )
