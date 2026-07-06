# Manual E2E Validation

Use this checklist for manual validation only. Automated safe tests must not call Telegram, OANDA, or live brokers.

## 1. Pre-flight Checklist

- Confirm current git commit:
  - `git rev-parse --short HEAD`
- Confirm safe suite passes:
  - `python3 tests/run_all_tests.py`
- Confirm OANDA integration remains opt-in:
  - Safe run should deselect integration tests.
- Confirm `.env` values needed for manual Telegram/OANDA checks:
  - `TELEGRAM_BOT_TOKEN`
  - `TELEGRAM_CHAT_ID`
  - `TELEGRAM_API_ID`
  - `TELEGRAM_API_HASH`
  - `TELEGRAM_PHONE`
  - `OANDA_ENV=practice`
  - `ALLOW_LIVE_TRADING=false`
  - `BOT_KILL_SWITCH=false` for paper/manual listener validation
- Confirm live trading is disabled:
  - `ALLOW_LIVE_TRADING=false`
- Confirm paper mode is used for E2E validation:
  - Use `PaperBroker` or paper pipeline tests.
- Confirm kill switch behavior before any live/practice execution test:
  - `BOT_KILL_SWITCH=true` must block execution.

## 2. Manual Telegram Test

1. Start the bot listener in a terminal:
   - `python listen_telegram_bot.py`
2. Send a sample message to the configured Telegram chat:
   - `BUY EURUSD @ 1.1000 SL 1.0950 TP 1.1100`
3. Confirm raw signal storage:
   - Inspect `data/signals.json`.
   - Expected: source/chat/message metadata and raw text are present.
4. Confirm parsed signal:
   - Expected: `parse_status` is `VALID_SIGNAL`.
   - Expected parsed fields: `symbol=EUR_USD`, `action=buy`, `stop_loss`, `take_profits`.
5. Confirm decision path using safe pipeline tests or a paper-only runner:
   - Expected: `TradeCandidate` is created.
   - Expected: no direct execution from ingestion or parser.
6. Confirm paper execution only:
   - Use `PaperBroker` or `tests/e2e/test_full_paper_pipeline.py`.
   - Expected: `ExecutionResult.status=FILLED`, `broker=paper`.
7. Confirm ledger trace:
   - Inspect the E2E temp ledger when running tests, or inspect configured ledger files.
   - Expected stages: parsing, decision, ensemble, ml signal quality, portfolio risk, capital allocation, execution, learning.

## 3. Manual Historical Replay Test

1. Import Telegram history:
   - `python import_telegram_history.py`
2. Run a backtest or replay against stored signals:
   - Use the existing backtesting runner or `BacktestPipeline`.
3. Inspect channel score/profile:
   - Confirm Channel Intelligence profile updates when backtest results are explicitly fed.
4. Confirm no live trades:
   - No OANDA order ids should be created.
   - No `ORDER_SUBMITTED` live broker event should appear.
   - Safe replay should produce simulated results only.

## 4. Manual Safety Checks

- Kill switch:
  - Set `BOT_KILL_SWITCH=true`.
  - Attempt an execution path.
  - Expected: execution is blocked before broker order placement.
- Live mode disabled:
  - Keep `ALLOW_LIVE_TRADING=false`.
  - Any live broker environment execution should be blocked.
- OANDA integration:
  - OANDA tests are opt-in only with `--include-integration`.
  - Do not run integration tests during safe E2E validation.
- Paper broker:
  - `PaperBroker` must work without network access.
  - It should simulate price, order fill, open trades, trade lookup, and close.

## 5. Manual Ledger Trace Check

For automated E2E, inspect the temp ledger path created by pytest. For runtime JSON stores, inspect:

- `data/trade_events.json`
- `data/decision_events.json`
- `data/execution_state.json`

Expected safe E2E event sequence:

1. `parsing`
2. `decision`
3. `ensemble`
4. `ml_signal_quality`
5. `portfolio_risk`
6. `capital_allocation`
7. `execution`
8. `learning`

Each stage should have:

- input id
- output id where applicable
- reason
- payload
- timestamp/created_at

## 6. Pass/Fail Sign-off

| Check | Expected Result | Pass/Fail | Notes |
| --- | --- | --- | --- |
| Safe suite | `python3 tests/run_all_tests.py` passes |  |  |
| Integration deselection | OANDA integration deselected by default |  |  |
| Telegram raw storage | Raw message appears in signal store |  |  |
| Parser output | Valid signal parsed correctly |  |  |
| Paper execution | Paper `ExecutionResult` is filled |  |  |
| Ledger trace | All expected stages are present |  |  |
| Kill switch | Blocks execution |  |  |
| Live disabled | Blocks live order path |  |  |
| Historical replay | Valid signals simulated, commentary skipped |  |  |
| No live broker calls | No OANDA/live broker touched |  |  |
