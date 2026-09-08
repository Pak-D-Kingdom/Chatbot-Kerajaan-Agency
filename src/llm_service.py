import re

import httpx2
from openai import OpenAI

from src.config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
)


class LLMService:
    """
    Service untuk komunikasi dengan LLM
    melalui OpenAI-compatible API seperti Groq.

    Output LLM dibersihkan agar cocok dikirim
    langsung ke Telegram sebagai plain text.
    """

    def __init__(self):
        if not LLM_API_KEY:
            raise ValueError(
                "LLM API key belum diset. "
                "Pastikan GROQ_API_KEY ada di file .env"
            )

        # Disable response compression untuk menghindari
        # masalah decompression pada HTTPX2.
        http_client = httpx2.Client(
            headers={
                "Accept-Encoding": "identity",
            },
            timeout=60.0,
        )

        self.client = OpenAI(
            api_key=LLM_API_KEY,
            base_url=LLM_BASE_URL,
            http_client=http_client,
        )

        self.model = LLM_MODEL
        self.max_tokens = LLM_MAX_TOKENS
        self.temperature = LLM_TEMPERATURE

    @staticmethod
    def _clean_response(text: str) -> str:
        """
        Membersihkan output LLM agar menjadi plain text
        yang aman dan rapi untuk Telegram.

        Yang dibersihkan:
        - Markdown bold/italic
        - Markdown links
        - HTML sederhana
        - escape character
        - tabel Markdown
        - heading Markdown
        - output 'svg'
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
        # [Daftar KOL](https://kerajaanagency.com/daftar-kol)
        # →
        # https://kerajaanagency.com/daftar-kol
        # ========================================================

        text = re.sub(
            r"\[([^\]]+)\]\((https?://[^)\s]+)(?:\s+\"[^\"]*\")?\)",
            r"\2",
            text,
        )

        # ========================================================
        # 3. Hapus HTML
        #
        # <br> → newline
        # <b>text</b> → text
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

        # Hapus HTML tag lain yang mungkin muncul
        text = re.sub(
            r"<[^>]+>",
            "",
            text,
        )

        # ========================================================
        # 4. Hapus Markdown bold
        #
        # **text** → text
        # __text__ → text
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
        #
        # *text* → text
        # _text_ → text
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
        #
        # `text` → text
        # ========================================================

        text = re.sub(
            r"`([^`]+)`",
            r"\1",
            text,
        )

        # ========================================================
        # 7. Hapus heading Markdown
        #
        # ## Judul → Judul
        # ========================================================

        text = re.sub(
            r"(?m)^\s{0,3}#{1,6}\s+",
            "",
            text,
        )

        # ========================================================
        # 8. Hapus Markdown blockquote
        #
        # > text → text
        # ========================================================

        text = re.sub(
            r"(?m)^\s*>\s?",
            "",
            text,
        )

        # ========================================================
        # 9. Hapus backslash escape
        #
        # \* → *
        # \_ → _
        # \| → |
        # ========================================================

        text = re.sub(
            r"\\([\\`*_{}\[\]()#+\-.!|>])",
            r"\1",
            text,
        )

        # ========================================================
        # 10. Bersihkan tabel Markdown
        #
        # | Langkah | Keterangan |
        # |---------|------------|
        #
        # Diubah menjadi:
        #
        # - Langkah — Keterangan
        # ========================================================

        lines = text.splitlines()
        cleaned_lines = []

        for line in lines:
            stripped = line.strip()

            # Lewati separator tabel
            # |---------|----------|
            if re.fullmatch(
                r"\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?",
                stripped,
            ):
                continue

            # Jika masih berupa tabel
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
        # 11. Bersihkan bullet Markdown
        #
        # * item → - item
        # + item → - item
        # ========================================================

        text = re.sub(
            r"(?m)^\s*[\*\+]\s+",
            "- ",
            text,
        )

        # ========================================================
        # 12. Rapikan numbered list
        #
        # Tidak mengubah nomor, hanya whitespace berlebih.
        # ========================================================

        text = re.sub(
            r"(?m)^\s*(\d+)\.\s+",
            r"\1. ",
            text,
        )

        # ========================================================
        # 13. Hapus whitespace berlebihan
        # ========================================================

        text = re.sub(
            r"[ \t]+",
            " ",
            text,
        )

        # ========================================================
        # 14. Rapikan terlalu banyak baris kosong
        # ========================================================

        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text,
        )

        # ========================================================
        # 15. Bersihkan whitespace awal/akhir
        # ========================================================

        return text.strip()

    def generate_response(
        self,
        messages: list[dict],
    ) -> str:
        """
        Mengirim conversation messages ke LLM
        dan mengembalikan response dalam bentuk
        plain text yang sudah dibersihkan.
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

        # Bersihkan output sebelum dikirim ke Telegram
        return self._clean_response(content)