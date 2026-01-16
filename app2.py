import streamlit as st
from google import genai

# ---------------------------
# PAGE CONFIG
# ---------------------------
st.set_page_config(
    page_title="Netcore Journey AI",
    page_icon="🟧",
    layout="centered"
)

# ---------------------------
# GEMINI CLIENT
# ---------------------------
from dotenv import load_dotenv
load_dotenv()

client=genai.Client(api_key="GEMINI_API_KEY")

# ---------------------------
# CUSTOM STYLING (NETCORE ORANGE + WHITE)
# ---------------------------
st.markdown(
    """
    <style>
        .main {
            background-color: #ffffff;
        }

        h1 {
            color: #ff7a00;
        }

        .subtitle {
            color: #555;
            margin-bottom: 20px;
        }

        .stChatMessage.user {
            background-color: #fff4e6;
            border-radius: 12px;
            padding: 12px;
        }

        .stChatMessage.assistant {
            background-color: #f9fafb;
            border-left: 4px solid #ff7a00;
            border-radius: 12px;
            padding: 12px;
        }

        .stChatInput textarea {
            border: 2px solid #ff7a00;
            border-radius: 10px;
        }

        .badge {
            background-color: #ff7a00;
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            margin-left: 10px;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------------------
# HEADER
# ---------------------------
st.markdown(
    """
    <h1>
        Journey Analytics AI
        <span class="badge">Netcore</span>
    </h1>
    <div class="subtitle">
        Ask about Journeys, workflow automations, triggers, conditions, channels, and conversions.
    </div>
    """,
    unsafe_allow_html=True
)

# ---------------------------
# SESSION STATE (MEMORY)
# ---------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------------------------
# DISPLAY CHAT HISTORY
# ---------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---------------------------
# USER INPUT
# ---------------------------
user_input = st.chat_input(
    "Ask about marketing journeys, triggers, splits, channels, optimizations..."
)

if user_input:
    # Store user message
    st.session_state.messages.append(
        {"role": "user", "content": user_input}
    )

    with st.chat_message("user"):
        st.markdown(user_input)

    # ---------------------------
    # SYSTEM PROMPT (NETCORE-SPECIFIC)
    # ---------------------------
    system_prompt = """
    """

    # ---------------------------
    # BUILD CONVERSATION FOR GEMINI
    # ---------------------------
    conversation = [
        {
            "role": "user",
            "parts": [{"text": system_prompt}]
        }
    ]

    for msg in st.session_state.messages:
        role = "model" if msg["role"] == "assistant" else "user"
        conversation.append(
            {
                "role": role,
                "parts": [{"text": msg["content"]}]
            }
        )

    # ---------------------------
    # GEMINI RESPONSE
    # ---------------------------
    with st.chat_message("assistant"):
        with st.spinner("Thinking through the journey..."):
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=conversation,
            )

            assistant_reply = response.text
            st.markdown(assistant_reply)

    # Store assistant message
    st.session_state.messages.append(
        {"role": "assistant", "content": assistant_reply}
    )
