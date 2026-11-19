from io import BytesIO
from gtts import gTTS
import logging

logger = logging.getLogger(__name__)


class TextToSpeech:
    def __init__(self):
        self._cache = {}

    def speak(self, text, lang="en"):
        cleaned = (text or "").strip()

        if not cleaned:
            return None

        if cleaned in self._cache:
            return self._cache[cleaned]

        try:
            buffer = BytesIO()
            gTTS(text=cleaned, lang=lang).write_to_fp(buffer)
            buffer.seek(0)
            audio_data = buffer.read()
            if audio_data:
                self._cache[cleaned] = audio_data
            return audio_data
        except Exception as e:
            logger.warning(f"gTTS speech generation error: {e}")
            return None
