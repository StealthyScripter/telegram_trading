from signals.telegram_bot_listener import TelegramBotListener


def main():
    listener = TelegramBotListener()
    listener.listen_forever(timeout=30)


if __name__ == "__main__":
    main()
