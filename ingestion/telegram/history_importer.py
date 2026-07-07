import asyncio
import os
from dotenv import load_dotenv

from ingestion.telegram.channel_client import TelegramChannelClient

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
        raise ValueError("Missing TELEGRAM_SIGNAL_CHANNELS in .env")

    limit = int(os.getenv("TELEGRAM_HISTORY_LIMIT", "100"))
    channels = parse_channels(raw_channels)

    client = TelegramChannelClient(channels=channels)

    for channel in channels:
        print(f"Importing history from: {channel}")
        results = await client.import_history(
            channel=channel,
            limit=limit,
        )

        saved_count = sum(1 for item in results if item.get("saved"))

        print(f"Imported {len(results)} messages")
        print(f"Saved {saved_count} new signals")


if __name__ == "__main__":
    asyncio.run(main())
