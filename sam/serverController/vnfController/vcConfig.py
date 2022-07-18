#!/usr/bin/python
# -*- coding: UTF-8 -*-


from sam.serverController.sffController.sfcConfig import CHAIN_TYPE_NSHOVERETH, CHAIN_TYPE_UFRR, DEFAULT_CHAIN_TYPE


class VCConfig:
    MAX_VIO_NUM = 65536 # max num of XX in virtioXX.
    # MAX_CPU_NUM = 10 # max num of CPU in each server; TODO: may be replaced by server.CPUNum in the future.    

    DOCKER_TCP_PORT = 5982  # maybe unsafe

    DPDKINFO_BUF = 65535  # used for element DPDKInfo

    DEBUG = False  # if you set debug=True, the container will not be removed even if the app is terminated.
                  # !!!please run docker rm XXX to free resources of the container.!!!

    NOT_AVAI_CPU = [0]  # used for bess

    DEFAULT_FASTCLICK = True

    FWD_IMAGE_DPDK = 'dpdk-app-testpmd'
    FWD_APP_DPDK = './x86_64-native-linuxapp-gcc/app/testpmd'

    if DEFAULT_CHAIN_TYPE == CHAIN_TYPE_UFRR:
        CLICK_PATH = "./fastclick/bin/click"

        FWD_IMAGE_CLICK = 'fastclick-vnf'
        FWD_APP_CLICK = './click-conf/fwd.click'

        USING_PRECONFIG = True  # whether to use the pre-config firewall rules 
        PRECONFIG_PATH = '/home/server0/HaoChen/rule/100Acls'

        FW_IMAGE_CLICK = 'fastclick-vnf'
        FW_APP_CLICK = './click-conf/statelessFW.click'
        FW_RULE_DIR = '/rule'
        FW_IPV4_RULE_PATH = '/rule/statelessFW'

        LB_IMAGE_CLICK = 'fastclick-vnf'
        LB_APP_CLICK = './click-conf/lb.click'

        MON_IMAGE_CLICK = 'fastclick-vnf'
        MON_APP_CLICK = './click-conf/monitor.click'
        MON_TCP_PORT = 8888  # maybe unsafe

        NAT_IMAGE_CLICK = 'fastclick-vnf'
        NAT_APP_CLICK = './click-conf/nat.click'

        VPN_IMAGE_CLICK = 'fastclick-vnf'
        VPN_APP_CLICK = './click-conf/vpn.click'

    elif DEFAULT_CHAIN_TYPE == CHAIN_TYPE_NSHOVERETH:
        CLICK_PATH = "./bin/click"

        FWD_IMAGE_CLICK = 'samfastclick:v1'
        FWD_APP_CLICK = './conf/sam/fwd.click'

        USING_PRECONFIG = False  # whether to use the pre-config firewall rules 
        PRECONFIG_PATH = '/home/smith/Projects/fastclick/conf/sam/'

        FW_IMAGE_CLICK = 'samfastclick:v1'
        FW_APP_CLICK = './conf/sam/statelessFW.click'
        FW_RULE_DIR = '/home/smith/Projects/fastclick/conf/sam'
        FW_IPV4_RULE_PATH = '/home/smith/Projects/fastclick/conf/sam/statelessFWRules'
        FW_IPV6_RULE_PATH = '/home/smith/Projects/fastclick/conf/sam/statelessFWIPv6Rules'
        FW_ROCEV1_RULE_PATH = '/home/smith/Projects/fastclick/conf/sam/statelessFWRoceV1Rules'

        # TODO: implement this vnf
        # LB_IMAGE_CLICK = 'samfastclick:v1'
        # LB_APP_CLICK = './conf/sam/lb.click'

        MON_IMAGE_CLICK = 'samfastclick:v1'
        MON_APP_CLICK = './conf/sam/monitor.click'
        MON_TCP_PORT = 7777  # maybe unsafe

        RATELIMITER_IMAGE_CLICK = 'samfastclick:v1'
        RATELIMITER_APP_CLICK = './conf/sam/rateLimiter.click'

        # TODO: implement this vnf
        # NAT_IMAGE_CLICK = 'samfastclick:v1'
        # NAT_APP_CLICK = './conf/sam/nat.click'

        # TODO: implement this vnf
        # VPN_IMAGE_CLICK = 'samfastclick:v1'
        # VPN_APP_CLICK = './conf/sam/vpn.click'
    else:
        raise ValueError("Unknown chain type.")

vcConfig = VCConfig()
