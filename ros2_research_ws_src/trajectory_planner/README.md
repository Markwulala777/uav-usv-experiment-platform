# trajectory_planner

Owns `/planner/reference_trajectory` and `/planner/status`.

The current implementation is a facade node that keeps the external planner
contract stable while selecting a backend through `planner_backend`.
