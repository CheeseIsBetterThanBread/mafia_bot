from adapters.telegram.bot import run_bot

if __name__ == "__main__":
    print("Launching bot")
    try:
        run_bot()
    except KeyboardInterrupt:
        print("Graceful shutdown")
