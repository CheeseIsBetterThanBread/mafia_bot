from pathlib import Path

# --- telegram ---
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_ADMIN_ID = 0
TELEGRAM_ADMINS = [TELEGRAM_ADMIN_ID]

# --- timers ---
SECONDS_PER_PLAYER = 8
SPEECH_LOWER_BOUND = 60
SPEECH_UPPER_BOUND = 90
WARNING_OFFSET = 10

# --- logging ---
CONFIG_DIR = Path(__file__).parent.resolve()
ROOT_DIR = CONFIG_DIR.parent

LOGS_DIR = ROOT_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOG_FILE = LOGS_DIR / "app.log"
MAX_BYTES_PER_FILE = 2 ** 20
BACKUP_FILES = 3

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
