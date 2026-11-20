import base64
import time
import streamlit as st
import streamlit.components.v1 as components


class VoicePipeline:
    def __init__(self, llm, tts):
        self.llm = llm
        self.tts = tts
        self.last_spoken_at = 0

    def _find_form_issue(self, exercise, metrics):
        if not metrics:
            return None

        if "issue" in metrics:
            return metrics["issue"]

        if exercise == "Squats":
            depth = metrics.get("depth_status", "")
            back_angle = metrics.get("back_angle", 180)
            
            if depth in ["TOO SHALLOW", "TOO HIGH"]:
                return "The squat depth was not deep enough — bend knees deeper until thighs are parallel."

            if isinstance(back_angle, (int, float)) and 0 < back_angle < 120:
                return "Leaning too far forward during the squat — keep your chest lifted and spine upright."

        elif exercise == "Push-ups":
            alignment = metrics.get("body_alignment", "")
            hip_status = metrics.get("hip_status", "")
            
            if alignment == "Poor Form":
                return "Body is sagging or bent — maintain a straight line from head to heels."

            if hip_status == "SAGGING":
                return "Hips are sagging down — squeeze your glutes and engage your core."

            if hip_status == "PIKED UP":
                return "Hips are piked too high — lower them to form a straight line."

        elif exercise == "Biceps Curls (Dumbbell)":
            swing = metrics.get("swing_status", "")
            shoulder = metrics.get("shoulder_status", "")
            
            if swing == "SWINGING":
                return "Torso is swinging — keep your body still and isolate the biceps."

            if shoulder == "ELBOW DRIFTING":
                return "Elbows are drifting away from your sides — keep them pinned close."

        elif exercise == "Shoulder Press":
            back_arch = metrics.get("back_arch_status", "")
            if back_arch == "Excessive Arch":
                return "Lower back is arching excessively — brace your core tight."
            if back_arch == "Slight Arch":
                return "Slight back arch detected — brace your core to keep your spine neutral."

        elif exercise == "Lunges":
            balance = metrics.get("balance_status", "")
            if balance == "OFF BALANCE":
                return "Losing balance during the lunge — feet should be hip-width apart."

        return None

    def process_event(self, event, exercise, metrics=None):
        if metrics is None:
            metrics = {}

        now = time.time()
        is_major_event = event in ["workout_started", "set_completed", "workout_completed"]

        issue = self._find_form_issue(exercise, metrics)

        if not is_major_event:
            if event == "rep_completed":
                if now - self.last_spoken_at < 5:
                    return None
            elif event == "no_pose_detected":
                if now - self.last_spoken_at < 6:
                    return None
            elif issue:
                if now - self.last_spoken_at < 4:
                    return None
            else:
                return None

        try:
            text = self.llm.give_feedback(event, issue)
        except Exception:
            text = self.llm._get_fallback_cue(event, issue)

        if not text:
            return None

        voice = self.tts.speak(text)
        self.last_spoken_at = now

        return voice, text


def autoplay_audio(audio_bytes, text="", audio_id=""):
    """
    Plays coach audio cleanly and reliably using the browser's Audio and SpeechSynthesis APIs.
    Guarded by audio_id so it executes once per unique cue without interrupting mid-sentence.
    """
    if not audio_bytes and not text:
        return

    b64 = base64.b64encode(audio_bytes).decode("utf-8") if audio_bytes else ""
    safe_text = (text or "").replace("\\", "\\\\").replace('"', '\\"').replace("'", "\\'").replace("\n", " ").replace("\r", "")
    id_str = str(audio_id or safe_text[:30] or "coach_voice")

    components.html(
        f"""
        <script>
        (function() {{
            try {{
                var targetWin = window;
                try {{
                    if (window.top && window.top.document) {{
                        targetWin = window.top;
                    }} else if (window.parent && window.parent.document) {{
                        targetWin = window.parent;
                    }}
                }} catch(e) {{
                    targetWin = window;
                }}

                var cueId = "{id_str}";
                if (targetWin._lastCoachAudioId === cueId) {{
                    return;
                }}
                targetWin._lastCoachAudioId = cueId;

                var speech = "{safe_text}";
                var b64Data = "{b64}";

                function speakWithSynthesis(w, txt) {{
                    try {{
                        var synth = (w && w.speechSynthesis) ? w.speechSynthesis : window.speechSynthesis;
                        if (synth && txt && txt.length > 0) {{
                            synth.cancel();
                            var utter = new SpeechSynthesisUtterance(txt);
                            utter.rate = 1.05;
                            utter.pitch = 1.0;
                            utter.volume = 1.0;
                            synth.speak(utter);
                        }}
                    }} catch(e) {{
                        console.error("SpeechSynthesis error:", e);
                    }}
                }}

                if (b64Data && b64Data.length > 50) {{
                    try {{
                        if (targetWin._currentCoachAudio) {{
                            try {{ targetWin._currentCoachAudio.pause(); }} catch(e) {{}}
                        }}
                        var snd = new Audio("data:audio/mp3;base64," + b64Data);
                        targetWin._currentCoachAudio = snd;
                        snd.volume = 1.0;
                        var p = snd.play();
                        if (p !== undefined) {{
                            p.catch(function(err) {{
                                console.warn("Audio autoplay blocked, falling back to speech synthesis:", err);
                                speakWithSynthesis(targetWin, speech);
                            }});
                        }}
                        return;
                    }} catch(e) {{
                        console.warn("Audio play error, falling back to speech synthesis:", e);
                        speakWithSynthesis(targetWin, speech);
                        return;
                    }}
                }}

                speakWithSynthesis(targetWin, speech);
            }} catch(err) {{
                console.error("Coach audio error:", err);
            }}
        }})();
        </script>
        """,
        height=0,
    )
