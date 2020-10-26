# SelfAdaptiveMano

SelfAdaptiveMano (SAM) is a NFV Management and Orchestration Platform based on docker API, BESS and P4 Switches.

More information can be obtained in doc folder.

# Environment

Python2.7

Ubuntu 16.04 LTS

# FYI

Please read files in "/doc/SoftwareRequirements/", "/doc/SoftwareDesign/" (Ignore the TODO sections)

Our architecture design is illustrated in Architecture-P4.pptx

Yuxuan Zhang needs to give a design of P4 controller according to our requirements written in Architecture-P4.pptx.

We need to discuss together and then work it out.

# BUG LIST

messageAgent send message failed when idle time is too long.

# TODO LIST

test orchestrator

Modify NetworkController's add SFCI cmd function. (add match filed with inport into IPv4_CLASSIFIER_TABLE); add delete SFC cmd function (delete the match entry in IPv4_CLASSIFIER_TABLE)

Add zone to all controller

Modify mediator: add zone

Simulator as Zone_Simulation; Mininet as Zone_Mininet;

Refactor datapath: encoding format error. "VNFID+SFCID+PATHID"

Add getSFCIStatus in sffController; measurer: add self.sendGetSFCIStateCmd()

Add sfci deleter in ufrr (optional)

# FEATURE REQUEST LIST
