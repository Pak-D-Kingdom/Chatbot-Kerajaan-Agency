from typing import Optional, Dict, Any

from sqlalchemy.orm import Session

from src.config import (
    FAISS_INDEX_DIR,
    MAX_CONVERSATION_HISTORY,
    RAG_TOP_K,
    RAG_MAX_CONTEXT_TOKENS,
)

from src.llm_service import LLMService
from src.rag_service import RAGService
from src.conversation_manager import ConversationManager


class ChatPipeline:
    """
    Pipeline utama chatbot Kerajaan Agency.

    Flow:

        User Message
              ↓
        Conversation Manager
              ↓
        RAG Retrieval
              ↓
        Prompt Templates
              ↓
        LLM
              ↓
        Natural Response
              ↓
        Telegram
    """

    def __init__(self):
        self.llm = LLMService()

        self.rag = RAGService(
            index_dir=FAISS_INDEX_DIR
        )

        self.rag.load_index()

        self.conv_manager = ConversationManager()

    def _build_system_prompt(
        self,
        rag_context: str,
    ) -> str:
        """
        Membuat system prompt untuk chatbot Kerajaan Agency.

        Prompt utama sebaiknya dikelola di prompt_templates.py.
        """

        base_prompt = """
You are the official AI assistant of Kerajaan Agency.

Your role is to help users understand Kerajaan Agency,
its creator ecosystem, opportunities, and recruitment
information.

CONVERSATION POLICY:
- Users communicate naturally through chat.
- Do not require Telegram commands.
- Answer the user's actual question directly.
- Maintain conversation context when relevant.
- Be helpful, friendly, concise, and natural.

KNOWLEDGE POLICY:
- Use the provided Knowledge Base as the primary source
  of factual information.
- Only provide factual claims supported by the Knowledge Base.
- Do not invent information.
- Do not guess missing information.
- Do not make up commission amounts.
- Do not promise income.
- Do not promise guaranteed sales.
- Do not promise guaranteed results.
- Do not invent products, programs, requirements,
  policies, or benefits.

RECRUITMENT POLICY:
- If the user shows genuine interest in becoming a
  KOL, Creator, or Affiliate, explain the relevant
  opportunity based on the Knowledge Base.
- Provide registration information only when appropriate.
- Do not repeatedly promote registration.
- Informational questions should be answered directly
  without forcing a registration CTA.

FALLBACK POLICY:
- If the requested information is not available
  in the Knowledge Base, clearly state that the
  information is currently unavailable.
- Never fill missing information with assumptions.

OUT OF SCOPE:
- If the question is unrelated to Kerajaan Agency,
  creator ecosystem, KOL, Creator, Affiliate,
  recruitment, or available Knowledge Base information,
  politely explain what topics you can help with.

KNOWLEDGE BASE CONTEXT:
"""

        if rag_context:
            base_prompt += f"\n{rag_context}"
        else:
            base_prompt += (
                "\nNo relevant Knowledge Base context was found."
            )

        return base_prompt

    def chat(
        self,
        user_message: str,
        session_id: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Memproses satu pesan user melalui pipeline AI.
        """

        if not user_message or not user_message.strip():
            return {
                "session_id": session_id,
                "reply": (
                    "Silakan kirim pertanyaan yang ingin kamu "
                    "ketahui tentang Kerajaan Agency 😊"
                ),
                "rag_sources": [],
            }

        user_message = user_message.strip()

        # =====================================================
        # 1. Session
        # =====================================================

        if session_id is None:
            session_id = f"telegram_{id(user_message)}"

        self.conv_manager.get_session(session_id)

        # =====================================================
        # 2. Conversation History
        # =====================================================

        history = self.conv_manager.get_history(
            session_id=session_id,
            limit=MAX_CONVERSATION_HISTORY,
        )

        # =====================================================
        # 3. RAG Retrieval
        # =====================================================

        rag_results = self.rag.search(
            user_message,
            top_k=RAG_TOP_K,
        )

        rag_context = self.rag.construct_context(
            rag_results,
            max_chars=RAG_MAX_CONTEXT_TOKENS,
        )

        # =====================================================
        # 4. Build System Prompt
        # =====================================================

        system_prompt = self._build_system_prompt(
            rag_context=rag_context
        )

        # =====================================================
        # 5. Build LLM Messages
        # =====================================================

        messages = [
            {
                "role": "system",
                "content": system_prompt,
            }
        ]

        messages.extend(history)

        messages.append(
            {
                "role": "user",
                "content": user_message,
            }
        )

        # =====================================================
        # 6. Call LLM
        # =====================================================

        try:
            reply = self.llm.generate_response(
                messages=messages
            )

        except Exception as exc:
            print(
                f"[ERROR] LLM gagal untuk session "
                f"{session_id}: {exc}"
            )

            reply = (
                "Maaf kak, sistem kami sedang mengalami "
                "gangguan 🙏\n\n"
                "Boleh coba kirim ulang pertanyaannya "
                "sebentar lagi?"
            )

        # =====================================================
        # 7. Save Conversation
        # =====================================================

        if db is not None:
            self.conv_manager.add_message(
                db=db,
                session_id=session_id,
                sender="user",
                message=user_message,
            )

            self.conv_manager.add_message(
                db=db,
                session_id=session_id,
                sender="bot",
                message=reply,
            )

        else:
            session = self.conv_manager.get_session(
                session_id
            )

            session["messages"].append(
                {
                    "sender": "user",
                    "text": user_message,
                }
            )

            session["messages"].append(
                {
                    "sender": "bot",
                    "text": reply,
                }
            )

        # =====================================================
        # 8. Build Result
        # =====================================================

        return {
            "session_id": session_id,
            "reply": reply,
            "rag_sources": [
                doc.metadata.get("source", "")
                for doc in rag_results
            ],
        }