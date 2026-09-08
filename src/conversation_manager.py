from typing import Dict, Any, List
from sqlalchemy.orm import Session

from src.database import Conversation


class ConversationManager:
    """
    Mengelola conversation context chatbot Kerajaan Agency.

    Session disimpan sementara di memory untuk development.
    Persistensi chat tetap dapat dilakukan melalui database.
    """

    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def get_session(self, session_id: str) -> Dict[str, Any]:
        """
        Mengambil session atau membuat session baru.
        """

        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "session_id": session_id,
                "messages": [],
            }

        return self.sessions[session_id]

    def add_message(
        self,
        db: Session,
        session_id: str,
        sender: str,
        message: str,
        intent: str = None,
        purchase_intent: str = None,
    ):
        """
        Menambahkan pesan ke memory dan database jika db tersedia.
        """

        session = self.get_session(session_id)

        msg_obj = {
            "sender": sender,
            "text": message,
        }

        session["messages"].append(msg_obj)

        if db is not None:
            db_message = Conversation(
                session_id=session_id,
                sender=sender,
                message=message,
                intent=intent,
                purchase_intent=purchase_intent,
            )

            db.add(db_message)
            db.commit()

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

        for msg in reversed(recent):
            text = msg.get("text", "")

            if total_chars + len(text) > max_chars:
                break

            sender = msg.get("sender")

            role = (
                "assistant"
                if sender == "bot"
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

    def clear_session(self, session_id: str):
        """
        Menghapus conversation session dari memory.
        """

        self.sessions.pop(session_id, None)