import asyncio
import logging
import os

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from src.config import (
    PROJECT_ROOT,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHANNEL_URL,
    WHATSAPP_CHANNEL_URL,
)
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
                "Mohon maaf, kami belum dapat memberikan "
                "jawaban untuk pertanyaan tersebut 🙏"
            )

    except Exception as exc:
        logger.exception(
            "Pipeline error | chat_id=%s",
            chat.id,
        )

        reply = (
            "Mohon maaf, terjadi gangguan pada sistem 🙏\n\n"
            "Silakan coba kirim pesan kembali beberapa saat lagi."
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
# Start Command Handler
# ============================================================

async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Menangani perintah /start dari user Telegram.
    Mengirimkan:
    1. Flyer sambutan (assets/flyer.jpg)
    2. Dokumen PDF Company Profile (assets/company_profile.pdf)
    3. Bubble chat pesan selamat datang
    """
    if not update.effective_chat:
        return

    chat_id = update.effective_chat.id
    user_first_name = f" {update.effective_user.first_name}" if (update.effective_user and update.effective_user.first_name) else ""

    assets_dir = os.path.join(PROJECT_ROOT, "assets")
    flyer_path = os.path.join(assets_dir, "flyer.jpg")
    pdf_path = os.path.join(assets_dir, "company_profile.pdf")

    # 1. Kirim Flyer jika tersedia
    if os.path.exists(flyer_path):
        try:
            with open(flyer_path, "rb") as photo_file:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=photo_file,
                    caption="👑 *Selamat Datang di Kerajaan Agency!*",
                    parse_mode="Markdown",
                )
        except Exception as exc:
            logger.warning("Gagal mengirim flyer: %s", exc)

    # 2. Kirim PDF Company Profile jika tersedia
    if os.path.exists(pdf_path):
        try:
            with open(pdf_path, "rb") as doc_file:
                await context.bot.send_document(
                    chat_id=chat_id,
                    document=doc_file,
                    caption="📄 *Company Profile Kerajaan Agency*",
                    parse_mode="Markdown",
                )
        except Exception as exc:
            logger.warning("Gagal mengirim company profile PDF: %s", exc)

    # 3. Kirim Pesan Sambutan (Bubble Chat)
    welcome_message = (
        f"Halo{user_first_name}! Selamat datang di *Kerajaan Agency Bot* 👑✨\n\n"
        "Saya adalah asisten resmi yang siap membantu Anda, baik calon kreator yang ingin berkembang bersama kami maupun pemilik brand yang ingin bekerja sama.\n\n"
        "📢 *PENTING: Jangan lewatkan info terbaru!*\n"
        "Sangat disarankan untuk segera bergabung ke saluran resmi kami agar selalu mendapatkan update produk terlaris, sampel gratis, jadwal live class/mentoring, serta tips FYP:\n"
        f"👉 *Telegram Channel:* {TELEGRAM_CHANNEL_URL}\n"
        f"👉 *WhatsApp Channel:* {WHATSAPP_CHANNEL_URL}\n\n"
        "Di sini Anda dapat menanyakan berbagai hal seputar:\n"
        "• 🎁 *Program Creator & KOL*: Syarat gabung, sampel gratis, content kit, dan komisi\n"
        "• 🏭 *Kemitraan Produsen/Maklon*: Model kerja sama dan uji pasar produk\n"
        "• 📝 *Pendaftaran Resmi*: Panduan mendaftar jadi kreator/partner\n\n"
        "Silakan ketik langsung pertanyaan Anda! 😊"
    )

    try:
        await update.message.reply_text(
            welcome_message,
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )
    except Exception as exc:
        logger.exception("Gagal mengirim welcome message: %s", exc)


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
    # Command Handler (/start)
    # ========================================================

    application.add_handler(
        CommandHandler("start", start_command)
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