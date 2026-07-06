# Production Readiness

This platform must not start live trading without explicit operational approval.

## Deployment Checklist

- Safe suite passes: `python3 tests/run_all_tests.py`
- Integration tests remain opt-in: `python3 tests/run_all_tests.py --include-integration`
- `BOT_KILL_SWITCH=true` blocks execution.
- Paper mode starts without live secrets.
- Live mode requires `ALLOW_LIVE_TRADING=true`.
- Live mode requires `LIVE_TRADING_APPROVED=true`.
- Live mode requires OANDA live secrets.
- Dry-run mode is used before live deployment.
- Backup artifact exists and restore validation passes.
- Monitoring and alert hooks are configured.
- Current git commit is recorded.

## Paper Soak Checklist

- Run paper pipeline for the planned soak window.
- Confirm no OANDA live order IDs are created.
- Inspect event ledger trace for every paper order.
- Confirm reconciliation reports no unexplained drift.
- Confirm channel and risk dashboards show expected state.

## Backup And Recovery

- Back up JSON state before deployment.
- Validate the backup artifact is non-empty.
- On restart, validate state files are readable JSON.
- If validation fails, keep live trading disabled.

## Rollback Procedure

- Set `BOT_KILL_SWITCH=true`.
- Stop listeners and execution workers.
- Restore the last validated state backup.
- Re-run safe tests.
- Restart in paper or dry-run mode only.
- Require fresh human approval before live mode.

## Incident Playbook

- Enable kill switch immediately.
- Record incident time, git commit, account id, broker, and affected symbol.
- Inspect event ledger trace from raw input through execution result.
- Inspect reconciliation status.
- Do not resume live trading until root cause and rollback status are reviewed.
