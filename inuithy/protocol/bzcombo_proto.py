""" BLE protocol definition
 @author Zex Li <top_zlynch@yahoo.com>
 @reference BLE_Control_Protocol.pdf
"""
from inuithy.common.predef import string_write
#, MessageType,\
#TrafficType, T_SRC, T_DEST, T_CHANNEL, T_MSG_TYPE, T_TRAFFIC_TYPE,\
#T_GENID, T_ADDR, T_TIME, T_NODE, T_PANID
from inuithy.protocol.ble_proto import BleProtocol
from inuithy.protocol.zigbee_proto import ZigbeeProtocol
from inuithy.protocol.protocol import Protocol

class BzProtocol(Protocol):
    """BLE-Zigbee combo control protocol
    """
    # Sub protocols
    #TODO correct parser
    ble = BleProtocol
    zbee = ZigbeeProtocol

    @staticmethod
    def joingrp(params=None):
        """Join group command builder"""
        return PROTO.ble.joingrp(params)

    @staticmethod
    def leavegrp(params=None):
        """Leave group command builder"""
        return PROTO.ble.leavegrp(params)

    @staticmethod
    def lighton(params=None):
        """Light on command builder"""
        return PROTO.ble.lighton(params)

    @staticmethod
    def lightoff(params=None):
        """Light off command builder"""
        return PROTO.ble.lightoff(params)

    @staticmethod
    def setaddr(params=None):
        """Set address command builder"""
        return PROTO.ble.setaddr(params)

    @staticmethod
    def getaddr(params=None):
        """Get address command builder"""
        return PROTO.ble.getaddr(params)

    @staticmethod
    def joinnw(params=None):
        """Join network command builder"""
        return PROTO.zbee.joinnw(params)

    @staticmethod
    def writeattribute2(params=None):
        """Write attribute command builder"""
        return PROTO.zbee.writeattribute2(params)

    @staticmethod
    def getfwver(params=None):
        return PROTO.ble.getfwver()

    @staticmethod
    def parse_rbuf(data, node):
        """Parse recieved data
        @data Serial command sent
        @node Node object
        @return Dict report for sending to controller
        """
        #TODO correct parser
        return PROTO.ble.parse_rbuf(data, node)

    @staticmethod
    def parse_wbuf(data, node, request):
        """Parse written buffer
        @data Serial command sent
        @node Node object
        @request Dict request information
        @return Dict report for sending to controller
        """
        #TODO correct parser
        return PROTO.ble.parse_wbuf(data, node, request)

PROTO = BzProtocol

