import os
from dotenv import load_dotenv


# ============================================================
# Environment
# ============================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

DOTENV_PATH = os.path.join(PROJECT_ROOT, ".env")

load_dotenv(dotenv_path=DOTENV_PATH)


# ============================================================
# LLM - Groq / OpenAI-Compatible API
# ============================================================

LLM_API_KEY = os.getenv(
    "GROQ_API_KEY",
    ""
)

LLM_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-20b"
)

LLM_BASE_URL = os.getenv(
    "GROQ_BASE_URL",
    "https://api.groq.com/openai/v1"
)

LLM_MAX_TOKENS = int(
    os.getenv("LLM_MAX_TOKENS", "2048")
)

LLM_TEMPERATURE = float(
    os.getenv("LLM_TEMPERATURE", "0.2")
)

LLM_MAX_RETRIES = int(
    os.getenv("LLM_MAX_RETRIES", "3")
)


if not LLM_API_KEY:
    print("[WARNING] GROQ_API_KEY belum diset.")

print("[INFO] LLM Provider: Groq")
print(f"[INFO] LLM Model: {LLM_MODEL}")


# ============================================================
# Telegram
# ============================================================

TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN",
    ""
)

if not TELEGRAM_BOT_TOKEN:
    print("[WARNING] TELEGRAM_BOT_TOKEN belum diset.")


# ============================================================
# Database
# ============================================================

DB_PATH = (
    f"sqlite:///"
    f"{os.path.join(PROJECT_ROOT, 'data', 'nasikotak.db')}"
)


# ============================================================
# Knowledge Base / RAG
# ============================================================

KNOWLEDGE_BASE_DIR = os.path.join(
    PROJECT_ROOT,
    "knowledge_base"
)

FAISS_INDEX_DIR = os.path.join(
    PROJECT_ROOT,
    "faiss_index"
)

EMBEDDING_MODEL = "intfloat/multilingual-e5-small"

RAG_TOP_K = 6

RAG_MAX_CONTEXT_TOKENS = 3000


# ============================================================
# KOL Registration
# ============================================================

KOL_REGISTRATION_URL = os.getenv(
    "KOL_REGISTRATION_URL",
    ""
)

TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN"
)
# ============================================================
# Conversation
# ============================================================

MAX_CONVERSATION_HISTORY = 10