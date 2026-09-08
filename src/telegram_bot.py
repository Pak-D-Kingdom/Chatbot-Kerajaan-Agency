import asyncio
import logging

from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    filters,
)

from src.config import TELEGRAM_BOT_TOKEN
from src.pipeline import ChatPipeline


# ============================================================
# Logging
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# ============================================================
# Pipeline
# ============================================================

pipeline = ChatPipeline()


# ============================================================
# Message Handler
# ============================================================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Menangani pesan teks biasa dari user Telegram.

    Telegram
        ↓
    ChatPipeline
        ↓
    RAG + Prompt + LLM
        ↓
    Telegram Reply
    """

    if not update.message:
        return

    if not update.message.text:
        return

    user_message = update.message.text.strip()

    if not user_message:
        return

    # ========================================================
    # Telegram User Information
    # ========================================================

    user = update.effective_user
    chat = update.effective_chat

    if not chat:
        return

    # Gunakan Telegram chat ID sebagai session ID.
    #
    # Dengan demikian percakapan user yang sama akan
    # mempertahankan context selama process bot hidup.
    session_id = f"telegram_{chat.id}"

    logger.info(
        "Incoming message | user_id=%s | chat_id=%s | message=%s",
        user.id if user else None,
        chat.id,
        user_message,
    )

    # ========================================================
    # Typing Indicator
    # ========================================================

    try:
        await context.bot.send_chat_action(
            chat_id=chat.id,
            action="typing",
        )
    except Exception as exc:
        logger.warning(
            "Gagal mengirim typing indicator: %s",
            exc,
        )

    # ========================================================
    # Run Pipeline
    # ========================================================
    #
    # Pipeline dan LLM bersifat synchronous.
    # asyncio.to_thread() digunakan agar proses LLM/RAG
    # tidak memblokir event loop Telegram.
    #

    try:
        result = await asyncio.to_thread(
            pipeline.chat,
            user_message=user_message,
            session_id=session_id,
        )

        reply = result.get("reply", "")

        if not reply:
            reply = (
                "Maaf kak, aku belum bisa memberikan "
                "jawaban untuk pertanyaan tersebut 🙏"
            )

    except Exception as exc:
        logger.exception(
            "Pipeline error | chat_id=%s",
            chat.id,
        )

        reply = (
            "Maaf kak, terjadi gangguan pada sistem 🙏\n\n"
            "Silakan coba kirim pesan kembali sebentar lagi."
        )

    # ========================================================
    # Send Response
    # ========================================================

    try:
        await update.message.reply_text(
            reply,
            disable_web_page_preview=True,
        )

    except Exception as exc:
        logger.exception(
            "Telegram reply error | chat_id=%s: %s",
            chat.id,
            exc,
        )


# ============================================================
# Error Handler
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Global Telegram error handler.
    """

    logger.error(
        "Telegram error: %s",
        context.error,
        exc_info=context.error,
    )


# ============================================================
# Main
# ============================================================

def main():
    """
    Menjalankan Telegram bot menggunakan polling.

    Development:
        python -m src.telegram_bot
    """

    if not TELEGRAM_BOT_TOKEN:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN belum diset. "
            "Tambahkan token bot ke file .env"
        )

    logger.info(
        "Starting Kerajaan Agency Telegram Bot..."
    )

    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    # ========================================================
    # Natural Text Handler
    # ========================================================

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message,
        )
    )

    # ========================================================
    # Error Handler
    # ========================================================

    application.add_error_handler(
        error_handler
    )

    # ========================================================
    # Start Polling
    # ========================================================

    logger.info(
        "Telegram bot is running..."
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()