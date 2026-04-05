# controller_interface

Owns the active control-reference path and the only PX4/offboard output.

`reference_mux` selects the source, `tracking_controller` emits `ControllerCommand`,
and `px4_offboard_bridge` is the only ENU->NED conversion point. `reference_mux`
is also the single active-reference owner for planner versus guidance.
