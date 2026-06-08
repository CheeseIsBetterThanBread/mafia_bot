from config.settings import ADAPTER_TYPE, AdapterType

from utils.logger import LOGGER
from utils.user_confirmation import confirm

def run_adapter():
    match ADAPTER_TYPE:
        case AdapterType.TELEGRAM:
            from adapters.telegram.bot import run_bot
            run_bot()
        case AdapterType.VK:
            from adapters.vk.bot import run_bot
            run_bot()
        case _:
            raise ValueError("Unknown adapter")

if __name__ == "__main__":
    print("Launching bot")
    try:
        run_adapter()
    except KeyboardInterrupt:
        print("\nGraceful shutdown\n")
        if confirm("Save verbose logs?", default_answer=False):
            LOGGER.save_verbose_log()
