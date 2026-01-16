# styles.py
import streamlit as st

def load_styles():
    st.markdown(
        """
        <style>

        /* PAGE */
        .main {
            background-color: #0e0f14;
            color: white;
        }

        h1 {
            color: white;
        }

        .subtitle {
            color: #a0a0a0;
            margin-bottom: 10px;
        }

        .badge {
            background-color: #ff7a00;
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
        }

        /* CHAT MESSAGES */
        .stChatMessage.user {
            background-color: #1f1f2b;
            border-radius: 16px;
            padding: 14px;
            margin-bottom: 10px;
        }

        .stChatMessage.assistant {
            background-color: #15161c;
            border-left: 4px solid #ff7a00;
            border-radius: 16px;
            padding: 14px;
            margin-bottom: 10px;
        }

        div[data-testid="stBottom"] {
            background: transparent !important;
        }

        section[data-testid="stChatInput"] {
            background: transparent !important;
            border: none !important;
            padding: 0 !important;
        }

        section[data-testid="stChatInput"] > div {
            background: transparent !important;
            border: none !important;
            padding: 0 !important;
        }

        section[data-testid="stChatInput"] textarea {
            background: #1f1f2b !important;
            color: white !important;
            border: 2px solid #ff7a00 !important;
            border-radius: 18px !important;
            padding: 14px 52px 14px 16px !important;
            font-size: 15px !important;
            line-height: 1.5 !important;
        }

        section[data-testid="stChatInput"] textarea::placeholder {
            color: #b0b0b0 !important;
        }

        section[data-testid="stChatInput"] textarea:focus {
            border-color: #ff7a00 !important;
            box-shadow: 0 0 0 3px rgba(255,122,0,0.25) !important;
            outline: none !important;
        }

        section[data-testid="stChatInput"] button {
            background: #ff7a00 !important;
            border-radius: 50% !important;
            width: 36px !important;
            height: 36px !important;
            border: none !important;
            position: absolute !important;
            right: 12px !important;
            bottom: 12px !important;
        }

        section[data-testid="stChatInput"] button:hover {
            background: #e56d00 !important;
        }

        section[data-testid="stChatInput"] button svg {
            fill: white !important;
        }

        </style>
        """,
        unsafe_allow_html=True
    )
