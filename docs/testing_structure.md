# Testing Structure

The test suite is organized by scope and module ownership.

## Layout

- `tests/contract/`
  - Contract schema, validation, and immutability tests.
- `tests/unit/`
  - Fast, isolated module tests.
  - Subfolders mirror production ownership:
    - `backtesting/`
    - `capital/`
    - `controls/`
    - `decision/`
    - `events/`
    - `execution/`
    - `ingestion/`
    - `learning/`
    - `parsing/`
    - `reconciliation/`
    - `routing/`
    - `storage/`
- `tests/pipeline/`
  - Multi-stage in-process pipeline tests with fakes and temp stores.
- `tests/e2e/`
  - Full safe paper-only end-to-end tests.
- `tests/integration/`
  - External broker/API tests only.

## Run Safe Tests

```bash
python3 tests/run_all_tests.py
```

Default safe tests include:

- `tests/contract`
- `tests/unit`
- `tests/pipeline`
- `tests/e2e`

The default suite excludes integration tests and must not call real brokers, Telegram, OANDA, or any external API.

## Run Module-Specific Tests

Examples:

```bash
python3 -m pytest -s tests/unit/execution
python3 -m pytest -s tests/unit/parsing
python3 -m pytest -s tests/unit/ingestion/telegram
python3 -m pytest -s tests/pipeline
python3 -m pytest -s tests/e2e
```

## Run Integration Tests

Integration tests are opt-in:

```bash
python3 tests/run_all_tests.py --include-integration
```

Real OANDA tests also require:

```bash
RUN_OANDA_INTEGRATION=true
```

Do not put real broker/API tests in the default safe suite. Any test that calls an external API must live under `tests/integration/` and be marked:

```python
@pytest.mark.integration
```

## Paper Broker Replacement

Default test coverage for open/fill/close trade behavior uses `PaperBroker` or fakes. Real OANDA tests are only for explicit external integration validation.
