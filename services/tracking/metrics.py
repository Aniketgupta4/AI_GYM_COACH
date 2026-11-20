import streamlit as st
import time
from services.config.workout_config import METRICS_FIELDS
from services.persistence.exercise_repository import add_exercise


def sync_metrics_update(context):
    if not context or not hasattr(context, "state") or not context.state.playing:
        return
    
    processor = getattr(context, "video_processor", None)

    if not processor:
        return 
    
    exercise = st.session_state.get("exercise_type")

    if not exercise:
        return
    
    processor.set_exercise(exercise)

    if st.session_state.get("needs_detector_reset", False):
        if hasattr(processor, "reset_detectors"):
            processor.reset_detectors(exercise)
        st.session_state.needs_detector_reset = False
        st.session_state.reps = 0
        st.session_state.sets_completed = 0
        st.session_state.current_set_reps = 0
        return

    latest_metrics = processor.get_latest_metrics()

    if not latest_metrics:
        return
    
    reps = latest_metrics.get("reps", 0)

    if reps is None:
        reps = 0
        
    st.session_state.reps = reps

    fields = METRICS_FIELDS.get(exercise)

    if not fields:
        return 

    for key, default in fields.items():
        st.session_state[key] = latest_metrics.get(key, default)

    reps_per_set = st.session_state.get("reps_per_set", 0)
    target_sets = st.session_state.get("target_sets", 0)

    if reps is not None and reps_per_set > 0 and target_sets > 0:
        sets_completed = reps // reps_per_set
        current_set_reps = reps % reps_per_set
        workout_completed = sets_completed >= target_sets 
    else:
        sets_completed = 0
        current_set_reps = 0
        workout_completed = False

    st.session_state.sets_completed = sets_completed
    st.session_state.current_set_reps = current_set_reps
    st.session_state.workout_completed = workout_completed

    pipeline = st.session_state.get("voice_pipeline")
    event_handled = False

    last_saved_sets = st.session_state.get("last_saved_sets_completed", 0)

    # Set completion voice coaching
    if target_sets > 0 and reps_per_set > 0 and sets_completed > last_saved_sets:
        if pipeline:
            result = pipeline.process_event(
                event="set_completed",
                exercise=exercise,
                metrics=latest_metrics,
            )
            if result:
                st.session_state.audio_to_play, st.session_state.coach_feedback = result
                st.session_state.audio_id = time.time()
                event_handled = True

        st.session_state.last_saved_sets_completed = sets_completed

    # Rep progress voice encouragement (every few reps when cadence allows)
    last_notified_reps = st.session_state.get("last_notified_reps", 0)
    if reps > last_notified_reps:
        st.session_state["last_notified_reps"] = reps
        if not event_handled and pipeline and not workout_completed:
            result = pipeline.process_event(
                event="rep_completed",
                exercise=exercise,
                metrics={"rep_num": reps, "current_set_reps": current_set_reps},
            )
            if result:
                st.session_state.audio_to_play, st.session_state.coach_feedback = result
                st.session_state.audio_id = time.time()
                event_handled = True

    # Full workout completion (target sets achieved)
    if workout_completed and not st.session_state.get("last_notified_workout_complete", False):
        st.session_state.last_notified_workout_complete = True

        finish_and_save_workout_session()

        if pipeline and not event_handled:
            result = pipeline.process_event(
                event="workout_completed",
                exercise=exercise,
                metrics=latest_metrics,
            )
            if result:
                st.session_state.audio_to_play, st.session_state.coach_feedback = result
                st.session_state.audio_id = time.time()
                event_handled = True

    pose_detected = latest_metrics.get("pose_detected", True)
    
    if not pose_detected and pipeline and not event_handled:
        result = pipeline.process_event(
            event="no_pose_detected",
            exercise=exercise,
            metrics={"issue": "No pose detected! Please step into the camera frame."},
        )
        if result:
            st.session_state.audio_to_play, st.session_state.coach_feedback = result
            st.session_state.audio_id = time.time()
            event_handled = True

    if pipeline and not event_handled:
        result = pipeline.process_event(
            event="ongoing_form_check",
            exercise=exercise,
            metrics=latest_metrics,
        )
        if result:
            st.session_state.audio_to_play, st.session_state.coach_feedback = result
            st.session_state.audio_id = time.time()


def finish_and_save_workout_session():
    """
    Saves the full workout session with total reps, sets, and duration once upon finish.
    """
    if not st.session_state.get("workout_started", False):
        return

    if st.session_state.get("workout_saved", False):
        st.session_state.workout_started = False
        return

    user_id = st.session_state.get("user_id")
    exercise = st.session_state.get("exercise_type")
    reps = st.session_state.get("reps", 0)
    sets_completed = st.session_state.get("sets_completed", 0)
    
    # If user performed reps but didn't finish a full set, record as 1 partial set
    if sets_completed == 0 and reps > 0:
        sets_to_record = 1
    else:
        sets_to_record = sets_completed

    start_time = st.session_state.get("workout_session_start_time")
    now_ts = time.time()
    if not start_time:
        start_time = st.session_state.get("set_cycle_started_at", now_ts)
    duration = max(1, round(now_ts - start_time))

    if user_id and exercise and reps > 0:
        add_exercise(user_id, exercise, reps, sets_to_record, duration)
        st.session_state.workout_saved = True

    st.session_state.workout_started = False

