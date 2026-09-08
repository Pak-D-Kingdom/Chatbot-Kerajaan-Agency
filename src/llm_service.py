import json
import re
import time
from typing import Optional, List, Dict

import httpx2
from pydantic import BaseModel
from openai import OpenAI

from src.config import (
    LLM_API_KEY,
    LLM_MODEL,
    LLM_BASE_URL,
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
    LLM_MAX_RETRIES,
    REGISTRATION_URL,
)

from src.prompt_templates import (
    build_system_prompt,
    VALID_INTENTS,
    JSON_FORMAT_INSTRUCTION,
    FALLBACK_MESSAGE,
)


class KerajaanStructuredResponse(BaseModel):
    """Structured response schema untuk Kerajaan Agency Chatbot."""

    reply: str
    intent: str = "ABOUT_AGENCY"
    show_cta: bool = False
    cta_text: Optional[str] = "📝 DAFTAR JADI KOL"
    cta_url: Optional[str] = REGISTRATION_URL
    is_fallback: bool = False


def extract_json(response_text: str) -> Optional[dict]:
    """
    Ekstrak JSON dari teks respons LLM.

    Mendukung:
    - JSON dalam markdown codeblock
    - JSON plain text
    """

    # ========================================================
    # 1. Coba format ```json ... ```
    # ========================================================

    codeblock_match = re.search(
        r"```(?:json)?\s*([\s\S]*?)\s*```",
        response_text,
    )

    if codeblock_match:
        try:
            return json.loads(codeblock_match.group(1))
        except json.JSONDecodeError:
            pass

    # ========================================================
    # 2. Coba cari object JSON
    # ========================================================

    json_patterns = [
        r"\{[\s\S]*\}",
        r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}",
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
    """
    Service komunikasi dengan LLM menggunakan
    OpenAI-compatible API seperti Groq.

    Menggabungkan:
    - Structured JSON response dari branch aisma
    - httpx2 workaround dari branch rehan
    - Response cleaning untuk Telegram
    """

    def __init__(self):
        # ========================================================
        # Validasi API Key
        # ========================================================

        if not LLM_API_KEY:
            raise ValueError(
                "LLM API key belum diset. "
                "Pastikan GROQ_API_KEY ada di file .env"
            )

        # ========================================================
        # HTTPX2 Client
        #
        # Disable response compression untuk menghindari
        # masalah decompression pada HTTPX2.
        # ========================================================

        http_client = httpx2.Client(
            headers={
                "Accept-Encoding": "identity",
            },
            timeout=60.0,
        )

        # ========================================================
        # OpenAI-compatible Client
        # ========================================================

        self.client = OpenAI(
            api_key=LLM_API_KEY,
            base_url=LLM_BASE_URL,
            http_client=http_client,
        )

        self.model = LLM_MODEL
        self.max_tokens = LLM_MAX_TOKENS
        self.temperature = LLM_TEMPERATURE
        self.max_retries = LLM_MAX_RETRIES

        # System prompt Kerajaan Agency
        self.system_prompt = build_system_prompt()

    # ============================================================
    # RESPONSE CLEANING
    # ============================================================

    @staticmethod
    def _clean_response(text: str) -> str:
        """
        Membersihkan output LLM agar rapi dan aman
        untuk dikirim ke Telegram.

        Yang dibersihkan:
        - Markdown bold/italic
        - Markdown links
        - HTML sederhana
        - escape character
        - tabel Markdown
        - heading Markdown
        - svg marker
        """

        if not text:
            return ""

        # ========================================================
        # 1. Hapus marker "svg"
        # ========================================================

        text = re.sub(
            r"(?im)^\s*svg\s*$",
            "",
            text,
        )

        # ========================================================
        # 2. Konversi Markdown link menjadi URL biasa
        #
        # [Daftar KOL](https://...)
        # →
        # https://...
        # ========================================================

        text = re.sub(
            r"\[([^\]]+)\]\((https?://[^)\s]+)(?:\s+\"[^\"]*\")?\)",
            r"\2",
            text,
        )

        # ========================================================
        # 3. Hapus HTML
        # ========================================================

        text = re.sub(
            r"<br\s*/?>",
            "\n",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"</?(?:b|strong|i|em|u|a|p|div|span)"
            r"(?:\s+[^>]*)?>",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"<[^>]+>",
            "",
            text,
        )

        # ========================================================
        # 4. Hapus Markdown bold
        # ========================================================

        text = re.sub(
            r"\*\*(.*?)\*\*",
            r"\1",
            text,
            flags=re.DOTALL,
        )

        text = re.sub(
            r"__(.*?)__",
            r"\1",
            text,
            flags=re.DOTALL,
        )

        # ========================================================
        # 5. Hapus Markdown italic
        # ========================================================

        text = re.sub(
            r"(?<!\*)\*(?!\s)(.*?)(?<!\s)\*(?!\*)",
            r"\1",
            text,
            flags=re.DOTALL,
        )

        text = re.sub(
            r"(?<!\w)_(.*?)_(?!\w)",
            r"\1",
            text,
            flags=re.DOTALL,
        )

        # ========================================================
        # 6. Hapus inline code
        # ========================================================

        text = re.sub(
            r"`([^`]+)`",
            r"\1",
            text,
        )

        # ========================================================
        # 7. Hapus heading Markdown
        # ========================================================

        text = re.sub(
            r"(?m)^\s{0,3}#{1,6}\s+",
            "",
            text,
        )

        # ========================================================
        # 8. Hapus blockquote
        # ========================================================

        text = re.sub(
            r"(?m)^\s*>\s?",
            "",
            text,
        )

        # ========================================================
        # 9. Hapus escape character
        # ========================================================

        text = re.sub(
            r"\\([\\`*_{}\[\]()#+\-.!|>])",
            r"\1",
            text,
        )

        # ========================================================
        # 10. Bersihkan tabel Markdown
        # ========================================================

        lines = text.splitlines()
        cleaned_lines = []

        for line in lines:
            stripped = line.strip()

            # Skip separator tabel
            if re.fullmatch(
                r"\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?",
                stripped,
            ):
                continue

            # Konversi tabel menjadi bullet
            if "|" in stripped:
                parts = [
                    part.strip()
                    for part in stripped.strip("|").split("|")
                ]

                parts = [
                    part
                    for part in parts
                    if part
                ]

                if parts:
                    cleaned_lines.append(
                        "- " + " — ".join(parts)
                    )

                continue

            cleaned_lines.append(line)

        text = "\n".join(cleaned_lines)

        # ========================================================
        # 11. Rapikan bullet Markdown
        # ========================================================

        text = re.sub(
            r"(?m)^\s*[\*\+]\s+",
            "- ",
            text,
        )

        # ========================================================
        # 12. Rapikan numbered list
        # ========================================================

        text = re.sub(
            r"(?m)^\s*(\d+)\.\s+",
            r"\1. ",
            text,
        )

        # ========================================================
        # 13. Whitespace
        # ========================================================

        text = re.sub(
            r"[ \t]+",
            " ",
            text,
        )

        # ========================================================
        # 14. Terlalu banyak baris kosong
        # ========================================================

        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text,
        )

        return text.strip()

    # ============================================================
    # CHAT WITH HISTORY
    # ============================================================

    def chat_with_history(
        self,
        user_message: str,
        history: List[Dict[str, str]],
        raw_user_message: Optional[str] = None,
    ) -> dict:
        """
        Memanggil LLM dengan history percakapan
        dan konteks RAG.

        Mengembalikan dictionary sesuai
        KerajaanStructuredResponse.
        """

        messages = [
            {
                "role": "system",
                "content": self.system_prompt,
            }
        ]

        # ========================================================
        # Tambahkan history percakapan
        # ========================================================

        for msg in history:
            messages.append(
                {
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                }
            )

        # ========================================================
        # Tambahkan pesan user saat ini
        #
        # user_message sudah dapat berisi konteks RAG
        # ========================================================

        messages.append(
            {
                "role": "user",
                "content": (
                    f"{user_message}\n\n"
                    f"{JSON_FORMAT_INSTRUCTION}"
                ),
            }
        )

        # ========================================================
        # Request ke LLM dengan retry
        # ========================================================

        response_text = ""

        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                )

                if not response.choices:
                    response_text = ""
                else:
                    response_text = (
                        response.choices[0].message.content or ""
                    ).strip()

                break

            except Exception as e:
                err_str = str(e).lower()

                is_rate_limit = (
                    "rate_limit" in err_str
                    or "429" in err_str
                )

                if (
                    is_rate_limit
                    and attempt < self.max_retries - 1
                ):
                    wait_time = 3 * (attempt + 1)

                    print(
                        f"[INFO] Rate limit Groq, "
                        f"menunggu {wait_time}s... "
                        f"({attempt + 1}/{self.max_retries})"
                    )

                    time.sleep(wait_time)

                else:
                    if attempt == self.max_retries - 1:
                        print(
                            f"[ERROR] LLMService gagal setelah "
                            f"{self.max_retries} percobaan: {e}"
                        )

                        return {
                            "reply": (
                                "Maaf, sistem AI kami sedang "
                                "sibuk atau mengalami gangguan "
                                "sesaat. Mohon coba tanyakan "
                                "kembali ya! 🙏"
                            ),
                            "intent": "OUT_OF_SCOPE",
                            "show_cta": False,
                            "cta_text": None,
                            "cta_url": None,
                            "is_fallback": True,
                            "error": str(e),
                        }

        # ========================================================
        # Ekstraksi JSON
        # ========================================================

        response_json = extract_json(response_text)

        # ========================================================
        # Jika LLM tidak mengembalikan JSON
        # ========================================================

        if response_json is None:
            clean_reply = self._clean_response(
                response_text
            )

            return {
                "reply": (
                    clean_reply
                    if clean_reply
                    else FALLBACK_MESSAGE
                ),
                "intent": "ABOUT_AGENCY",
                "show_cta": False,
                "cta_text": "📝 DAFTAR JADI KOL",
                "cta_url": REGISTRATION_URL,
                "is_fallback": False,
            }

        # ========================================================
        # Validasi Intent
        # ========================================================

        raw_intent = str(
            response_json.get(
                "intent",
                "ABOUT_AGENCY",
            )
        ).upper()

        if raw_intent not in VALID_INTENTS:
            raw_intent = "ABOUT_AGENCY"

        response_json["intent"] = raw_intent

        # ========================================================
        # Bersihkan reply
        # ========================================================

        if "reply" in response_json:
            response_json["reply"] = self._clean_response(
                str(response_json["reply"])
            )

        # ========================================================
        # Pastikan field CTA
        # ========================================================

        if response_json.get("show_cta"):
            response_json["cta_url"] = (
                response_json.get("cta_url")
                or REGISTRATION_URL
            )

            response_json["cta_text"] = (
                response_json.get("cta_text")
                or "📝 DAFTAR JADI KOL"
            )

        # ========================================================
        # Validasi schema
        # ========================================================

        try:
            validated = KerajaanStructuredResponse(
                **response_json
            )

            return validated.model_dump()

        except Exception as ve:
            print(
                f"[WARN] Schema validation warning: {ve}"
            )

            return response_json

    # ============================================================
    # GENERATE RESPONSE
    # ============================================================

    def generate_response(
        self,
        messages: list[dict],
    ) -> str:
        """
        Method tambahan untuk kompatibilitas dengan
        penggunaan LLM secara langsung.

        Mengembalikan plain text yang sudah dibersihkan.
        """

        if not messages:
            raise ValueError(
                "Messages tidak boleh kosong."
            )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )

        if not response.choices:
            return ""

        content = response.choices[0].message.content

        if not content:
            return ""

        return self._clean_response(content)