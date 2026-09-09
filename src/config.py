import os
from dotenv import load_dotenv


# ============================================================
# Environment
# ============================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

DOTENV_PATH = os.path.join(
    PROJECT_ROOT,
    ".env"
)

load_dotenv(dotenv_path=DOTENV_PATH)


# ============================================================
# LLM - Groq / OpenAI-Compatible API
# ============================================================

LLM_API_KEY = os.getenv(
    "GROQ_API_KEY",
    ""
)

LLM_BASE_URL = os.getenv(
    "LLM_BASE_URL",
    os.getenv(
        "GROQ_BASE_URL",
        "https://api.groq.com/openai/v1"
    )
)

LLM_MODEL = os.getenv(
    "LLM_MODEL",
    os.getenv(
        "GROQ_MODEL",
        "openai/gpt-oss-20b"
    )
)

LLM_MAX_TOKENS = int(
    os.getenv(
        "LLM_MAX_TOKENS",
        "2048"
    )
)

LLM_TEMPERATURE = float(
    os.getenv(
        "LLM_TEMPERATURE",
        "0.2"
    )
)

LLM_MAX_RETRIES = int(
    os.getenv(
        "LLM_MAX_RETRIES",
        "3"
    )
)

if not LLM_API_KEY:
    print(
        "[WARNING] GROQ_API_KEY belum diset."
    )

print("[INFO] LLM Provider: Groq")
print(f"[INFO] LLM Model: {LLM_MODEL}")


# ============================================================
# Telegram Bot
# ============================================================

TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN",
    ""
)

if not TELEGRAM_BOT_TOKEN:
    print(
        "[WARNING] TELEGRAM_BOT_TOKEN belum diset."
    )


# ============================================================
# Kerajaan Agency
# ============================================================

REGISTRATION_URL = os.getenv(
    "REGISTRATION_URL",
    "https://kerajaanagency.com/daftar-kol"
)

TELEGRAM_CHANNEL_URL = os.getenv(
    "TELEGRAM_CHANNEL_URL",
    "https://t.me/+3ZJBNBYh8iU4MGM1"
)

WHATSAPP_CHANNEL_URL = os.getenv(
    "WHATSAPP_CHANNEL_URL",
    "https://whatsapp.com/channel/0029VbDUpC07T8bZYVq3KW02"
)


# ============================================================
# Database & Storage Paths
# ============================================================

DB_PATH = (
    f"sqlite:///"
    f"{os.path.join(PROJECT_ROOT, 'data', 'kerajaan_agency.db')}"
)

KNOWLEDGE_BASE_DIR = os.path.join(
    PROJECT_ROOT,
    "knowledge_base"
)

FAISS_INDEX_DIR = os.path.join(
    PROJECT_ROOT,
    "faiss_index"
)


# ============================================================
# RAG Settings
# ============================================================

EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "intfloat/multilingual-e5-small"
)

RAG_TOP_K = int(
    os.getenv(
        "RAG_TOP_K",
        "6"
    )
)

RAG_MAX_CONTEXT_TOKENS = int(
    os.getenv(
        "RAG_MAX_CONTEXT_TOKENS",
        "3000"
    )
)


# ============================================================
# Conversation Settings
# ============================================================

MAX_CONVERSATION_HISTORY = int(
    os.getenv(
        "MAX_CONVERSATION_HISTORY",
        "10"
    )
)