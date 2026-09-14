"""Role-based RAG chatbot — Streamlit UI."""

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from auth import authenticate
from rag.answer import answer_question, is_small_talk
from rag.ingest import ingest_role

st.set_page_config(page_title="Role RAG Chat", page_icon="🔐", layout="wide")


def _init_session():
    defaults = {
        "authenticated": False,
        "username": "",
        "role": "",
        "messages": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _logout():
    st.session_state.authenticated = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.session_state.messages = []


def _login_page():
    st.title("🔐 Company Policy Assistant")
    st.caption("Log in to chat with documents for your role only.")

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in", type="primary")

    if submitted:
        user = authenticate(username, password)
        if user:
            st.session_state.authenticated = True
            st.session_state.username = user["username"]
            st.session_state.role = user["role"]
            st.session_state.messages = []
            st.rerun()
        else:
            st.error("Invalid username or password.")

    with st.expander("Demo accounts"):
        st.markdown(
            """
| Username | Password | Role | Sees |
|---|---|---|---|
| `admin` | `admin123` | Admin | Laptop, hardware & trip policies |
| `hr` | `hr123` | HR | Leave, loan & medical policies |
            """
        )


def _ensure_index(role: str) -> bool:
    from rag.store import get_collection

    try:
        return get_collection(role).count() > 0
    except Exception:
        return False


def _chat_page():
    role = st.session_state.role

    with st.sidebar:
        st.subheader("Session")
        st.write(f"**User:** {st.session_state.username}")
        st.write(f"**Role:** {role}")
        if st.button("Log out"):
            _logout()
            st.rerun()

        st.divider()
        st.subheader("Index")
        if _ensure_index(role):
            st.success(f"Index ready for `{role}`")
        else:
            st.warning("No index yet — click Build index below.")
        if st.button(f"Build index for {role}"):
            with st.spinner("Embedding documents..."):
                n = ingest_role(role)
            st.success(f"Indexed {n} chunks.")
            st.rerun()

        st.divider()
        st.markdown("**Try asking**")
        if role == "admin":
            st.markdown(
                "- How far in advance must laptop requests be submitted?\n"
                "- What devices are included in hardware issuance?\n"
                "- What is the company contribution for annual trips?"
            )
        else:
            st.markdown(
                "- How do I apply for leave?\n"
                "- What is the maximum loan amount?\n"
                "- Where do I submit the medical reimbursement form?"
            )

    st.title("💬 Chat")
    st.caption(f"Talk to **{role}** Assistant.")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                st.caption(f"Sources: {', '.join(msg['sources'])}")

    prompt = st.chat_input("Ask about your policies...")
    if not prompt:
        return

    if not _ensure_index(role):
        st.error(f"No index for `{role}`. Use **Build index** in the sidebar first.")
        return

    history = list(st.session_state.messages)
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        spinner = "Thinking..." if is_small_talk(prompt) else "Searching ..."
        with st.spinner(spinner):
            result = answer_question(role, prompt, history=history)
        st.markdown(result["answer"])
        if result.get("sources"):
            st.caption(f"Sources: {', '.join(result['sources'])}")

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result["answer"],
            "sources": result["sources"],
        }
    )


def main():
    _init_session()
    if not st.session_state.authenticated:
        _login_page()
    else:
        _chat_page()


if __name__ == "__main__":
    main()
