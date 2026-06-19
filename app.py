from pathlib import Path
import os
import sys
import uuid

import streamlit as st
from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from agent.deep_agent import build_agent_config
from scripts.langgraph_agent_cli import get_message_content, needs_as_of_approval


st.set_page_config(
    page_title="Revenue Manager Agent",
    layout="centered",
)


APP_USERNAME = os.getenv("BASIC_AUTH_USERNAME", "admin")
APP_PASSWORD = os.getenv("BASIC_AUTH_PASSWORD", "otel-demo")


def check_basic_login() -> bool:
    if st.session_state.get("authenticated"):
        return True

    st.markdown(
        """
        <style>
        .stApp {
            background: #f5f6f8;
        }

        .block-container {
            max-width: 460px;
            padding-top: 5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.form("login"):
        st.subheader("Revenue Manager Agent")
        st.caption("Sign in to continue.")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")

    if submitted:
        if username == APP_USERNAME and password == APP_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Invalid credentials")

    return False


if not check_basic_login():
    st.stop()


st.markdown(
    """
    <style>
    .stApp {
        background: #f5f6f8;
        color: #111827;
    }

    .block-container {
        max-width: 920px;
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    h1, h2, h3, p, label, span, div {
        color: #111827;
    }

    .app-header {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 24px 26px;
        margin-bottom: 18px;
        box-shadow: 0 8px 22px rgba(15, 23, 42, 0.05);
    }

    .app-header h1 {
        margin: 0;
        font-size: 30px;
        line-height: 1.2;
        color: #111827;
    }

    .app-header p {
        margin: 10px 0 0 0;
        color: #4b5563;
        font-size: 15px;
        line-height: 1.5;
    }

    [data-testid="stExpander"] {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        overflow: hidden;
    }

    [data-testid="stExpander"] summary {
        background: #ffffff;
        color: #111827;
        font-weight: 700;
    }

    [data-testid="stExpander"] summary p {
        color: #111827;
        font-size: 17px;
    }

    .stButton > button {
        border-radius: 10px;
        border: 1px solid #d1d5db;
        background: #ffffff;
        color: #111827;
        font-weight: 600;
        min-height: 52px;
        box-shadow: none;
    }

    .stButton > button:hover {
        border-color: #2563eb;
        background: #eff6ff;
        color: #111827;
    }

    .stButton > button:focus {
        border-color: #2563eb;
        box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.18);
        color: #111827;
    }

    [data-testid="stChatMessage"] {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 12px;
        margin-bottom: 12px;
        box-shadow: 0 6px 18px rgba(15, 23, 42, 0.04);
    }

    [data-testid="stChatMessage"] p,
    [data-testid="stChatMessage"] li,
    [data-testid="stChatMessage"] div,
    [data-testid="stChatMessage"] span {
        color: #111827 !important;
    }

    [data-testid="stMarkdownContainer"] {
        color: #111827;
    }

    [data-testid="stMarkdownContainer"] p {
        color: #111827;
    }

    [data-testid="stChatInput"] {
        background: #ffffff;
    }

    .stAlert {
        background: #fff7ed;
        color: #111827;
        border-radius: 10px;
    }

    .stSpinner > div {
        color: #111827 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def build_agent():
    config = build_agent_config()

    if os.getenv("GROQ_API_KEY"):
        llm = ChatGroq(
            model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            temperature=0,
        )
    else:
        llm = ChatOllama(
            model=os.getenv("OLLAMA_MODEL", "qwen2.5:3b"),
            temperature=0,
        )

    agent = create_react_agent(
        model=llm,
        tools=config["tools"],
        checkpointer=MemorySaver(),
        prompt=config["system_prompt"],
    )

    return agent


def extract_tool_trace(result: dict) -> list[str]:
    trace = []

    for msg in result.get("messages", []):
        tool_calls = getattr(msg, "tool_calls", None)

        if tool_calls:
            for call in tool_calls:
                trace.append(f"Tool called: {call.get('name')} args={call.get('args')}")

        msg_type = getattr(msg, "type", "")
        name = getattr(msg, "name", None)
        content = getattr(msg, "content", "")

        if msg_type == "tool":
            trace.append(f"Tool result from: {name}")
            if content:
                trace.append(f"Tool output: {content}")

    return trace


def run_agent(question: str) -> tuple[str, list[str]]:
    result = st.session_state.agent.invoke(
        {"messages": [HumanMessage(content=question)]},
        config={
            "configurable": {
                "thread_id": st.session_state.thread_id,
            }
        },
    )

    answer = get_message_content(result["messages"][-1])
    trace = extract_tool_trace(result)

    return answer, trace


def render_answer_with_trace(answer: str, trace: list[str]) -> None:
    st.markdown(answer)

    if trace:
        with st.expander("Tool trace"):
            for item in trace:
                st.code(item)


if "thread_id" not in st.session_state:
    st.session_state.thread_id = f"streamlit-{uuid.uuid4()}"

if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent" not in st.session_state:
    st.session_state.agent = build_agent()

if "pending_approval_question" not in st.session_state:
    st.session_state.pending_approval_question = None


st.markdown(
    """
    <div class="app-header">
        <h1>Revenue Manager Agent</h1>
        <p>Ask questions about OTB, segment mix, pickup pace, and block vs transient demand. The agent uses deterministic revenue tools backed by Postgres.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


with st.expander("Try these demo questions", expanded=True):
    col1, col2 = st.columns(2)

    demo_questions = [
        "What is July 2026 OTB?",
        "What is our segment mix for July 2026?",
        "How much pickup did we get in the last 7 days for future stays from 2026-06-15?",
        "What is block vs transient mix for July 2026?",
        "What was July 2026 OTB as of 2026-06-15?",
    ]

    for index, question in enumerate(demo_questions):
        target_col = col1 if index % 2 == 0 else col2

        with target_col:
            if st.button(question, key=f"demo-{index}", use_container_width=True):
                st.session_state.next_question = question

if st.button("New conversation"):
    st.session_state.thread_id = f"streamlit-{uuid.uuid4()}"
    st.session_state.messages = []
    st.session_state.pending_approval_question = None
    st.rerun()


for message in st.session_state.messages:
    with st.chat_message(
        message["role"],
        avatar=message.get("avatar", "assistant"),
    ):
        st.markdown(message["content"])


typed_question = st.chat_input("Ask a revenue question...")
question = st.session_state.pop("next_question", None) or typed_question

if question:
    if needs_as_of_approval(question):
        st.session_state.pending_approval_question = question
    else:
        st.session_state.messages.append(
            {"role": "user", "content": question, "avatar": "user"}
        )

        with st.chat_message("user", avatar="user"):
            st.markdown(question)

        with st.chat_message("assistant", avatar="assistant"):
            with st.spinner("Checking revenue tools..."):
                answer, trace = run_agent(question)
                render_answer_with_trace(answer, trace)

        st.session_state.messages.append(
            {"role": "assistant", "content": answer, "avatar": "assistant"}
        )


if st.session_state.pending_approval_question:
    question = st.session_state.pending_approval_question

    st.warning("This question uses point-in-time OTB and needs approval before running the tool.")
    st.markdown(f"**Question:** {question}")

    approve_col, deny_col = st.columns(2)

    with approve_col:
        if st.button("Approve and run", use_container_width=True):
            st.session_state.messages.append(
                {"role": "user", "content": question, "avatar": "user"}
            )

            with st.chat_message("user", avatar="user"):
                st.markdown(question)

            with st.chat_message("assistant", avatar="assistant"):
                with st.spinner("Checking as-of OTB..."):
                    answer, trace = run_agent(question)
                    render_answer_with_trace(answer, trace)

            st.session_state.messages.append(
                {"role": "assistant", "content": answer, "avatar": "assistant"}
            )

            st.session_state.pending_approval_question = None
            st.rerun()

    with deny_col:
        if st.button("Cancel", use_container_width=True):
            st.session_state.pending_approval_question = None
            st.info("Cancelled. The as-of OTB tool was not run.")
            st.rerun()