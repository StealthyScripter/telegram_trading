import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def imports_for(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def test_signals_wrappers_import_production_modules():
    assert "parsing.parser" in imports_for(ROOT / "signals" / "signal_parser.py")
    assert "parsing.processor" in imports_for(ROOT / "signals" / "signal_processor.py")
    assert "storage.signal_store" in imports_for(ROOT / "signals" / "signal_store.py")
    assert "ingestion.telegram.bot_listener" in imports_for(ROOT / "signals" / "telegram_bot_listener.py")
    assert "ingestion.telegram.channel_client" in imports_for(ROOT / "signals" / "telegram_channel_client.py")
    assert "ingestion.telegram.listener" in imports_for(ROOT / "signals" / "telegram_listener.py")


def test_broker_wrappers_import_production_modules():
    assert "execution.brokers.oanda" in imports_for(ROOT / "brokers" / "oanda.py")
    assert "execution.brokers.factory" in imports_for(ROOT / "brokers" / "factory.py")


def test_compatibility_wrappers_remain_importable():
    from brokers.factory import BrokerFactory
    from brokers.oanda import OandaBroker
    from signals.signal_parser import SignalParser
    from signals.signal_processor import SignalProcessor
    from signals.signal_store import SignalStore
    from signals.telegram_bot_listener import TelegramBotListener
    from signals.telegram_channel_client import TelegramChannelClient
    from signals.telegram_listener import TelegramSignalListener

    assert BrokerFactory
    assert OandaBroker
    assert SignalParser
    assert SignalProcessor
    assert SignalStore
    assert TelegramBotListener
    assert TelegramChannelClient
    assert TelegramSignalListener


def test_production_modules_do_not_import_compatibility_wrappers():
    production_dirs = [
        "ingestion",
        "parsing",
        "execution",
        "decision",
        "risk",
        "capital",
        "events",
        "learning",
        "storage",
    ]
    violations = []

    for directory in production_dirs:
        for path in (ROOT / directory).rglob("*.py"):
            for imported in imports_for(path):
                if imported.startswith(("signals", "brokers")):
                    violations.append((str(path.relative_to(ROOT)), imported))

    assert violations == []
