import re
from dataclasses import dataclass, asdict
from enum import Enum

from contracts.parsed_signal import ParsedSignal as ParsedSignalContract
from contracts.parsed_signal import ParsedSignalStatus
from contracts.raw_message import RawMessage


class SignalParseStatus(str, Enum):
    VALID_SIGNAL = "VALID_SIGNAL"
    PARTIAL_SIGNAL = "PARTIAL_SIGNAL"
    INVALID_SIGNAL = "INVALID_SIGNAL"
    COMMENTARY_ONLY = "COMMENTARY_ONLY"
    CLOSE_SIGNAL = "CLOSE_SIGNAL"
    UPDATE_SIGNAL = "UPDATE_SIGNAL"


@dataclass
class ParsedSignal:
    status: SignalParseStatus
    symbol: str | None = None
    action: str | None = None
    entry_type: str | None = None  # market, limit, stop, unknown
    entry_price: str | None = None
    stop_loss: str | None = None
    take_profits: list[str] | None = None
    raw_text: str | None = None
    reason: str | None = None

    def to_dict(self):
        data = asdict(self)
        data["status"] = self.status.value
        return data


class SignalParser:
    ACTIONS = {
        "BUY": "buy",
        "SELL": "sell",
        "LONG": "buy",
        "SHORT": "sell",
    }

    SYMBOL_ALIASES = {
        "EURUSD": "EUR_USD",
        "EUR/USD": "EUR_USD",
        "EUR_USD": "EUR_USD",
        "GBPUSD": "GBP_USD",
        "GBP/USD": "GBP_USD",
        "GBP_USD": "GBP_USD",
        "USDJPY": "USD_JPY",
        "USD/JPY": "USD_JPY",
        "USD_JPY": "USD_JPY",
        "XAUUSD": "XAU_USD",
        "XAU/USD": "XAU_USD",
        "XAU_USD": "XAU_USD",
        "GOLD": "XAU_USD",
    }

    def parse(self, raw_text: str) -> ParsedSignal:
        text = self._clean_text(raw_text)

        if not text:
            return ParsedSignal(
                status=SignalParseStatus.INVALID_SIGNAL,
                raw_text=raw_text,
                reason="Empty message",
            )

        if self._is_close_signal(text):
            return ParsedSignal(
                status=SignalParseStatus.CLOSE_SIGNAL,
                raw_text=raw_text,
                reason="Close signal detected",
            )

        if self._is_update_signal(text):
            return ParsedSignal(
                status=SignalParseStatus.UPDATE_SIGNAL,
                raw_text=raw_text,
                reason="Update signal detected",
            )

        action = self._extract_action(text)
        symbol = self._extract_symbol(text)

        if not action and not symbol:
            return ParsedSignal(
                status=SignalParseStatus.COMMENTARY_ONLY,
                raw_text=raw_text,
                reason="No symbol or action found",
            )

        entry_type = self._extract_entry_type(text)
        entry_price = self._extract_entry_price(text)
        stop_loss = self._extract_stop_loss(text)
        take_profits = self._extract_take_profits(text)

        missing = []

        if not symbol:
            missing.append("symbol")

        if not action:
            missing.append("action")

        if not stop_loss:
            missing.append("stop_loss")

        if not take_profits:
            missing.append("take_profit")

        status = (
            SignalParseStatus.VALID_SIGNAL
            if not missing
            else SignalParseStatus.PARTIAL_SIGNAL
        )

        return ParsedSignal(
            status=status,
            symbol=symbol,
            action=action,
            entry_type=entry_type,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profits=take_profits,
            raw_text=raw_text,
            reason=None if not missing else f"Missing: {', '.join(missing)}",
        )

    def parse_raw_message(self, raw_message: RawMessage) -> ParsedSignalContract:
        parsed = self.parse(raw_message.raw_text)

        return ParsedSignalContract(
            raw_message_id=raw_message.id,
            source=raw_message.source,
            status=ParsedSignalStatus(parsed.status.value),
            symbol=parsed.symbol,
            action=parsed.action,
            entry_type=parsed.entry_type,
            entry_price=parsed.entry_price,
            stop_loss=parsed.stop_loss,
            take_profits=parsed.take_profits or [],
            reason=parsed.reason,
            raw_text=parsed.raw_text,
        )

    def _clean_text(self, raw_text: str) -> str:
        return re.sub(r"\s+", " ", raw_text.strip().upper())

    def _extract_action(self, text: str) -> str | None:
        for keyword, action in self.ACTIONS.items():
            if re.search(rf"\b{keyword}\b", text):
                return action

        return None

    def _extract_symbol(self, text: str) -> str | None:
        for alias, normalized in self.SYMBOL_ALIASES.items():
            if alias in text:
                return normalized

        return None

    def _extract_entry_type(self, text: str) -> str:
        if "BUY NOW" in text or "SELL NOW" in text or "MARKET" in text:
            return "market"

        if "LIMIT" in text:
            return "limit"

        if "STOP" in text and "STOP LOSS" not in text:
            return "stop"

        return "market" if "NOW" in text else "unknown"

    def _extract_entry_price(self, text: str) -> str | None:
        patterns = [
            r"\bENTRY\s*[:@]?\s*(\d+(?:\.\d+)?)",
            r"\bENTER\s*[:@]?\s*(\d+(?:\.\d+)?)",
            r"@\s*(\d+(?:\.\d+)?)",
            r"\bPRICE\s*[:@]?\s*(\d+(?:\.\d+)?)",
            r"\bLIMIT\s*[:@]?\s*(\d+(?:\.\d+)?)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)

        return None

    def _extract_stop_loss(self, text: str) -> str | None:
        patterns = [
            r"\bSL\s*[:@]?\s*(\d+(?:\.\d+)?)",
            r"\bS/L\s*[:@]?\s*(\d+(?:\.\d+)?)",
            r"\bSTOP\s*LOSS\s*[:@]?\s*(\d+(?:\.\d+)?)",
            r"\bSTOPLOSS\s*[:@]?\s*(\d+(?:\.\d+)?)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)

        return None

    def _extract_take_profits(self, text: str) -> list[str]:
        take_profits = []

        tp_patterns = [
            r"\bTP\d*\s*[:@]?\s*(\d+(?:\.\d+)?)",
            r"\bTAKE\s*PROFIT\d*\s*[:@]?\s*(\d+(?:\.\d+)?)",
        ]

        for pattern in tp_patterns:
            matches = re.findall(pattern, text)
            take_profits.extend(matches)

        # Deduplicate while preserving order
        seen = set()
        unique = []

        for tp in take_profits:
            if tp not in seen:
                unique.append(tp)
                seen.add(tp)

        return unique

    def _is_close_signal(self, text: str) -> bool:
        close_keywords = [
            "CLOSE NOW",
            "CLOSE TRADE",
            "CLOSE POSITION",
            "EXIT NOW",
            "EXIT TRADE",
        ]

        return any(keyword in text for keyword in close_keywords)

    def _is_update_signal(self, text: str) -> bool:
        update_keywords = [
            "MOVE SL",
            "MOVE STOP",
            "SL TO BE",
            "STOP TO BE",
            "BREAKEVEN",
            "BREAK EVEN",
            "CANCEL SIGNAL",
            "DELETE SIGNAL",
        ]

        return any(keyword in text for keyword in update_keywords)
