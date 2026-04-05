uint8 NO_CONTACT=0
uint8 FIRST_CONTACT=1
uint8 STABLE_CONTACT=2
uint8 CONTACT_LOST=3

std_msgs/Header header
uint8 contact_state
bool landing_completed
bool landing_failed
string reason
