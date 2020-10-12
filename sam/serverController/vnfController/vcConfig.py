#!/usr/bin/python
# -*- coding: UTF-8 -*-

class VCConfig:
    MAX_VIO_NUM = 65536 # max num of XX in virtioXX.
    MAX_CPU_NUM = 12 # max num of CPU in each server; TODO: may be replaced by server.CPUNum in the future.    
    
    DOCKER_TCP_PORT = 5982  # maybe unsafe

    DEBUG = True  # if you set debug=True, the container will not be removed even if the app is terminated.
                  # !!!please run docker rm XXX to free resources of the container.!!!

    DEFAULT_FASTCLICK = True

    FWD_IMAGE_DPDK = 'dpdk-app-testpmd'
    FWD_APP_DPDK = './x86_64-native-linuxapp-gcc/app/testpmd'

    FWD_IMAGE_CLICK = 'fastclick'
    FWD_APP_CLICK = './test-dpdk.click'

    FW_IMAGE_CLICK = 'test-click-fw'
    FW_APP_CLICK = './click-conf/testFW.click'
    FW_RULE_DIR = '/rule'
    FW_RULE_PATH = '/rule/statelessFW'

vcConfig = VCConfig()
