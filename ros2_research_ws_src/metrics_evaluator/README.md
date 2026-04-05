# metrics_evaluator

Consumes public run topics and `/experiment/events` to compute summaries.

This package now owns the chain-validation reporting helpers used by the
repository's formal validation entrypoint, `run_chain_validation.sh`, across
scenario 1/2/3:

- `summary_writer`
- `frame_audit`
- `geometry_consistency`

The resulting run directory artifacts include:

- `summary.json`
- `frame_audit_report.json`
- `geometry_consistency_report.json`

The migrated frame audit remains in this package as a debug-oriented helper
node, while `summary_writer` is the authoritative source for
`chain_validation_passed`.
