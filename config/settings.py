from dotenv import load_dotenv
from enum import Enum
from pathlib import Path

import os

load_dotenv()

CONFIG_DIR = Path(__file__).parent.resolve()
ROOT_DIR = CONFIG_DIR.parent
DATABASE_DIR = ROOT_DIR / "database"

CACHE_TTL_SECONDS = 3600


# --- adapters ---
class AdapterType(Enum):
    TELEGRAM = "telegram"
    VK = "vk"


ADAPTER_TYPE = AdapterType.TELEGRAM

# --- telegram ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_ADMINS = [
    int(admin_id)
    for admin_id in os.getenv("TELEGRAM_ADMINS", "").split(",")
    if admin_id
]

# --- vk ---
VK_BOT_TOKEN = os.getenv("VK_BOT_TOKEN", "")
VK_ADMINS = [
    int(admin_id) for admin_id in os.getenv("VK_ADMINS", "").split(",") if admin_id
]

# --- database path ---
TELEGRAM_DB_PATH = DATABASE_DIR / "telegram.db"
VK_DB_PATH = DATABASE_DIR / "vk.db"

match ADAPTER_TYPE:
    case AdapterType.TELEGRAM:
        DB_PATH = TELEGRAM_DB_PATH
    case AdapterType.VK:
        DB_PATH = VK_DB_PATH
    case _:
        raise ValueError(f"Missing database path for adapter {ADAPTER_TYPE}")

# --- day timers ---
SECONDS_PER_PLAYER = 8
SPEECH_LOWER_BOUND = 60
SPEECH_UPPER_BOUND = 90
WARNING_OFFSET = 10

# --- night timers ---
THIEF_TIME = 60
THIEF_LOWER = 20
THIEF_UPPER = 45
NIGHT_TIME = 180
REMINDER_OFFSET = 60

# --- logging ---
LOGS_DIR = ROOT_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOG_FILE = LOGS_DIR / "app.log"
MAX_BYTES_PER_FILE = 2**20
BACKUP_FILES = 3
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(funcName)s - %(message)s"

# --- callback contract ---
NOMINATE_CALLBACK_TEMPLATE = "nom|{chat_id}|{player_number}"
NOMINATE_TYPES = {"chat_id": int, "player_number": int}

VOTE_CALLBACK_TEMPLATE = "v|{chat_id}|{player_number}"
VOTE_TYPES = {"chat_id": int, "player_number": int}

BALANCE_CALLBACK_TEMPLATE = "bal|{chat_id}|{number}"
BALANCE_TYPES = {"chat_id": int, "number": int}

NIGHT_CALLBACK_TEMPLATE = "n|{chat_id}|{action}|{target}"
NIGHT_TYPES = {"chat_id": int, "target": int}

NULL_OPTION = 0

# --- role assignment ---
PLAIN_ASSIGNMENT = 1
BALANCE_ASSIGNMENT = 2
SIMULATION_ASSIGNMENT = 4

CURRENT_ASSIGNMENT = PLAIN_ASSIGNMENT | BALANCE_ASSIGNMENT | SIMULATION_ASSIGNMENT
assert (CURRENT_ASSIGNMENT & PLAIN_ASSIGNMENT) != 0 or (CURRENT_ASSIGNMENT & BALANCE_ASSIGNMENT) != 0

BALANCE_CUT_OFF = 5.0

PROBABILITY_THRESHOLD = 0.05
NIGHT_LOWER = 40
NIGHT_UPPER = 70
