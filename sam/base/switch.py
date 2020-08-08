
SWITCH_TYPE_P4 = "SWITCH_TYPE_P4"
SWITCH_TYPE_OPENFLOW = "SWITCH_TYPE_OPENFLOW"

class Switch(object):
    def __init__(self, switchID, switchType):
        self.switchID = switchID
        self.switchType = switchType