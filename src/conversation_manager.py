import re
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from src.database import Conversation

# Keyword triggers untuk mendeteksi minat bergabung / CTA pendaftaran
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

PRODUSEN_TRIGGERS = [
    r"\b(mitra|kemitraan|partner)\s+(produsen|pabrik|maklon|brand)\b",
    r"\bjual\s+produk\b",
    r"\btitip\s+produk\b",
    r"\bmaklon\b",
    r"\bcurated\s+product\b",
]

class ConversationManager:
    """
    Mengelola state percakapan, riwayat chat, klasifikasi minat,
    dan deteksi promotion engine untuk Kerajaan Agency Chatbot.
    """
    def __init__(self):
        # In-memory session store
        self.sessions: Dict[str, Dict[str, Any]] = {}
        
    def get_session(self, session_id: str) -> Dict[str, Any]:
        """
        Mengambil atau menginisialisasi session baru untuk user.
        """
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "session_id": session_id,
                "user_type": "CREATOR",       # CREATOR, PRODUSEN, atau GENERAL
                "last_intent": None,
                "interest_level": "LOW",      # LOW, MEDIUM, HIGH
                "show_cta": False,
                "messages": []
            }
        return self.sessions[session_id]

    def check_promotion_trigger(self, message: str, intent: Optional[str] = None) -> bool:
        """
        Mengecek apakah pesan user atau intent memicu promosi / CTA pendaftaran.
        Trigger aktif jika intent adalah JOIN_KOL atau terdapat keyword minat tinggi.
        """
        if intent == "JOIN_KOL":
            return True

        lower_msg = message.lower()
        for pattern in JOIN_TRIGGERS:
            if re.search(pattern, lower_msg):
                return True
        return False

    def check_user_type(self, message: str) -> Optional[str]:
        """
        Deteksi sederhana apakah user adalah produsen/maklon atau creator.
        """
        lower_msg = message.lower()
        for pattern in PRODUSEN_TRIGGERS:
            if re.search(pattern, lower_msg):
                return "PRODUSEN"
        return None

    def update_session(self, session_id: str, intent: Optional[str] = None, 
                       show_cta: bool = False, user_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Memperbarui status session percakapan.
        """
        session = self.get_session(session_id)
        
        if intent:
            session["last_intent"] = intent
            if intent in ["JOIN_KOL", "CREATOR_BENEFIT", "MONETIZATION"]:
                session["interest_level"] = "HIGH"
            elif intent in ["ABOUT_AGENCY", "FAQ"]:
                if session["interest_level"] != "HIGH":
                    session["interest_level"] = "MEDIUM"
                    
        if show_cta:
            session["show_cta"] = True
            
        if user_type:
            session["user_type"] = user_type
            
        return session
        
    def add_message(self, session_id: str, sender: str, message: str, 
                    intent: Optional[str] = None, db: Optional[Session] = None):
        """
        Menyimpan history pesan ke memori session dan opsional ke database SQLite.
        """
        session = self.get_session(session_id)
        session["messages"].append({"sender": sender, "text": message})
        
        # Simpan ke SQLite jika db session tersedia
        if db is not None:
            try:
                db_msg = Conversation(
                    session_id=session_id,
                    sender=sender,
                    message=message,
                    intent=intent,
                    purchase_intent=session.get("interest_level")
                )
                db.add(db_msg)
                db.commit()
            except Exception as e:
                db.rollback()
                print(f"[WARN] Gagal menyimpan conversation ke DB: {e}")

    def get_history(self, session_id: str, limit: int = 6, max_chars: int = 2500) -> List[Dict[str, str]]:
        """
        Mengambil sejumlah history terakhir untuk konteks LLM.
        """
        session = self.get_session(session_id)
        recent = session["messages"][-limit:]
        
        trimmed = []
        total = 0
        for msg in reversed(recent):
            msg_len = len(msg.get("text", ""))
            if total + msg_len > max_chars:
                break
            trimmed.append(msg)
            total += msg_len
            
        return list(reversed(trimmed))

    def clear_session(self, session_id: str):
        """Reset session percakapan."""
        if session_id in self.sessions:
            del self.sessions[session_id]