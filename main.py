import os
import threading
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="google.protobuf")
os.environ["GLOG_minloglevel"] = "2"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

# Monkey patch streamlit_webrtc SessionShutdownObserver to prevent NoneType is_alive crash
try:
    from streamlit_webrtc.shutdown import SessionShutdownObserver
    def _safe_shutdown_stop(self, timeout: float = 1.0) -> None:
        thread = self._polling_thread
        self._polling_thread = None
        if thread:
            self._polling_thread_stop_event.set()
            if threading.current_thread() is not thread:
                thread.join(timeout=timeout)
    SessionShutdownObserver.stop = _safe_shutdown_stop
except Exception:
    pass

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

import time
import pandas as pd
import streamlit as st
from services.auth.login_wall import render_login_wall
from services.config.workout_config import EXERCISE_OPTIONS
from services.state.session_defaults import initial_session_defaults
from services.ui.style_loader import load_css, inject_local_font, inject_webrtc_styles
from services.persistence.exercise_repository import init_db
from streamlit_webrtc import webrtc_streamer, WebRtcMode
from services.vision.exercise_video_processor import VideoProcessorClass
from services.tracking.metrics import sync_metrics_update, finish_and_save_workout_session
from services.persistence.exercise_repository import get_users_exercises, clear_user_history, get_or_create_user
from groq import Groq
from services.coaching.llm import LLMCoach
from services.coaching.tts import TextToSpeech
from services.coaching.voice_pipeline import VoicePipeline, autoplay_audio


EXERCISE_TIPS = {
    "Squats": [
        "🦶 Stance: Feet shoulder-width apart, toes slightly angled out.",
        "📐 Depth: Lower until thighs are parallel to the floor.",
        "🛡️ Posture: Keep chest proud, spine straight, brace core."
    ],
    "Push-ups": [
        "📏 Alignment: Maintain a straight plank from head to heels.",
        "💪 Elbows: Keep elbows at 45° to torso, avoid flaring out.",
        "🔒 Core: Squeeze glutes and abs to avoid sagging hips."
    ],
    "Biceps Curls (Dumbbell)": [
        "📌 Elbows: Pin elbows beside your ribs throughout the curl.",
        "🛑 Still Body: Isolate your arms, avoid swinging the torso.",
        "⏳ Tempo: Lift with power, lower with control."
    ],
    "Shoulder Press": [
        "🏛️ Core: Lock ribs down and engage glutes to protect spine.",
        "⬆️ Extension: Press straight up to full arm extension overhead.",
        "🛡️ Back Arch: Do not hyperextend or arch your lower back."
    ],
    "Lunges": [
        "⚖️ Balance: Step forward with hip-width spacing.",
        "📐 90° Angles: Bend both front and back knees to 90 degrees.",
        "🛡️ Torso: Keep upper body tall and upright."
    ]
}


def sync_from_main():
    ex = st.session_state.get("main_plan_exercise", "Squats")
    sets = st.session_state.get("main_plan_sets", 3)
    reps = st.session_state.get("main_plan_reps", 10)
    st.session_state.plan_exercise = ex
    st.session_state.plan_sets = sets
    st.session_state.plan_reps = reps
    st.session_state.sb_plan_exercise = ex
    st.session_state.sb_plan_sets = sets
    st.session_state.sb_plan_reps = reps


def sync_from_sb():
    ex = st.session_state.get("sb_plan_exercise", "Squats")
    sets = st.session_state.get("sb_plan_sets", 3)
    reps = st.session_state.get("sb_plan_reps", 10)
    st.session_state.plan_exercise = ex
    st.session_state.plan_sets = sets
    st.session_state.plan_reps = reps
    st.session_state.main_plan_exercise = ex
    st.session_state.main_plan_sets = sets
    st.session_state.main_plan_reps = reps


def main():
    st.set_page_config(
        page_icon="🏋️‍♀️",
        page_title="AI Real-time GYM Coach",
        initial_sidebar_state="expanded",
        layout="wide"
    )

    current_dir = os.path.dirname(os.path.abspath(__file__))
    load_css(os.path.join(current_dir, "static", "style.css"))
    inject_local_font(os.path.join(current_dir, "static", "AdobeClean.otf"), "AdobeClean")

    init_db()
    initial_session_defaults()

    is_logged_in = st.session_state.get("logged_in", False) and st.session_state.get("user_id") is not None

    # Login screen: NO SIDEBAR ("from login page remove sidebar")
    if not is_logged_in:
        st.markdown(
            """
            <style>
            [data-testid="stSidebar"],
            [data-testid="stExpandSidebarButton"],
            header[data-testid="stHeader"] [data-testid="stExpandSidebarButton"] {
                display: none !important;
                visibility: hidden !important;
                width: 0 !important;
                height: 0 !important;
                pointer-events: none !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        render_login_wall()
        return

    # Home & Training screen: SHOW SIDEBAR ("home page pe show sidebar")
    if "voice_pipeline" not in st.session_state or st.session_state.voice_pipeline is None:
        try:
            api_key = os.environ.get("GROQ_API_KEY", "")

            if not api_key and hasattr(st, "secrets") and "GROQ_API_KEY" in st.secrets:
                api_key = st.secrets["GROQ_API_KEY"]
            
            groq_client = Groq(api_key=api_key) if api_key else None
            llm_coach = LLMCoach(groq_client)
            tts = TextToSpeech()
            st.session_state.voice_pipeline = VoicePipeline(llm_coach, tts)
        except Exception:
            llm_coach = LLMCoach(None)
            tts = TextToSpeech()
            st.session_state.voice_pipeline = VoicePipeline(llm_coach, tts)

    workout_started = st.session_state.get("workout_started", False)
    
    with st.sidebar:
        # Modern Brand Logo Header
        st.markdown(
            """
            <div class="brand-header-box">
                <div class="brand-icon-emblem">⚡</div>
                <div class="brand-text-column">
                    <span class="brand-title-text">APNA AI COACH</span>
                    <span class="brand-badge-pill">PRO SMART TRAINER</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        athlete_name = st.session_state.get("username", "Aniket")

        if is_logged_in:
            st.markdown(
                f"""
                <div class="sidebar-user-pill">
                    <span>👤</span>
                    <span>Athlete: <strong>{athlete_name}</strong></span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if st.button("🚪 Switch Athlete / Logout", key="sidebar_logout_btn", width="stretch"):
                st.session_state["logged_in"] = False
                st.session_state["user_id"] = None
                st.session_state["workout_started"] = False
                st.rerun()
        else:
            st.markdown(
                """
                <div class="sidebar-user-pill">
                    <span>👤</span>
                    <span>Status: <strong>Guest (Sign In)</strong></span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        if not workout_started:
            st.subheader("Workout Setup")

            cur_plan_ex = st.session_state.get("plan_exercise", EXERCISE_OPTIONS[0])
            cur_idx = EXERCISE_OPTIONS.index(cur_plan_ex) if cur_plan_ex in EXERCISE_OPTIONS else 0

            sb_plan_exercise = st.selectbox(
                "Select Exercise",
                options=EXERCISE_OPTIONS,
                index=cur_idx,
                key="sb_plan_exercise",
                on_change=sync_from_sb
            )

            sb_plan_sets = st.number_input(
                "Target Sets",
                min_value=1,
                max_value=50,
                value=int(st.session_state.get("plan_sets", 3)),
                key="sb_plan_sets",
                step=1,
                on_change=sync_from_sb
            )

            sb_plan_reps = st.number_input(
                "Reps per Set",
                min_value=1,
                max_value=50,
                value=int(st.session_state.get("plan_reps", 10)),
                key="sb_plan_reps",
                step=1,
                on_change=sync_from_sb
            )

            plan_exercise = st.session_state.get("plan_exercise", sb_plan_exercise)
            plan_sets = int(st.session_state.get("plan_sets", sb_plan_sets))
            plan_reps = int(st.session_state.get("plan_reps", sb_plan_reps))

            st.markdown("")

            start_label = f"🚀 Start Workout ({plan_exercise})" if is_logged_in else f"🚀 Start as {athlete_name}"
            start_session_button = st.button(start_label, width="stretch", key="start_session_button")

            if start_session_button:
                if not is_logged_in:
                    u = get_or_create_user(athlete_name)
                    st.session_state["user_id"] = u["id"]
                    st.session_state["username"] = u["username"]
                    st.session_state["logged_in"] = True

                st.session_state.exercise_type = plan_exercise
                st.session_state.target_sets = int(plan_sets)
                st.session_state.reps_per_set = int(plan_reps)
                st.session_state.reps = 0
                st.session_state.sets_completed = 0
                st.session_state.current_set_reps = 0
                st.session_state.workout_started = True
                st.session_state.workout_saved = False
                st.session_state.workout_session_start_time = time.time()
                st.session_state.set_cycle_started_at = time.time()
                st.session_state.last_saved_sets_completed = 0
                st.session_state.last_notified_sets_completed = 0
                st.session_state.last_notified_reps = 0
                st.session_state.last_notified_workout_complete = False
                st.session_state.needs_detector_reset = True

                if st.session_state.voice_pipeline:
                    result = st.session_state.voice_pipeline.process_event(
                        event="workout_started",
                        exercise=plan_exercise,
                        metrics={}
                    )
                    if result:
                        st.session_state.audio_to_play, st.session_state.coach_feedback = result
                        st.session_state.audio_id = time.time()

                st.rerun()

            # Exercise Guidelines in sidebar
            tips = EXERCISE_TIPS.get(plan_exercise, [])
            if tips:
                tips_html = "".join([f"<li>{t}</li>" for t in tips])
                st.markdown(
                    f"""
                    <div class="sidebar-tips-card">
                        <h4>💡 Form Guidance</h4>
                        <ul>{tips_html}</ul>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            exercise = st.session_state.get("exercise_type", "Exercise")
            sets = st.session_state.get("target_sets", 3)
            reps = st.session_state.get("reps_per_set", 10)

            st.markdown(
                f"""
                <div class="sidebar-status-card">
                    <div class="status-indicator">
                        <span>🟢 LIVE TRAINING</span>
                    </div>
                    <div class="session-exercise-name">{exercise}</div>
                    <div class="session-target-badge">Goal: {sets} Sets × {reps} Reps</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            tips = EXERCISE_TIPS.get(exercise, [])
            if tips:
                tips_html = "".join([f"<li>{t}</li>" for t in tips])
                st.markdown(
                    f"""
                    <div class="sidebar-tips-card">
                        <h4>💡 Form Focus</h4>
                        <ul>{tips_html}</ul>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.markdown("")
            end_session_button = st.button("⏹️ End Workout", key="sidebar_end_session_button", width="stretch")

            if end_session_button:
                finish_and_save_workout_session()
                if st.session_state.voice_pipeline:
                    result = st.session_state.voice_pipeline.process_event(
                        event="workout_completed",
                        exercise=exercise,
                        metrics={}
                    )
                    if result:
                        st.session_state.audio_to_play, st.session_state.coach_feedback = result
                        st.session_state.audio_id = time.time()
                st.rerun()

    # Modern Center Page Top Navigation & Status Bar
    status_label = "🔴 LIVE TRAINING" if workout_started else "🟢 VISION READY"
    status_color = "#FF3366" if workout_started else "var(--accent-green)"
    athlete_name = st.session_state.get("username", "Athlete")

    st.markdown(
        f"""
        <div class="app-top-header">
            <div class="top-brand-left">
                <div class="top-pulse-dot" style="background:{status_color}; box-shadow:0 0 12px {status_color};"></div>
                <span class="top-title-text">APNA <span class="hero-gradient-text">AI COACH</span> • PRO</span>
            </div>
            <div class="top-profile-badge">
                <span style="color:{status_color}; font-weight:700; font-size:0.78rem; text-transform:uppercase; letter-spacing:0.06em;">{status_label}</span>
                <span>•</span>
                <span>👤 Athlete: <strong>{athlete_name}</strong></span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
 
    # Audio playback when NOT in workout mode (welcome/completion)
    audio_id = st.session_state.get("audio_id", 0)
    last_played_id = st.session_state.get("last_played_audio_id", 0)
    if not workout_started and audio_id > 0 and audio_id != last_played_id:
        autoplay_audio(st.session_state.get("audio_to_play"), text=st.session_state.get("coach_feedback", ""), audio_id=str(audio_id))
        st.session_state["last_played_audio_id"] = audio_id

    # Display coach feedback text cleanly when not in workout mode (in workout mode it is inside the side HUD)
    if not workout_started and st.session_state.get("coach_feedback"):
        st.markdown("")
        st.success(f"🤖 **Coach:** {st.session_state.coach_feedback}")

    if not workout_started:
        cur_plan_ex = st.session_state.get("plan_exercise", EXERCISE_OPTIONS[0])
        cur_idx = EXERCISE_OPTIONS.index(cur_plan_ex) if cur_plan_ex in EXERCISE_OPTIONS else 0
        cur_sets = int(st.session_state.get("plan_sets", 3))
        cur_reps = int(st.session_state.get("plan_reps", 10))

        st.markdown(
            """
            <div class="ready-card-container">
                <div class="ready-card-header">
                    <span style="font-size:1.8rem;">🏋️‍♂️</span>
                    <div>
                        <h3 style="margin:0; color:#fff;">Session Setup & Target Plan</h3>
                        <span class="ready-card-badge">Customize Your Exercise, Sets & Reps</span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Full Interactive Workout Controls Right on Center Screen!
        setup_c1, setup_c2, setup_c3 = st.columns([5, 3, 3], gap="medium")
        with setup_c1:
            main_exercise = st.selectbox(
                "🏋️ Select Exercise",
                options=EXERCISE_OPTIONS,
                index=cur_idx,
                key="main_plan_exercise",
                on_change=sync_from_main
            )
        with setup_c2:
            main_sets = st.number_input(
                "🎯 Target Sets",
                min_value=1,
                max_value=50,
                value=cur_sets,
                key="main_plan_sets",
                step=1,
                on_change=sync_from_main
            )
        with setup_c3:
            main_reps = st.number_input(
                "🔄 Reps per Set",
                min_value=1,
                max_value=50,
                value=cur_reps,
                key="main_plan_reps",
                step=1,
                on_change=sync_from_main
            )

        active_exercise = st.session_state.get("plan_exercise", main_exercise)
        active_sets = int(st.session_state.get("plan_sets", main_sets))
        active_reps = int(st.session_state.get("plan_reps", main_reps))
        active_total_reps = active_sets * active_reps

        st.markdown(
            f"""
            <div class="ready-card-grid" style="margin-top: 14px; margin-bottom: 16px;">
                <div class="ready-grid-item">
                    <div class="ready-item-title">Selected Exercise</div>
                    <div class="ready-item-value">{active_exercise}</div>
                </div>
                <div class="ready-grid-item">
                    <div class="ready-item-title">Target Sets & Reps</div>
                    <div class="ready-item-value" style="color:var(--accent-green);">{active_sets} Sets × {active_reps} Reps</div>
                </div>
                <div class="ready-grid-item">
                    <div class="ready-item-title">Total Rep Goal</div>
                    <div class="ready-item-value">{active_total_reps} Reps Total</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Form Guidance Tips
        tips = EXERCISE_TIPS.get(active_exercise, [])
        if tips:
            tips_html = "".join([f"<li>{t}</li>" for t in tips])
            st.markdown(
                f"""
                <div class="sidebar-tips-card" style="margin-bottom: 22px;">
                    <h4>💡 {active_exercise} — Form Guidance & Technique</h4>
                    <ul>{tips_html}</ul>
                </div>
                """,
                unsafe_allow_html=True,
            )

        btn_col1, btn_col2, btn_col3 = st.columns([1, 2, 1])
        with btn_col2:
            main_start_button = st.button(
                f"🚀 Start Workout Now ({active_exercise})",
                key="main_start_workout_button",
                width="stretch"
            )
            if main_start_button:
                st.session_state.exercise_type = active_exercise
                st.session_state.target_sets = int(active_sets)
                st.session_state.reps_per_set = int(active_reps)
                st.session_state.reps = 0
                st.session_state.sets_completed = 0
                st.session_state.current_set_reps = 0
                st.session_state.workout_started = True
                st.session_state.workout_saved = False
                st.session_state.workout_session_start_time = time.time()
                st.session_state.set_cycle_started_at = time.time()
                st.session_state.last_saved_sets_completed = 0
                st.session_state.last_notified_sets_completed = 0
                st.session_state.last_notified_reps = 0
                st.session_state.last_notified_workout_complete = False
                st.session_state.needs_detector_reset = True

                if st.session_state.voice_pipeline:
                    result = st.session_state.voice_pipeline.process_event(
                        event="workout_started",
                        exercise=active_exercise,
                        metrics={}
                    )
                    if result:
                        st.session_state.audio_to_play, st.session_state.coach_feedback = result
                        st.session_state.audio_id = time.time()

                st.rerun()

    else:
        exercise = st.session_state.get("exercise_type", "Exercise")
        total_reps = st.session_state.get("reps", 0)
        current_set_reps = st.session_state.get("current_set_reps", 0)
        reps_per_set = st.session_state.get("reps_per_set", 10)
        sets_completed = st.session_state.get("sets_completed", 0)
        target_sets = st.session_state.get("target_sets", 3)

        # Side-by-Side Split View: Live Camera (Left) & Telemetry HUD (Right)
        col_cam, col_hud = st.columns([13, 10], gap="medium")

        with col_cam:
            # Live Camera Stream
            rtc_config = {
                "iceServers": [
                    {"urls": ["stun:stun.l.google.com:19302"]},
                    {"urls": ["stun:stun1.l.google.com:19302"]},
                    {"urls": ["stun:stun2.l.google.com:19302"]},
                    {"urls": ["stun:global.stun.twilio.com:3478"]},
                    {"urls": ["stun:stun.cloudflare.com:3478"]},
                ]
            }

            try:
                context = webrtc_streamer(
                    key="exercise-analysis",
                    mode=WebRtcMode.SENDRECV,
                    video_processor_factory=VideoProcessorClass,
                    rtc_configuration=rtc_config,
                    media_stream_constraints={
                        "video": True,
                        "audio": False
                    },
                    async_processing=True
                )
            except Exception:
                context = None

            if context:
                sync_metrics_update(context)

            inject_webrtc_styles()

            # Compact Live Session Info Strip below camera
            st.markdown(
                f"""
                <div class="cam-info-strip">
                    <div class="cam-live-badge"><span class="live-dot"></span> LIVE VISION ACTIVE</div>
                    <div class="cam-exercise-tag">{exercise}</div>
                    <div class="cam-goal-tag">Goal: {target_sets} Sets × {reps_per_set} Reps</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_hud:
            # Refresh live values updated by sync_metrics_update in this frame
            total_reps = st.session_state.get("reps", 0)
            current_set_reps = st.session_state.get("current_set_reps", 0)
            reps_per_set = st.session_state.get("reps_per_set", 10)
            sets_completed = st.session_state.get("sets_completed", 0)
            target_sets = st.session_state.get("target_sets", 3)

            # In-session coach audio playback (placed inside col_hud so it NEVER shifts col_cam or unmounts webrtc_streamer)
            audio_id = st.session_state.get("audio_id", 0)
            audio_data = st.session_state.get("audio_to_play")
            coach_text = st.session_state.get("coach_feedback", "")
            if audio_id > 0 and (audio_data or coach_text):
                autoplay_audio(audio_data, text=coach_text, audio_id=str(audio_id))

            # 1. AI Coach Feedback Card
            coach_text = st.session_state.get("coach_feedback", "")
            if coach_text:
                st.markdown(
                    f"""
                    <div class="hud-coach-box">
                        <div class="hud-coach-header">
                            <span class="hud-coach-avatar">🤖</span>
                            <span class="hud-coach-title">AI FORM COACH</span>
                        </div>
                        <div class="hud-coach-message">"{coach_text}"</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"""
                    <div class="hud-coach-box hud-coach-idle">
                        <div class="hud-coach-header">
                            <span class="hud-coach-avatar">🤖</span>
                            <span class="hud-coach-title">AI FORM COACH</span>
                        </div>
                        <div class="hud-coach-message" style="color:var(--text-muted); font-size:0.88rem;">
                            Step into camera frame. AI coach is watching your posture!
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # 2. Main Stat Cards: Total Reps & Set Progress
            st.markdown(
                f"""
                <div class="hud-stats-grid">
                    <div class="hud-stat-card hud-stat-hero">
                        <span class="hud-stat-label">TOTAL REPS</span>
                        <span class="hud-stat-number">{total_reps}</span>
                    </div>
                    <div class="hud-stat-card">
                        <span class="hud-stat-label">CURRENT SET</span>
                        <span class="hud-stat-number">{current_set_reps} <small style="font-size:0.85rem; color:var(--text-muted);">/ {reps_per_set}</small></span>
                    </div>
                    <div class="hud-stat-card">
                        <span class="hud-stat-label">SETS COMPLETED</span>
                        <span class="hud-stat-number">{sets_completed} <small style="font-size:0.85rem; color:var(--text-muted);">/ {target_sets}</small></span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Set Progress Bar
            progress_pct = min(1.0, max(0.0, current_set_reps / reps_per_set)) if reps_per_set > 0 else 0.0
            st.progress(progress_pct)

            # 3. Biomechanical Form Telemetry Row
            if exercise == "Squats":
                knee_angle = st.session_state.get('knee_angle', 0)
                depth_status = str(st.session_state.get('depth_status', 'STAND'))
                depth_color = "var(--accent-green)" if ("PARALLEL" in depth_status or "DEEP" in depth_status) else ("#FFB800" if "SHALLOW" in depth_status else "#FFFFFF")
                st.markdown(
                    f"""
                    <div class="hud-telemetry-row">
                        <div class="hud-telemetry-item">
                            <span class="telemetry-label">Knee Angle</span>
                            <span class="telemetry-value">{knee_angle}°</span>
                        </div>
                        <div class="hud-telemetry-item">
                            <span class="telemetry-label">Depth Status</span>
                            <span class="telemetry-pill" style="color:{depth_color}; border-color:{depth_color};">{depth_status}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            elif exercise == "Push-ups":
                elbow_angle = st.session_state.get('elbow_angle', 0)
                hip_status = str(st.session_state.get('hip_status', 'N/A'))
                st.markdown(
                    f"""
                    <div class="hud-telemetry-row">
                        <div class="hud-telemetry-item">
                            <span class="telemetry-label">Elbow Angle</span>
                            <span class="telemetry-value">{elbow_angle}°</span>
                        </div>
                        <div class="hud-telemetry-item">
                            <span class="telemetry-label">Hip Alignment</span>
                            <span class="telemetry-pill">{hip_status}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            elif exercise == "Biceps Curls (Dumbbell)":
                elbow_angle = st.session_state.get('elbow_angle', 0)
                shoulder_status = str(st.session_state.get('shoulder_status', 'N/A'))
                st.markdown(
                    f"""
                    <div class="hud-telemetry-row">
                        <div class="hud-telemetry-item">
                            <span class="telemetry-label">Elbow Flexion</span>
                            <span class="telemetry-value">{elbow_angle}°</span>
                        </div>
                        <div class="hud-telemetry-item">
                            <span class="telemetry-label">Shoulder Stability</span>
                            <span class="telemetry-pill">{shoulder_status}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            elif exercise == "Shoulder Press":
                ext_status = str(st.session_state.get('extension_status', 'N/A'))
                arch_status = str(st.session_state.get('back_arch_status', 'N/A'))
                st.markdown(
                    f"""
                    <div class="hud-telemetry-row">
                        <div class="hud-telemetry-item">
                            <span class="telemetry-label">Arm Extension</span>
                            <span class="telemetry-pill">{ext_status}</span>
                        </div>
                        <div class="hud-telemetry-item">
                            <span class="telemetry-label">Back Arch</span>
                            <span class="telemetry-pill">{arch_status}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            elif exercise == "Lunges":
                front_knee = st.session_state.get('front_knee_angle', 0)
                balance_status = str(st.session_state.get('balance_status', 'N/A'))
                st.markdown(
                    f"""
                    <div class="hud-telemetry-row">
                        <div class="hud-telemetry-item">
                            <span class="telemetry-label">Front Knee</span>
                            <span class="telemetry-value">{front_knee}°</span>
                        </div>
                        <div class="hud-telemetry-item">
                            <span class="telemetry-label">Torso Balance</span>
                            <span class="telemetry-pill">{balance_status}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

            # Prominent Finish & Save Workout Button in HUD Panel
            main_end_button = st.button("⏹️ Finish & Save Workout", key="hud_end_session_button", width="stretch")
            if main_end_button:
                finish_and_save_workout_session()
                if st.session_state.voice_pipeline:
                    result = st.session_state.voice_pipeline.process_event(
                        event="workout_completed",
                        exercise=exercise,
                        metrics={}
                    )
                    if result:
                        st.session_state.audio_to_play, st.session_state.coach_feedback = result
                        st.session_state.audio_id = time.time()
                st.rerun()

        # Real-time refresh loop: re-runs every 250ms while playing so col_hud renders fresh metrics and voice coaching
        if context and getattr(context, "state", None) and context.state.playing:
            time.sleep(0.25)
            st.rerun()

    st.divider()

    st.markdown("### 📊 Workout History & Progress")

    user_id = st.session_state.get("user_id", 0)

    if isinstance(user_id, int) and user_id > 0:
        history_rows = get_users_exercises(user_id)

        if history_rows:
            def _format_duration(secs):
                s = int(secs)
                if s < 60:
                    return f"{s}s"
                m = s // 60
                rem = s % 60
                return f"{m}m {rem:02d}s"

            total_sessions = len(history_rows)
            total_lifetime_reps = sum(r['reps'] for r in history_rows)
            total_lifetime_secs = sum(r['time'] for r in history_rows)

            col_h1, col_h2, col_h3 = st.columns(3)
            with col_h1:
                st.metric("Total Sessions", f"{total_sessions}")
            with col_h2:
                st.metric("Lifetime Reps", f"{total_lifetime_reps}")
            with col_h3:
                st.metric("Total Active Time", _format_duration(total_lifetime_secs))

            tab_sessions, tab_daily = st.tabs(["🕒 All Workout Sessions (Recent First)", "📅 Daily Summary"])

            with tab_sessions:
                sessions_arr = []
                for idx, row in enumerate(history_rows, 1):
                    raw_dt = str(row['created_at'])
                    try:
                        parsed_dt = pd.to_datetime(raw_dt).strftime("%d %b %Y, %I:%M %p")
                    except Exception:
                        parsed_dt = raw_dt

                    sessions_arr.append({
                        "#": idx,
                        "Date & Time": parsed_dt,
                        "Exercise": row['exercise_name'],
                        "Sets Done": row['sets'],
                        "Total Reps": row['reps'],
                        "Duration": _format_duration(row['time'])
                    })

                df_sessions = pd.DataFrame(sessions_arr)
                st.dataframe(df_sessions.set_index("#"), use_container_width=True)

            with tab_daily:
                daily_arr = []
                for row in history_rows:
                    raw_dt = str(row['created_at'])
                    try:
                        parsed_date = pd.to_datetime(raw_dt).strftime("%Y-%m-%d")
                    except Exception:
                        parsed_date = raw_dt[:10]

                    daily_arr.append({
                        "Exercise": row['exercise_name'],
                        "Date": parsed_date,
                        "Reps": row['reps'],
                        "Sets": row['sets'],
                        "Time (sec)": row['time']
                    })

                df_daily = pd.DataFrame(daily_arr)
                agg_df = df_daily.groupby(["Exercise", "Date"]).agg({
                    "Reps": "sum",
                    "Sets": "sum",
                    "Time (sec)": "sum"
                }).reset_index()
                agg_df["Duration"] = agg_df["Time (sec)"].apply(_format_duration)
                agg_df.drop(columns=["Time (sec)"], inplace=True)
                agg_df.index += 1
                st.table(agg_df)

            with st.expander("⚙️ Manage Workout History"):
                if st.button("🗑️ Clear My Workout History", key="clear_history_btn"):
                    clear_user_history(user_id)
                    st.success("History cleared successfully!")
                    st.rerun()
        else:
            st.info("🏋️ No workout history found yet. Complete a workout to see your progress here!")
    else:
        st.info("Please log in to view workout history.")


if __name__ == "__main__":
    main()
