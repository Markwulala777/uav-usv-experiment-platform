uint8 CONTINUE=0
uint8 HOLD=1
uint8 REPLAN=2
uint8 GO_AROUND=3
uint8 ABORT=4

std_msgs/Header header
uint8 advisory
string[] reason_codes
