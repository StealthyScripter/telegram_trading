from dataclasses import dataclass


@dataclass(frozen=True)
class InstrumentMeta:
    symbol: str
    pip_size: float
    price_precision: int
    min_units: int
    max_spread: float
    max_quote_age_seconds: int = 30


INSTRUMENTS = {
    "EUR_USD": InstrumentMeta(
        symbol="EUR_USD",
        pip_size=0.0001,
        price_precision=5,
        min_units=1,
        max_spread=0.0005,
        max_quote_age_seconds=30,
    ),
    "GBP_USD": InstrumentMeta(
        symbol="GBP_USD",
        pip_size=0.0001,
        price_precision=5,
        min_units=1,
        max_spread=0.0007,
        max_quote_age_seconds=30,
    ),
    "USD_JPY": InstrumentMeta(
        symbol="USD_JPY",
        pip_size=0.01,
        price_precision=3,
        min_units=1,
        max_spread=0.05,
    ),
    "XAU_USD": InstrumentMeta(
        symbol="XAU_USD",
        pip_size=0.1,
        price_precision=3,
        min_units=1,
        max_spread=1.5,
    ),
}


def get_instrument_meta(symbol: str) -> InstrumentMeta:
    if symbol not in INSTRUMENTS:
        raise ValueError(f"No instrument metadata configured for {symbol}")

    return INSTRUMENTS[symbol]
