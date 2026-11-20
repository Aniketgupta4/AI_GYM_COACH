import streamlit as st
from services.persistence.exercise_repository import get_or_create_user


def render_login_wall():
    if st.session_state.get("logged_in", False) and st.session_state.get("user_id") is not None:
        return True

    # High-Impact Hero Experience
    st.markdown(
        """
        <div class="login-hero-container">
            <div class="hero-badge-pill">⚡ COMPUTER VISION FITNESS INTELLIGENCE</div>
            <h1 class="hero-main-title">APNA <span class="hero-gradient-text">AI COACH</span> • PRO</h1>
            <p class="hero-tagline">Real-time biomechanics, dynamic AI voice coaching, cadence tracking, and automatic rep analysis right from your camera.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 3 Feature Highlight Cards
    st.markdown(
        """
        <div class="login-feature-grid">
            <div class="login-feature-card">
                <div class="feature-icon-wrapper">🎯</div>
                <div class="feature-card-title">Biomechanical Vision</div>
                <div class="feature-card-desc">Sub-millimeter joint tracking & depth verification powered by MediaPipe AI.</div>
            </div>
            <div class="login-feature-card">
                <div class="feature-icon-wrapper">🎙️</div>
                <div class="feature-card-title">Real-time Voice AI</div>
                <div class="feature-card-desc">Instant coaching audio cues correcting your posture and pacing on every rep.</div>
            </div>
            <div class="login-feature-card">
                <div class="feature-icon-wrapper">📊</div>
                <div class="feature-card-title">Analytics & History</div>
                <div class="feature-card-desc">Automated set progression, cadence graphs, and lifetime workout history.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Centered Glassmorphic Login Card
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        st.markdown(
            """
            <div class="login-card-wrapper">
                <div class="login-card-header">
                    <div class="athlete-icon-circle">👤</div>
                    <div>
                        <h3 class="login-card-title">Athlete Profile Access</h3>
                        <p class="login-card-subtitle">Sign in to save personal workout stats & history</p>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.form("athlete_login_card_form", clear_on_submit=False):
            username_input = st.text_input(
                "Athlete Name",
                value=st.session_state.get("username", "Aniket"),
                placeholder="Enter athlete name (e.g. Aniket)"
            )

            # Sidebar plan preview
            plan_exercise = st.session_state.get("plan_exercise", "Squats")
            plan_sets = st.session_state.get("plan_sets", 3)
            plan_reps = st.session_state.get("plan_reps", 10)
            st.caption(f"⚡ Selected in Sidebar: **{plan_exercise}** ({plan_sets} Sets × {plan_reps} Reps)")

            submit_button = st.form_submit_button("🚀 Enter Training Arena & Save Profile", width="stretch")

        if submit_button:
            cleaned = (username_input or "").strip()
            if not cleaned:
                cleaned = "Aniket"
            user = get_or_create_user(cleaned)
            st.session_state["user_id"] = user["id"]
            st.session_state["username"] = user["username"]
            st.session_state["logged_in"] = True
            st.rerun()

        st.markdown(
            """
            <div class="login-privacy-footer">
                <span>🔒</span>
                <span>Private & Secure • Zero Cloud Video Recording • Processed Locally</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return False