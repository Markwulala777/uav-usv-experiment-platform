# experiment_manager

Owns `/experiment/run_status` and `/experiment/events`, writes per-run metadata,
acts as the run-level event-log owner, and publishes `/experiment/scenario_profile`.

For scenario 1/2/3 chain validation, `experiment_manager` remains the owner of
the run directory and emits the metadata consumed by `frame_audit`,
`geometry_consistency`, and `summary_writer`. This supports the repository's
formal chain-validation entrypoint, and the resulting `summary.json`
distinguishes `mission_outcome` from `chain_validation_passed`.
