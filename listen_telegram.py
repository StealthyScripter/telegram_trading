import asyncio
import os
from dotenv import load_dotenv

from signals.telegram_listener import TelegramSignalListener

load_dotenv()


def parse_channels(raw: str) -> list[str | int]:
    channels = []

    for item in raw.split(","):
        item = item.strip()

        if not item:
            continue

        if item.lstrip("-").isdigit():
            channels.append(int(item))
        else:
            channels.append(item)

    return channels


async def main():
    raw_channels = os.getenv("TELEGRAM_SIGNAL_CHANNELS", "")

    if not raw_channels:
        raise ValueError(
            "Missing TELEGRAM_SIGNAL_CHANNELS in .env. "
            "Example: TELEGRAM_SIGNAL_CHANNELS=@channel_one,@channel_two"
        )

    channels = parse_channels(raw_channels)

    listener = TelegramSignalListener(channels=channels)
    await listener.start()


if __name__ == "__main__":
    asyncio.run(main())
