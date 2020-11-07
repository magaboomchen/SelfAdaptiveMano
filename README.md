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

# TODO LIST

Add zone to all controller
* Simulator as SIMULATOR_ZONE
* Mininet as MININET_ZONE
* Turbonet as TURBONET_ZONE

Orchestrator
* add ADD_SFC_REQUEST, ADD_SFCI_REQUEST, DEL_SFCI_REQUEST, DEL_SFC_REQUEST

Measurer
* add self.sendGetSFCIStateCmd()

Adaptive
* give a design

Request Processor
* give a design

SFFController
* add getSFCIStatus

NetworkController
* (Optional) ryuCommandAgentUFRR/ryuCommandAgentNotVia: add CMD_TYPE_DEL_SFC handler (delete route2Classifier)

# FEATURE REQUEST LIST
