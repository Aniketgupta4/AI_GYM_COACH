import streamlit as st
from services.persistence.exercise_repository import get_or_create_user


def render_login_wall():
    if st.session_state.get("user_id") is not None:
        return True

    st.markdown(
        """
        <div class="login-compact-box">
            <div class="login-compact-badge">⚡ ATHLETE CHECK-IN</div>
            <h2 class="login-compact-title">Welcome to Apna AI Coach</h2>
            <p class="login-compact-desc">Enter your athlete name to load your workout profile and track history.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Athlete Name", placeholder="e.g. Aniket Gupta", value="Aniket")
        submit_button = st.form_submit_button("🚀 Enter Training Ground", width="stretch")

    if submit_button:
        cleaned_username = (username or "").strip()
        if not cleaned_username:
            cleaned_username = "Aniket"

        user = get_or_create_user(cleaned_username)
        st.session_state["user_id"] = user["id"]
        st.session_state["username"] = user["username"]
        st.rerun()

    return False