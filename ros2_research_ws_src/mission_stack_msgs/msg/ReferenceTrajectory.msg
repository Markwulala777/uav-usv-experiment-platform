std_msgs/Header header
# phase is a planning-context snapshot, not the authoritative mission phase.
uint8 phase
string planner_backend
mission_stack_msgs/ReferenceTrajectoryPoint[] trajectory_points
# terminal_target may describe a single terminal point or a terminal-set summary.
mission_stack_msgs/TerminalTargetSpec terminal_target
bool feasible
bool replan_requested
string replan_reason
string diagnostic_code
float32 solve_time_ms
builtin_interfaces/Duration valid_horizon
uint32 sequence_id
string source
