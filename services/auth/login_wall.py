import streamlit as st
from services.persistence.exercise_repository import get_or_create_user


def render_login_wall():
    if st.session_state.get("user_id") is not None:
        return True

    # Hero Branding Header
    st.markdown(
        """
        <div class="login-hero-container">
            <div class="hero-badge-pill">⚡ NEXT-GEN COMPUTER VISION FITNESS</div>
            <h1 class="hero-main-title">APNA <span class="hero-gradient-text">AI GYM COACH</span></h1>
            <p class="hero-tagline">
                Real-time biomechanical pose detection with proactive AI voice coaching & automatic rep tracking.
            </p>
        </div>

        <div class="login-feature-grid">
            <div class="login-feature-card">
                <div class="feature-icon-wrapper">🎯</div>
                <div class="feature-card-title">Pose Precision</div>
                <div class="feature-card-desc">33-point real-time skeletal joint analysis tracking exact depth & angles.</div>
            </div>
            <div class="login-feature-card">
                <div class="feature-icon-wrapper">🎙️</div>
                <div class="feature-card-title">Live Voice AI</div>
                <div class="feature-card-desc">Instant vocal encouragement & biomechanical form correction cues.</div>
            </div>
            <div class="login-feature-card">
                <div class="feature-icon-wrapper">📊</div>
                <div class="feature-card-title">Smart Analytics</div>
                <div class="feature-card-desc">Zero-touch automated rep cadence, set tracking, and workout history.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Athlete Entry Card
    st.markdown(
        """
        <div class="login-card-wrapper">
            <div class="login-card-header">
                <div class="athlete-icon-circle">👤</div>
                <div>
                    <h3 class="login-card-title">Athlete Check-in</h3>
                    <p class="login-card-subtitle">Enter your name or athlete ID to begin your session</p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input(
            "Athlete Name",
            placeholder="e.g. Aniket Gupta",
            label_visibility="collapsed",
        )
        submit_button = st.form_submit_button("🚀 Enter Training Arena", width="stretch")

    if submit_button:
        cleaned_username = (username or "").strip()
        if not cleaned_username:
            st.error("⚠️ Please enter a name or username to start training.")
            return False

        user = get_or_create_user(cleaned_username)
        st.session_state["user_id"] = user["id"]
        st.session_state["username"] = user["username"]
        st.rerun()

    st.markdown(
        """
        <div class="login-privacy-footer">
            <span>🔒</span>
            <span><strong>100% Private Camera Inference</strong> — Video frames are processed entirely in your browser and never saved or transmitted.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    return False