import asyncio
import os
from dotenv import load_dotenv

from import_telegram_history import parse_channels
from signals.telegram_channel_client import TelegramChannelClient

load_dotenv()


async def main():
    raw_channels = os.getenv("TELEGRAM_SIGNAL_CHANNELS", "")

    if not raw_channels:
        raise ValueError("Missing TELEGRAM_SIGNAL_CHANNELS in .env")

    channels = parse_channels(raw_channels)

    client = TelegramChannelClient(channels=channels)

    await client.listen_forever()


if __name__ == "__main__":
    asyncio.run(main())
