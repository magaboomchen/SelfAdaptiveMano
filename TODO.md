# TODO LIST

This list is only a part of TODO!
Please contace offline to get more TODOs!

Dashboard
* user can add new routing scheme, stores it to database, sends it to control layer's module
* select routing/addressing scheme
* validate SFCIID selection

Dispatcher
* None

Orchestrator
* UFRR mapping: check vnfi in vnfiSequence, delete duplicate vnfi in same server
* UFRR mapping and E2E-P: measure vnf max latency and update function getLatencyOfVNF in performanceModel.py

Measurer
* add self.sendGetSFCIStateCmd()

Regulator
* Add scaling ability
* design CMD_TYPE_FAILURE_ABNORMAL_RESUME

SFFController
* add getSFCIStatus
* add icmp reply function (ipv4 and ipv6)
* add multi-queue to PMDPORT to support multi-core vnf.
A practical design:
    wm2 -> RoundRobin() -> QueueIncs;
    QueueOut -> merge -> update();
Remeber set queue number in PMDPort()

ClassifierController
* None

vnfController
* (optinal) numa node support: numa cpu core and mem allocation
* independent dpdk apps: set different --file-prefix for differenct vnfi
* test chain deployment in one server
* (optinal) scalability: divide into server/client mode. distribute the vnfiAdder agent to different servers
* Bugs: In addVNFI(), client.close() fails in the last line of code. I recommand store client in a dib, may be could save TCP connection time!

NetworkController
* P4 NF
* add icmp reply function (ipv4 and ipv6)
* add SFF rules (ipv4 and ipv6)
* add NF rules (ipv4 and ipv6)

Database Agent
* None
