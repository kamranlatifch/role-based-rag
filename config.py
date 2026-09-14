import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

MODEL = os.getenv("GEMINI_MODEL", "google/gemini-2.5-flash")
EMBED_MODEL = os.getenv("EMBED_MODEL", "openai/text-embedding-3-small")
API_KEY = os.getenv("COGENT_OPRNROUTER_KEY")
BASE_URL = "https://openrouter.ai/api/v1"

DATA_DIR = ROOT / "data"
INDEX_DIR = ROOT / "index"
USERS_FILE = ROOT / "users.yaml"

ROLES = ("admin", "hr")
COLLECTION_PREFIX = "role_docs_"
TOP_K = 4
MAX_HISTORY_TURNS = 6
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
