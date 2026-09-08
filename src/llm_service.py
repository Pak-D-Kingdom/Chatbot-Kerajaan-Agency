import json
import re
import time
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from openai import OpenAI

from src.config import (
    LLM_API_KEY, 
    LLM_MODEL, 
    LLM_BASE_URL,
    LLM_MAX_TOKENS, 
    LLM_TEMPERATURE, 
    LLM_MAX_RETRIES,
    REGISTRATION_URL
)
from src.prompt_templates import (
    build_system_prompt, 
    VALID_INTENTS, 
    JSON_FORMAT_INSTRUCTION,
    FALLBACK_MESSAGE
)

class KerajaanStructuredResponse(BaseModel):
    """Structured response schema untuk Kerajaan Agency Chatbot"""
    reply: str
    intent: str = "ABOUT_AGENCY"
    show_cta: bool = False
    cta_text: Optional[str] = "📝 DAFTAR JADI KOL"
    cta_url: Optional[str] = REGISTRATION_URL
    is_fallback: bool = False

def extract_json(response_text: str) -> Optional[dict]:
    """Ekstrak JSON dari teks respons LLM, mendukung format dalam markdown codeblock atau plain."""
    # 1. Coba pola ```json ... ```
    codeblock_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
    if codeblock_match:
        try:
            return json.loads(codeblock_match.group(1))
        except json.JSONDecodeError:
            pass

    # 2. Coba pola kurung kurawal terluar
    json_patterns = [
        r'\{[\s\S]*\}',
        r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',
    ]
    for pattern in json_patterns:
        match = re.search(pattern, response_text)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                continue
    return None

class LLMService:
    """Client LLM menggunakan OpenAI SDK (kompatibel dengan Groq)."""
    
    def __init__(self):
        self.client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
        self.system_prompt = build_system_prompt()

    def chat_with_history(
        self, 
        user_message: str, 
        history: List[Dict[str, str]], 
        raw_user_message: Optional[str] = None
    ) -> dict:
        """
        Memanggil LLM dengan history percakapan dan konteks RAG.
        Mengembalikan dictionary sesuai KerajaanStructuredResponse.
        """
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]

        # Tambahkan percakapan sebelumnya
        for msg in history:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

        # Tambahkan pesan user saat ini (yang sudah di-augment konteks RAG)
        messages.append({
            "role": "user",
            "content": f"{user_message}\n\n{JSON_FORMAT_INSTRUCTION}"
        })

        response_text = ""
        for attempt in range(LLM_MAX_RETRIES):
            try:
                response = self.client.chat.completions.create(
                    model=LLM_MODEL,
                    messages=messages,
                    max_tokens=LLM_MAX_TOKENS,
                    temperature=LLM_TEMPERATURE
                )
                response_text = response.choices[0].message.content.strip()
                break
            except Exception as e:
                err_str = str(e).lower()
                is_rate_limit = "rate_limit" in err_str or "429" in err_str
                if is_rate_limit and attempt < LLM_MAX_RETRIES - 1:
                    wait_time = 3 * (attempt + 1)
                    print(f"[INFO] Rate limit Groq, menunggu {wait_time}s... ({attempt+1}/{LLM_MAX_RETRIES})")
                    time.sleep(wait_time)
                else:
                    if attempt == LLM_MAX_RETRIES - 1:
                        print(f"[ERROR] LLMService gagal setelah {LLM_MAX_RETRIES} percobaan: {e}")
                        return {
                            "reply": "Maaf, sistem AI kami sedang sibuk atau mengalami gangguan sesaat. Mohon coba tanyakan kembali ya! 🙏",
                            "intent": "OUT_OF_SCOPE",
                            "show_cta": False,
                            "cta_text": None,
                            "cta_url": None,
                            "is_fallback": True,
                            "error": str(e)
                        }

        # Ekstraksi respons JSON
        response_json = extract_json(response_text)
        if response_json is None:
            # Jika LLM menjawab plain text tanpa format JSON
            clean_reply = re.sub(r'```(?:json)?', '', response_text).strip('`').strip()
            return {
                "reply": clean_reply if clean_reply else FALLBACK_MESSAGE,
                "intent": "ABOUT_AGENCY",
                "show_cta": False,
                "cta_text": "📝 DAFTAR JADI KOL",
                "cta_url": REGISTRATION_URL,
                "is_fallback": False
            }

        # Validasi Intent
        raw_intent = str(response_json.get("intent", "ABOUT_AGENCY")).upper()
        if raw_intent not in VALID_INTENTS:
            raw_intent = "ABOUT_AGENCY"
        response_json["intent"] = raw_intent

        # Pastikan field default CTA
        if response_json.get("show_cta"):
            response_json["cta_url"] = response_json.get("cta_url") or REGISTRATION_URL
            response_json["cta_text"] = response_json.get("cta_text") or "📝 DAFTAR JADI KOL"

        try:
            validated = KerajaanStructuredResponse(**response_json)
            return validated.model_dump()
        except Exception as ve:
            print(f"[WARN] Schema validation warning: {ve}")
            return response_json