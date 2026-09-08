import re
from typing import Dict, Any, List, Optional

from sqlalchemy.orm import Session

from src.database import Conversation


# ============================================================
# Trigger Minat Bergabung / CTA
# ============================================================

JOIN_TRIGGERS = [
    r"\bmau\s+(daftar|gabung|join)\b",
    r"\bcara\s+(daftar|gabung|join)\b",
    r"\b(daftar|gabung|join)\s+(kol|creator|affiliate|agensi|agency)\b",
    r"\bjadi\s+(kol|creator|affiliate)\b",
    r"\blink\s+(daftar|pendaftaran|registrasi)\b",
    r"\bformulir\s+(daftar|pendaftaran|registrasi)\b",
    r"\b(mau|minta|klaim|dapat)\s+sample\b",
    r"\btertarik\s+(gabung|join|daftar)\b",
    r"\bkomisi\b",
    r"\bpenghasilan\b",
]


# ============================================================
# Trigger Produsen / Maklon
# ============================================================

PRODUSEN_TRIGGERS = [
    r"\b(mitra|kemitraan|partner)\s+(produsen|pabrik|maklon|brand)\b",
    r"\bjual\s+produk\b",
    r"\btitip\s+produk\b",
    r"\bmaklon\b",
    r"\bcurated\s+product\b",
]


class ConversationManager:
    """
    Mengelola state percakapan, riwayat chat,
    klasifikasi user, dan deteksi minat untuk
    Kerajaan Agency Chatbot.

    Session disimpan sementara di memory.
    Persistensi conversation dapat dilakukan
    melalui database SQLite.
    """

    def __init__(self):
        # In-memory session store
        self.sessions: Dict[str, Dict[str, Any]] = {}

    # ========================================================
    # SESSION
    # ========================================================

    def get_session(
        self,
        session_id: str,
    ) -> Dict[str, Any]:
        """
        Mengambil session atau membuat session baru.
        """

        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "session_id": session_id,
                "user_type": "CREATOR",
                "last_intent": None,
                "interest_level": "LOW",
                "show_cta": False,
                "messages": [],
            }

        return self.sessions[session_id]

    # ========================================================
    # PROMOTION / CTA TRIGGER
    # ========================================================

    def check_promotion_trigger(
        self,
        message: str,
        intent: Optional[str] = None,
    ) -> bool:
        """
        Mengecek apakah pesan user atau intent
        memicu CTA pendaftaran.

        Trigger aktif jika:
        - intent = JOIN_KOL
        - atau pesan mengandung keyword minat tinggi.
        """

        if intent == "JOIN_KOL":
            return True

        lower_msg = message.lower()

        for pattern in JOIN_TRIGGERS:
            if re.search(pattern, lower_msg):
                return True

        return False

    # ========================================================
    # USER TYPE
    # ========================================================

    def check_user_type(
        self,
        message: str,
    ) -> Optional[str]:
        """
        Mendeteksi apakah user merupakan produsen/maklon.
        """

        lower_msg = message.lower()

        for pattern in PRODUSEN_TRIGGERS:
            if re.search(pattern, lower_msg):
                return "PRODUSEN"

        return None

    # ========================================================
    # UPDATE SESSION
    # ========================================================

    def update_session(
        self,
        session_id: str,
        intent: Optional[str] = None,
        show_cta: bool = False,
        user_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Memperbarui state session berdasarkan
        intent, CTA, dan tipe user.
        """

        session = self.get_session(session_id)

        # ----------------------------------------------------
        # Intent
        # ----------------------------------------------------

        if intent:
            session["last_intent"] = intent

            if intent in [
                "JOIN_KOL",
                "CREATOR_BENEFIT",
                "MONETIZATION",
            ]:
                session["interest_level"] = "HIGH"

            elif intent in [
                "ABOUT_AGENCY",
                "FAQ",
            ]:
                if session["interest_level"] != "HIGH":
                    session["interest_level"] = "MEDIUM"

        # ----------------------------------------------------
        # CTA
        # ----------------------------------------------------

        if show_cta:
            session["show_cta"] = True

        # ----------------------------------------------------
        # User Type
        # ----------------------------------------------------

        if user_type:
            session["user_type"] = user_type

        return session

    # ========================================================
    # ADD MESSAGE
    # ========================================================

    def add_message(
        self,
        db: Optional[Session],
        session_id: str,
        sender: str,
        message: str,
        intent: Optional[str] = None,
        purchase_intent: Optional[str] = None,
    ):
        """
        Menambahkan pesan ke memory dan database.

        Parameter db dibuat sebagai argumen pertama setelah self
        agar kompatibel dengan pipeline versi rehan.
        """

        session = self.get_session(session_id)

        # ----------------------------------------------------
        # Memory
        # ----------------------------------------------------

        session["messages"].append(
            {
                "sender": sender,
                "text": message,
            }
        )

        # ----------------------------------------------------
        # Database
        # ----------------------------------------------------

        if db is not None:
            try:
                db_message = Conversation(
                    session_id=session_id,
                    sender=sender,
                    message=message,
                    intent=intent,
                    purchase_intent=(
                        purchase_intent
                        if purchase_intent is not None
                        else session.get("interest_level")
                    ),
                )

                db.add(db_message)
                db.commit()

            except Exception as e:
                db.rollback()

                print(
                    "[WARN] Gagal menyimpan conversation "
                    f"ke DB: {e}"
                )

    # ========================================================
    # GET HISTORY
    # ========================================================

    def get_history(
        self,
        session_id: str,
        limit: int = 10,
        max_chars: int = 6000,
    ) -> List[Dict[str, str]]:
        """
        Mengambil history percakapan terakhir.

        Output:
        [
            {
                "role": "user",
                "content": "..."
            },
            {
                "role": "assistant",
                "content": "..."
            }
        ]
        """

        session = self.get_session(session_id)

        recent = session["messages"][-limit:]

        history = []
        total_chars = 0

        # Ambil dari pesan terbaru ke terlama
        for msg in reversed(recent):
            text = msg.get("text", "")

            if total_chars + len(text) > max_chars:
                break

            sender = msg.get("sender")

            role = (
                "assistant"
                if sender in ["bot", "assistant"]
                else "user"
            )

            history.append(
                {
                    "role": role,
                    "content": text,
                }
            )

            total_chars += len(text)

        return list(reversed(history))

    # ========================================================
    # CLEAR SESSION
    # ========================================================

    def clear_session(
        self,
        session_id: str,
    ):
        """
        Menghapus conversation session dari memory.
        """

        self.sessions.pop(
            session_id,
            None,
        )