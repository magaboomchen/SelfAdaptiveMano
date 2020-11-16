#!/usr/bin/python
# -*- coding: UTF-8 -*-

class VCConfig:
    MAX_VIO_NUM = 65536 # max num of XX in virtioXX.
    MAX_CPU_NUM = 12 # max num of CPU in each server; TODO: may be replaced by server.CPUNum in the future.    
    
    DOCKER_TCP_PORT = 5982  # maybe unsafe

    DEBUG = True  # if you set debug=True, the container will not be removed even if the app is terminated.
                  # !!!please run docker rm XXX to free resources of the container.!!!

    DEFAULT_FASTCLICK = True

    USING_PRECONFIG = True  # whether to use the pre-config firewall rules 
    PRECONFIG_PATH = '/home/server0/HaoChen/rule'

    FWD_IMAGE_DPDK = 'dpdk-app-testpmd'
    FWD_APP_DPDK = './x86_64-native-linuxapp-gcc/app/testpmd'

    FWD_IMAGE_CLICK = 'release/fastclick-vnf'
    FWD_APP_CLICK = './click-conf/fwd.click'

    FW_IMAGE_CLICK = 'release/fastclick-vnf'
    FW_APP_CLICK = './click-conf/statelessFW.click'
    FW_RULE_DIR = '/rule'
    FW_RULE_PATH = '/rule/statelessFW'

    LB_IMAGE_CLICK = 'release/fastclick-vnf'
    LB_APP_CLICK = './click-conf/lb.click'

    MON_IMAGE_CLICK = 'release/fastclick-vnf'
    MON_APP_CLICK = './click-conf/monitor.click'
    MON_TCP_PORT = 8888  # maybe unsafe

        

vcConfig = VCConfig()
