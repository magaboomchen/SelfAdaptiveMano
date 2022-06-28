# SelfAdaptiveMano

SelfAdaptiveMano (SAM) is a NFV Management and Orchestration Platform based on docker API, BESS and P4 Switches.

More information can be obtained in doc folder.

# Environment

Python2.7

Ubuntu 16.04 LTS / 18.04 LTS

# Installation
please read INSTALL.md

# For Yangpu Li's Information
## TODO list
* add interference algorithm (you may need to implement some other algorithm for comparison)
* add interference model into sam/orchestration/algorithms/base/performanceModel.py
    * add function: loadInterferenceModel(self, filepathToModel)
    * add function: getThroughput(self, serverArchitecture, targetNFType, competitorsList)
* implement simulator
    * embed performanceModel into simulator
    * export Throughput of each sfc to files
    * you can analyse the files and draw figures for your essay
* implement test for your algorithm in sam/orchestration/algorithms/interferenceAware/test
    * setup 
        * OSFCAdder()
        * prepare some problem instances
            * DCNInfoBaseMaintainer(): topology, server set
            * RequestBatchList: user's sfc requests
    * Call OSFCAdder.genABatchOfRequestAndAddSFCICmds() to generate ADD_SFCI_CMD
        * genABatchOfRequestAndAddSFCICmds will call interferenceAware() to calculate the mapping results
    * Save these cmds into files.
    * Send these cmds to simulator, simulator needs to simulate all metrics such as Throughtput.
    * Simulator save all results to files.
    * Draw figures.

# Development Mode
Inspired by github-flow, we don't need a dev branch.

You can create a new branch to develop a module in your charge.

As long as you test your modules, you can merge your branch into master.

# P4 development Information

Please read files in "/doc/SoftwareRequirements/", "/doc/SoftwareDesign/" (Ignore the TODO sections)

Our architecture design is illustrated in Architecture-P4.pptx

We need to give a design of P4 controller according to our requirements written in Architecture-P4.pptx.

We need to discuss together and then work it out.

# BUG LIST

vnfcontroller
* (not sure) it will get stuck when delete vnfi if vnfi has existed
* can't support multi-core click (maybe the problem of sff? fastclick use RSS to enable multi-core)

sffController
* vnf can't use multi-core, increase queue number in PMDPort(RSS)
* sfciID can't larger than 255 because update() module rewrite 1 byte from vnfID.
To tackle this bug, please refactor Update() module in bess and refactor sffController.
In details, add "value_maks" arg to Update() to only update vnfID in SFF. 

integration
* None

ryu
* _del_flow() needs add out_port and out_group to make sure the correctness. Refactor all api reference by other module.

# TODO LIST

Readme.md
* add rabbitmq setting

<!-- Base
* add routing/addressing scheme name to sfci's attributes -->

Dashboard
<!-- * give requirements -->
* user can add new routing scheme, stores it to database, sends it to control layer's module
* select routing/addressing scheme
* validate SFCIID selection
* add _initRoutingSchemeTable() and other functions in sam\dashboard\dashboardInfoBaseMaintainer.py

Dispatcher
* Sync dib into mysql periodically

Orchestrator
* UFRR mapping: check vnfi in vnfiSequence, delete duplicate vnfi in same server
* UFRR mapping and E2E-P: measure vnf max latency and update function getLatencyOfVNF in performanceModel.py

Measurer
* add self.sendGetSFCIStateCmd()

Adaptive
* give a design

SFFController
* (optional) add getSFCIStatus
* add icmp reply function (ipv4 and ipv6)
* add multi-queue to PMDPORT to support multi-core vnf.
A practical design:
    wm2 -> RoundRobin() -> QueueIncs;
    QueueOut -> merge -> update();
Remeber set queue number in PMDPort()

ClassifierController
* None

vnfController
* numa node support: numa cpu core and mem allocation
* independent dpdk apps: set different --file-prefix for differenct vnfi
* test chain deployment in one server
* scalability: divide into server/client mode. distribute the vnfiAdder agent to different servers
* Bugs: In addVNFI(), client.close() fails in the last line of code. I recommand store client in a dib, may be could save TCP connection time!

NetworkController
* P4 NF
* add icmp reply function (ipv4 and ipv6)
* add SFF rules (ipv4 and ipv6)
* add NF rules (ipv4 and ipv6)

Database Agent
* add database agent to orchestrator, measurer, dashboard, adaptive

Regulator
* design CMD_TYPE_FAILURE_ABNORMAL_RESUME

# FEATURE REQUEST LIST
