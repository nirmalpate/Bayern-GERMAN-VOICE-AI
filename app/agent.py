import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from openai import OpenAI

from app.call_log import CallLogger
from app.knowledge import load_hotel_knowledge

EMERGENCY_WORDS = {
    "notfall", "schlüssel", "brand", "feuer", "krank", "arzt", "krankenwagen",
    "aufsperren", "ausgesperrt", "hilfe", "problem", "polizei", "verletzt",
}

FALLBACK_ERROR = "Entschuldigung, dazu kann ich Ihnen gerade keine Auskunft geben. Bitte wenden Sie sich an unsere Rezeption."


class HotelAgent:
    def __init__(self, call_id: str, caller_number: str = "Unbekannt"):
        self.call_id = call_id
        self.caller_number = caller_number
        self.logger = CallLogger(call_id)
        self.needs_transfer = False

        self.client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.environ.get("GROQ_API_KEY"),
        )
        self.model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

        hour = datetime.now(ZoneInfo("Europe/Berlin")).hour
        self.is_night_shift = hour >= 21 or hour < 6
        self.night_mode_engaged = self.is_night_shift

        knowledge_text = load_hotel_knowledge()
        self.system_prompt = f"""Du bist der exklusive, charmante digitale Telefon-Assistent des 5-Sterne-Hotels Bayerischer Hof in München.
Nutze folgendes Wissen, um Fragen präzise zu beantworten:
{knowledge_text}

Regeln:
- Antworte extrem kurz, höflich und in exzellentem Deutsch (maximal 1-2 kurze Sätze für das Telefongespräch).
- Nenne nur Fakten aus dem Wissen. Wenn du etwas nicht weißt, sage das ehrlich und verweise auf die Rezeption.
"""
        self.history = [{"role": "system", "content": self.system_prompt}]

    @staticmethod
    def _is_emergency(text: str) -> bool:
        words = set(re.findall(r"[\wäöüß]+", text.lower()))
        return bool(words & EMERGENCY_WORDS)

    def _record(self, user_text: str, answer: str):
        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": answer})
        self.logger.log_turn("assistant", answer)

    def reply(self, user_text: str) -> str:
        self.logger.log_turn("user", user_text)

        if self.is_night_shift and self.night_mode_engaged:
            if self._is_emergency(user_text):
                self.needs_transfer = True
                answer = ("Das verstehe ich. Ich verbinde Sie sofort mit dem "
                          "diensthabenden Portier. Bitte bleiben Sie dran.")
                self._record(user_text, answer)
                return answer
            self.night_mode_engaged = False

        self.history.append({"role": "user", "content": user_text})
        try:
            kwargs = {}
            if "gpt-oss" in self.model:
                # reasoning model: keep thinking short so it answers fast with content
                kwargs["extra_body"] = {"reasoning_effort": "low"}
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.history,
                max_tokens=600,
                temperature=0.3,
                timeout=10,
                **kwargs,
            )
            answer = (response.choices[0].message.content or "").strip()
        except Exception as e:
            self.logger.log_turn("error", repr(e))
            answer = ""

        if not answer:
            answer = FALLBACK_ERROR

        self.history.append({"role": "assistant", "content": answer})
        self.logger.log_turn("assistant", answer)
        return answer
