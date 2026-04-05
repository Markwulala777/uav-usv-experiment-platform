# platform_interface

Owns the public platform-side research interface:

- `/platform/state`
- `/platform/landing_zone_state`

Legacy compatibility publications are still emitted on:

- `/deck/state_truth`
- `/deck/landing_zone_state`

It does not permanently own `/uav/*`. The transitional `platform_uav_truth_provider`
node exists only to keep the current baseline runnable while a dedicated
UAV-state package is not yet extracted.
