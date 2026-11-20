from services.config.workout_config import PROMPT
import logging

logger = logging.getLogger(__name__)


class LLMCoach:
    def __init__(self, groq_client=None):
        self.client = groq_client
        self.history = []
        self.system_prompt = PROMPT
        self.model = "qwen/qwen3.8-27b"
        self.fallback_models = ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]

    def _get_fallback_cue(self, event, issue=None):
        if event == "workout_started":
            return "Let's crush this workout! Get into position and start strong!"
        if event == "workout_completed":
            return "Workout completed! Outstanding effort today, rest up and hydrate!"
        if event == "set_completed":
            return "Awesome job! Set complete, take a breath before the next one."
        if event == "rep_completed":
            return "Strong rep! Maintain that rhythm and power!"
        if event == "no_pose_detected":
            return "Step into the camera frame so I can track your workout."

        if issue:
            low = issue.lower()
            if "deep" in low or "shallow" in low or "high" in low or "bending" in low:
                return "Squat a bit deeper, get your thighs parallel to the ground!"
            if "leaning" in low or "forward" in low or "chest" in low:
                return "Keep your chest up and your spine tall!"
            if "sagging" in low:
                return "Tighten your core and keep your hips in a straight line!"
            if "piked" in low:
                return "Lower your hips to form a straight line from head to heels!"
            if "elbow" in low or "drifting" in low:
                return "Keep your elbows pinned close to your body!"
            if "swing" in low:
                return "Control the weight, keep your torso still and avoid swinging!"
            if "arch" in low:
                return "Brace your core tight and avoid arching your lower back!"
            if "balance" in low:
                return "Widen your stance slightly and maintain your balance!"
            return issue

        return "Great form! Keep that cadence going strong!"

    def give_feedback(self, event, issue=None):
        prompt = f"Event: {event}"
        if issue:
            prompt += f" Form Issue: {issue}"

        if not self.client:
            return self._get_fallback_cue(event, issue)

        messages = [
            {"role": "system", "content": self.system_prompt},
            *self.history[-8:],
            {"role": "user", "content": prompt}
        ]

        models_to_try = [self.model] + [m for m in self.fallback_models if m != self.model]

        for model_name in models_to_try:
            try:
                response = self.client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=0.4,
                    max_tokens=60,
                    timeout=3.0,
                )
                text = response.choices[0].message.content.strip()
                if text:
                    self.history.append({"role": "assistant", "content": text})
                    return text
            except Exception as e:
                logger.warning(f"Groq error with model {model_name}: {e}")
                continue

        # If all LLM calls fail or timeout, return high-energy fallback cue
        return self._get_fallback_cue(event, issue)
