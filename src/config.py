import os
from dotenv import load_dotenv

# === Paths ===
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOTENV_PATH = os.path.join(PROJECT_ROOT, ".env")
load_dotenv(dotenv_path=DOTENV_PATH)

# === LLM Provider (Groq / OpenAI-compatible) ===
# Mendukung Groq secara default, fallback ke OPENAI_API_KEY jika ada
LLM_API_KEY = os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2048"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))

# === Telegram Bot ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# === Kerajaan Agency Links ===
REGISTRATION_URL = os.getenv("REGISTRATION_URL", "https://kerajaanagency.com/daftar-kol")

# === Database & Storage Paths ===
DB_PATH = f"sqlite:///{os.path.join(PROJECT_ROOT, 'data', 'kerajaan_agency.db')}"
KNOWLEDGE_BASE_DIR = os.path.join(PROJECT_ROOT, "knowledge_base")
FAISS_INDEX_DIR = os.path.join(PROJECT_ROOT, "faiss_index")

# === RAG Settings ===
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-small")
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "6"))
RAG_MAX_CONTEXT_TOKENS = int(os.getenv("RAG_MAX_CONTEXT_TOKENS", "3000"))

# === Conversation Settings ===
MAX_CONVERSATION_HISTORY = int(os.getenv("MAX_CONVERSATION_HISTORY", "10"))