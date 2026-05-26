from dotenv import load_dotenv
from pathlib import Path

import os

load_dotenv()

# --- telegram ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_ADMINS = [
    int(admin_id)
    for admin_id in os.getenv("TELEGRAM_ADMINS", "").split(",")
    if admin_id
]

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
CONFIG_DIR = Path(__file__).parent.resolve()
ROOT_DIR = CONFIG_DIR.parent

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
