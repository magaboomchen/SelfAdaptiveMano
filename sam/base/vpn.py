#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
This file defines the format of rules used for vpn. 
In vnfi, VPNTuple is maintained in vnfi.config['VPN']
This is a IPSec VPN which use AES algorithm to encrpt payload after ip layer

Usually, user needs a pair of VPN as the end point of tunnel
VPN1 <---> VPN2
User needs to provides config for both two VPN, here is an example:
VPN1:
    VPN_TunnelSrcIP = "3.3.3.3/32"
    VPN_TunnelDstIP = "4.4.4.4"
    VPN_EncryptKey = "11FF0183A9471ABE01FFFA04103BB102"
    VPN_AuthKey = "11FF0183A9471ABE01FFFA04103BB202"

VPN2:
    VPN_TunnelSrcIP = "4.4.4.4/32"
    VPN_TunnelDstIP = "3.3.3.3"
    VPN_EncryptKey = "11FF0183A9471ABE01FFFA04103BB102"
    VPN_AuthKey = "11FF0183A9471ABE01FFFA04103BB202"

Cautions:
    These two VPNs' configs are relative, so be careful to set them.
'''

class VPNTuple(object):
    def __init__(self, tunnelSrcIP, tunnelDstIP, encryptKey, authKey): 
        self.tunnelSrcIP = tunnelSrcIP
        self.tunnelDstIP = tunnelDstIP
        self.encryptKey = encryptKey
        self.authKey = authKey
