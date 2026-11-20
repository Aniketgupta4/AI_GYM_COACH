import streamlit as st


def initial_session_defaults():
    defaults = {
        "reps": 0,
        "target_sets": 3,
        "reps_per_set": 10,
        "sets_completed": 0,
        "current_set_reps": 0,
        "workout_complete": False,
        "workout_completed": False,
        "last_notified_sets_completed": 0,
        "last_notified_workout_complete": False,
        "last_saved_sets_completed": 0,
        "last_counted_reps": 0,
        "last_notified_reps": 0,
        "set_cycle_started_at": 0.0,
        "last_exercise_type": "Squats",

        # Athlete Login & Profile
        "logged_in": False,
        "user_id": None,
        "username": "Aniket",

        # Audio and Coaching state
        "audio_to_play": None,
        "coach_feedback": "",
        "audio_id": 0,
        "last_played_audio_id": 0,

        # Workout plan (set before starting)
        "workout_started": False,
        "workout_saved": False,
        "workout_session_start_time": 0.0,
        "plan_exercise": "Squats",
        "plan_sets": 3,
        "plan_reps": 10,
        "sb_plan_exercise": "Squats",
        "sb_plan_sets": 3,
        "sb_plan_reps": 10,
        "main_plan_exercise": "Squats",
        "main_plan_sets": 3,
        "main_plan_reps": 10,

        # Common Angles
        "knee_angle": 0,
        "back_angle": 0,
        "elbow_angle": 0,
        "front_knee_angle": 0,
        "torso_angle": 0,

        # Status fields
        "depth_status": "N/A",
        "body_alignment": "N/A",
        "hip_status": "N/A",
        "shoulder_status": "N/A",
        "swing_status": "N/A",
        "extension_status": "N/A",
        "back_arch_status": "N/A",
        "balance_status": "N/A",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
