import uuid
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from src.config import (
    FAISS_INDEX_DIR,
    MAX_CONVERSATION_HISTORY,
    RAG_TOP_K,
    RAG_MAX_CONTEXT_TOKENS,
    REGISTRATION_URL,
)
from src.llm_service import LLMService
from src.rag_service import RAGService
from src.conversation_manager import ConversationManager


class ChatPipeline:
    """
    Orkestrator utama chatbot Kerajaan Agency.

    Flow:
        Telegram
            ↓
        ChatPipeline
            ↓
        Conversation Manager
            ↓
        RAG Retrieval
            ↓
        LLM Service + Prompt Template
            ↓
        Structured Response
            ↓
        Telegram
    """

    def __init__(self, load_index: bool = True):
        self.llm = LLMService()

        self.rag = RAGService(
            index_dir=FAISS_INDEX_DIR
        )

        if load_index:
            try:
                self.rag.load_index()
            except Exception as exc:
                print(
                    f"[WARN] FAISS index belum dapat dimuat: {exc}"
                )
                print(
                    "[WARN] Pastikan index sudah tersedia "
                    "atau jalankan rebuild_index.py."
                )

        self.conv_manager = ConversationManager()

    def chat(
        self,
        user_message: str,
        session_id: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Memproses satu pesan user dari awal hingga akhir.
        """

        # =====================================================
        # 1. Validasi input
        # =====================================================

        if not user_message or not user_message.strip():
            return {
                "session_id": session_id,
                "reply": (
                    "Silakan kirim pertanyaan yang ingin Anda "
                    "ketahui tentang Kerajaan Agency 😊"
                ),
                "intent": "FAQ",
                "show_cta": False,
                "cta_text": None,
                "cta_url": None,
                "is_fallback": False,
                "rag_sources": [],
            }

        user_message = user_message.strip()

        # =====================================================
        # 2. Session
        # =====================================================

        if not session_id:
            session_id = str(uuid.uuid4())

        self.conv_manager.get_session(session_id)

        # Deteksi tipe user
        detected_user_type = self.conv_manager.check_user_type(
            user_message
        )

        if detected_user_type:
            self.conv_manager.update_session(
                session_id=session_id,
                user_type=detected_user_type,
            )

        # =====================================================
        # 3. Conversation History
        # =====================================================

        history = self.conv_manager.get_history(
            session_id=session_id,
            limit=MAX_CONVERSATION_HISTORY,
        )

        # =====================================================
        # 4. RAG Retrieval
        # =====================================================

        rag_results = []
        rag_context = ""

        try:
            rag_results = self.rag.search(
                user_message,
                top_k=RAG_TOP_K,
            )

            rag_context = self.rag.construct_context(
                rag_results,
                max_chars=RAG_MAX_CONTEXT_TOKENS,
            )

        except Exception as exc:
            print(f"[WARN] RAG search gagal: {exc}")

        # =====================================================
        # 5. Build augmented user message
        # =====================================================

        augmented_message = user_message

        if rag_context:
            augmented_message = (
                "[KONTEKS DARI KNOWLEDGE BASE KERAJAAN AGENCY]\n"
                f"{rag_context}\n"
                "[END KONTEKS]\n\n"
                f"Pertanyaan pengguna: {user_message}"
            )

        # =====================================================
        # 6. Call LLM
        # =====================================================

        try:
            llm_response = self.llm.chat_with_history(
                user_message=augmented_message,
                history=history,
                raw_user_message=user_message,
            )

        except Exception as exc:
            print(
                f"[ERROR] LLM gagal untuk session "
                f"{session_id}: {exc}"
            )

            return {
                "session_id": session_id,
                "reply": (
                    "Mohon maaf, sistem kami sedang mengalami "
                    "gangguan 🙏\n\n"
                    "Silakan coba kirim ulang pertanyaan Anda "
                    "beberapa saat lagi."
                ),
                "intent": "FAQ",
                "show_cta": False,
                "cta_text": None,
                "cta_url": None,
                "is_fallback": True,
                "rag_sources": [],
            }

        # =====================================================
        # 7. Extract structured response
        # =====================================================

        reply_text = llm_response.get("reply", "").strip()

        intent = llm_response.get(
            "intent",
            "ABOUT_AGENCY",
        )

        show_cta = bool(
            llm_response.get("show_cta", False)
        )

        # =====================================================
        # 8. CTA trigger
        # =====================================================

        should_trigger_cta = (
            self.conv_manager.check_promotion_trigger(
                user_message,
                intent,
            )
        )

        if should_trigger_cta:
            show_cta = True

        cta_text = (
            llm_response.get("cta_text")
            or "📝 DAFTAR JADI KOL"
        )

        cta_url = (
            llm_response.get("cta_url")
            or REGISTRATION_URL
        )

        # =====================================================
        # 9. Update session
        # =====================================================

        self.conv_manager.update_session(
            session_id=session_id,
            intent=intent,
            show_cta=show_cta,
        )

        # =====================================================
        # 10. Save conversation
        # =====================================================

        self.conv_manager.add_message(
            db=db,
            session_id=session_id,
            sender="user",
            message=user_message,
            intent=intent,
        )

        self.conv_manager.add_message(
            db=db,
            session_id=session_id,
            sender="bot",
            message=reply_text,
            intent=intent,
        )

        # =====================================================
        # 11. RAG sources
        # =====================================================

        rag_sources = []

        for doc, _score in rag_results:
            source = doc.metadata.get("source")

            if source and source not in rag_sources:
                rag_sources.append(source)

        # =====================================================
        # 12. Final response
        # =====================================================

        return {
            "session_id": session_id,
            "reply": reply_text,
            "intent": intent,
            "show_cta": show_cta,
            "cta_text": cta_text if show_cta else None,
            "cta_url": cta_url if show_cta else None,
            "is_fallback": llm_response.get(
                "is_fallback",
                False,
            ),
            "rag_sources": rag_sources,
        }