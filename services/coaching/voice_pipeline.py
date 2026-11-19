import base64
import time
import streamlit as st


class VoicePipeline:
    def __init__(self, llm, tts):
        self.llm = llm
        self.tts = tts
        self.last_spoken_at = 0
        self.last_encouraged_at = 0

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
            if event == "no_pose_detected":
                if now - self.last_spoken_at < 8:
                    return None
            elif issue:
                if now - self.last_spoken_at < 6:
                    return None
            else:
                # Periodic positive encouragement every 15 seconds during active exercise
                if now - self.last_spoken_at < 15:
                    return None
                self.last_encouraged_at = now

        try:
            text = self.llm.give_feedback(event, issue)
        except Exception:
            text = self.llm._get_fallback_cue(event, issue)

        if not text:
            return None

        voice = self.tts.speak(text)
        self.last_spoken_at = now

        return voice, text


def autoplay_audio(audio_bytes, text=""):
    """
    Plays audio cleanly and seamlessly in the browser.
    Injects directly into the top-level page using st.html (no iframes).
    Survives Streamlit's 250ms reruns without stopping or restarting.
    """
    if not audio_bytes and not text:
        return

    b64 = base64.b64encode(audio_bytes).decode("utf-8") if audio_bytes else ""
    escaped_text = (text or "").replace('\\', '\\\\').replace('"', '\\"').replace("'", "\\'").replace('\n', ' ').replace('\r', '')
    timestamp = int(time.time() * 1000)

    html_code = f"""
    <div style="display:none;" id="ai-coach-voice-{timestamp}">
    <script>
    (function() {{
        try {{
            var speechText = "{escaped_text}";
            var b64Data = "{b64}";
            var audioPlayed = false;

            function playWebSpeech() {{
                if (audioPlayed) return;
                try {{
                    if ('speechSynthesis' in window && speechText.length > 0) {{
                        window.speechSynthesis.cancel();
                        var utter = new SpeechSynthesisUtterance(speechText);
                        utter.rate = 1.0;
                        utter.pitch = 1.0;
                        utter.volume = 1.0;
                        var voices = window.speechSynthesis.getVoices();
                        if (voices && voices.length > 0) {{
                            for (var i = 0; i < voices.length; i++) {{
                                if (voices[i].lang.indexOf('en') === 0) {{
                                    utter.voice = voices[i];
                                    break;
                                }}
                            }}
                        }}
                        window.speechSynthesis.speak(utter);
                        audioPlayed = true;
                    }}
                }} catch(e) {{
                    console.error("SpeechSynthesis error:", e);
                }}
            }}

            if (b64Data && b64Data.length > 100) {{
                try {{
                    if (window._currentCoachAudio) {{
                        try {{
                            window._currentCoachAudio.pause();
                            window._currentCoachAudio.currentTime = 0;
                        }} catch(e) {{}}
                    }}
                    var audio = new Audio("data:audio/mp3;base64," + b64Data);
                    window._currentCoachAudio = audio;
                    audio.volume = 1.0;
                    var playPromise = audio.play();
                    if (playPromise !== undefined) {{
                        playPromise.then(function() {{
                            audioPlayed = true;
                        }}).catch(function(err) {{
                            console.warn("HTML5 audio blocked by browser, falling back to Web Speech:", err);
                            playWebSpeech();
                        }});
                    }}
                }} catch(errAudio) {{
                    console.warn("Audio element initialization failed, using Web Speech:", errAudio);
                    playWebSpeech();
                }}
            }} else {{
                playWebSpeech();
            }}
        }} catch(globalErr) {{
            console.error("Coach audio playback failed:", globalErr);
        }}
    }})();
    </script>
    </div>
    """
    st.html(html_code, unsafe_allow_javascript=True)
