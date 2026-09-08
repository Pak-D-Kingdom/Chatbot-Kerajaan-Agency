import uuid
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from src.config import (
    FAISS_INDEX_DIR, 
    MAX_CONVERSATION_HISTORY, 
    RAG_TOP_K, 
    RAG_MAX_CONTEXT_TOKENS,
    REGISTRATION_URL
)
from src.llm_service import LLMService
from src.rag_service import RAGService
from src.conversation_manager import ConversationManager

class ChatPipeline:
    """
    Orkestrator utama chatbot Kerajaan Agency:
    1. Mengelola session percakapan
    2. RAG Retrieval dari Knowledge Base Kerajaan Agency
    3. LLM Generation (Groq / OpenAI-compatible) dengan instruksi persona resmi
    4. Evaluasi Promotion Trigger & Call to Action (CTA) pendaftaran
    """

    def __init__(self, load_index: bool = True):
        self.llm = LLMService()
        self.rag = RAGService(index_dir=FAISS_INDEX_DIR)
        if load_index:
            try:
                self.rag.load_index()
            except Exception as e:
                print(f"[WARN] FAISS index belum dapat dimuat ({e}). Pastikan sudah menjalankan rebuild_index.py.")
        self.conv_manager = ConversationManager()
    
    def chat(self, user_message: str, session_id: Optional[str] = None, 
             db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Memproses pesan customer dari awal hingga akhir.
        """
        # 1. Inisialisasi Session
        if not session_id:
            session_id = str(uuid.uuid4())
        session = self.conv_manager.get_session(session_id)

        # 2. Deteksi tipe pengguna awal (Creator vs Produsen)
        detected_user_type = self.conv_manager.check_user_type(user_message)
        if detected_user_type:
            self.conv_manager.update_session(session_id, user_type=detected_user_type)

        # 3. RAG Retrieval
        rag_results = []
        rag_context = ""
        try:
            rag_results = self.rag.search(user_message, top_k=RAG_TOP_K)
            rag_context = self.rag.construct_context(rag_results, max_chars=RAG_MAX_CONTEXT_TOKENS)
        except Exception as e:
            print(f"[WARN] RAG search gagal: {e}")

        # 4. Ambil Conversation History
        history = self.conv_manager.get_history(session_id, limit=MAX_CONVERSATION_HISTORY)
        formatted_history = []
        for msg in history:
            role = "assistant" if msg.get("sender") == "bot" else "user"
            formatted_history.append({"role": role, "content": msg.get("text", "")})

        # 5. Siapkan Prompt dengan RAG Context
        augmented_message = user_message
        if rag_context:
            augmented_message = (
                f"[KONTEKS DARI KNOWLEDGE BASE KERAJAAN AGENCY]\n"
                f"{rag_context}\n"
                f"[END KONTEKS]\n\n"
                f"Pertanyaan pengguna: {user_message}"
            )

        # 6. Panggil LLM Service (Groq)
        llm_response = self.llm.chat_with_history(
            user_message=augmented_message,
            history=formatted_history,
            raw_user_message=user_message
        )

        reply_text = llm_response.get("reply", "")
        intent = llm_response.get("intent", "ABOUT_AGENCY")
        show_cta = bool(llm_response.get("show_cta", False))

        # 7. Evaluasi Promotion Engine / CTA trigger berbasis keyword & intent
        should_trigger_cta = self.conv_manager.check_promotion_trigger(user_message, intent)
        if should_trigger_cta:
            show_cta = True

        cta_text = llm_response.get("cta_text") or "📝 DAFTAR JADI KOL"
        cta_url = llm_response.get("cta_url") or REGISTRATION_URL

        # 8. Update Session & Simpan History Percakapan
        self.conv_manager.update_session(
            session_id=session_id,
            intent=intent,
            show_cta=show_cta
        )
        self.conv_manager.add_message(session_id, "user", user_message, intent=intent, db=db)
        self.conv_manager.add_message(session_id, "bot", reply_text, intent=intent, db=db)

        # 9. Format Sumber RAG untuk Transparansi
        rag_sources = []
        if rag_results:
            for doc, _ in rag_results:
                src = doc.metadata.get("source")
                if src and src not in rag_sources:
                    rag_sources.append(src)

        return {
            "session_id": session_id,
            "reply": reply_text,
            "intent": intent,
            "show_cta": show_cta,
            "cta_text": cta_text if show_cta else None,
            "cta_url": cta_url if show_cta else None,
            "is_fallback": llm_response.get("is_fallback", False),
            "rag_sources": rag_sources
        }