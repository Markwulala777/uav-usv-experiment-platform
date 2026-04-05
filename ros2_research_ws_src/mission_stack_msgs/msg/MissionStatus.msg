uint8 SEARCH=0
uint8 APPROACH=1
uint8 ALIGN=2
uint8 SYNCHRONIZE=3
uint8 WINDOW_WAIT=4
uint8 TERMINAL_DESCENT=5
uint8 TOUCHDOWN=6
uint8 POST_LANDING=7
uint8 ABORT_GO_AROUND=8

std_msgs/Header header
uint8 phase
uint8 previous_phase
string transition_reason
