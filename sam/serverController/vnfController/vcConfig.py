#!/usr/bin/python
# -*- coding: UTF-8 -*-


class VCConfig:
    MAX_VIO_NUM = 65536 # max num of XX in virtioXX.
    MAX_CPU_NUM = 10 # max num of CPU in each server; TODO: may be replaced by server.CPUNum in the future.    

    DOCKER_TCP_PORT = 5982  # maybe unsafe

    DPDKINFO_BUF = 65535  # used for element DPDKInfo

    DEBUG = False  # if you set debug=True, the container will not be removed even if the app is terminated.
                  # !!!please run docker rm XXX to free resources of the container.!!!

    DEFAULT_FASTCLICK = True

    USING_PRECONFIG = True  # whether to use the pre-config firewall rules 
    PRECONFIG_PATH = '/home/server0/HaoChen/rule/100Acls'

    FWD_IMAGE_DPDK = 'dpdk-app-testpmd'
    FWD_APP_DPDK = './x86_64-native-linuxapp-gcc/app/testpmd'

    FWD_IMAGE_CLICK = 'fastclick-vnf'
    #FWD_IMAGE_CLICK = 'fastclick-vnf/disable-batch' 
    FWD_APP_CLICK = './click-conf/fwd.click'

    FW_IMAGE_CLICK = 'fastclick-vnf'
    #FW_IMAGE_CLICK = 'fastclick-vnf/disable-batch'
    FW_APP_CLICK = './click-conf/statelessFW.click'
    FW_RULE_DIR = '/rule'
    FW_RULE_PATH = '/rule/statelessFW'

    LB_IMAGE_CLICK = 'fastclick-vnf'
    #LB_IMAGE_CLICK = 'fastclick-vnf'
    LB_APP_CLICK = './click-conf/lb.click'

    MON_IMAGE_CLICK = 'fastclick-vnf'
    #MON_IMAGE_CLICK = 'fastclick-vnf/disable-batch'
    MON_APP_CLICK = './click-conf/monitor.click'
    MON_TCP_PORT = 8888  # maybe unsafe

    NAT_IMAGE_CLICK = 'fastclick-vnf'
    #NAT_IMAGE_CLICK = 'fastclick-vnf/disable-batch'
    NAT_APP_CLICK = './click-conf/nat.click'

    VPN_IMAGE_CLICK = 'fastclick-vnf'
    #VPN_IMAGE_CLICK = 'fastclick-vnf/disable-batch'
    VPN_APP_CLICK = './click-conf/vpn.click'

    NOT_AVAI_CPU = [0]  # used for bess

vcConfig = VCConfig()
