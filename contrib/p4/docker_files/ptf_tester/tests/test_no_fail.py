import ptf
from ptf.base_tests import BaseTest
from ptf import config
import ptf.testutils as testutils
from scapy.all import *
import re

TYPE_MYTUNNEL = 0x1212
TYPE_IPV4 = 0x0800


class MyTunnel(Packet):
    name="MyTunnel"
    fields_desc = [
        ShortField("pid", 0),
        ShortField("dst_id", 0)
    ]
    def mysummary(self):
        return self.sprintf("pid=%pid%, dst_id=%dst_id%")

class DataplaneBaseTest(BaseTest):
    def __init__(self):
        BaseTest.__init__(self)

    def setUp(self):
        self.dataplane = ptf.dataplane_instance
        self.dataplane.flush()
        if config["log_dir"] != None:
            filename = os.path.join(config["log_dir"], str(self)) + ".pcap"
            self.dataplane.start_pcap(filename)

    def tearDown(self):
        if config["log_dir"] != None:
            self.dataplane.stop_pcap()

class IPV4OneSwitchTest(DataplaneBaseTest):
    def __init__(self):
        DataplaneBaseTest.__init__(self)

    def runTest(self):
        #log_to_file("Staring first test")
        pkt = testutils.simple_tcp_packet(pktlen=100, ip_dst="192.168.1.2", ip_ttl=64, eth_dst="00:01:02:03:04:05", eth_src="00:01:02:03:04:05")
        pkt_expected = testutils.simple_tcp_packet(pktlen=100, ip_dst="192.168.1.2", ip_ttl=63, eth_dst="00:01:02:03:04:05", eth_src="00:01:02:03:04:05")
        try:
            testutils.send_packet(self, (0, 1), pkt)
        except Exception as e:
            print(e)
        
        
        testutils.verify_packet(self, pkt_expected, (1, 1))

class Ipv4TwoSwitchesTest(DataplaneBaseTest):
    def __init__(self):
        DataplaneBaseTest.__init__(self)

    def runTest(self):
        pkt = testutils.simple_tcp_packet(pktlen=100, ip_dst="192.168.1.4", ip_ttl=64, eth_dst="00:01:02:03:04:05", eth_src="00:01:02:03:04:05")
        pkt_expected = testutils.simple_tcp_packet(pktlen=100, ip_dst="192.168.1.4", ip_ttl=62, eth_dst="00:01:02:03:04:05", eth_src="00:01:02:03:04:05")

        testutils.send_packet(self, (0, 1), pkt)

        testutils.verify_packet(self, pkt_expected, (3,1))
# class MyTunnelPacketTest(DataplaneBaseTest):
#     def __init__(self):
#         DataplaneBaseTest.__init__(self)

#     def runTest(self):
#         #log_to_file("Starting second test")

#         bind_layers(Ether, MyTunnel, type=TYPE_MYTUNNEL)
#         bind_layers(MyTunnel, IP, pid=TYPE_IPV4)
#         pkt = Ether(dst="00:01:02:03:04:05", src="00:01:02:03:04:05")/MyTunnel()/IP(dst="192.168.1.2", ttl=64)

#         log_to_file("---Packet--- \n" + str(pkt.show))

#         pkt_expected = Ether(dst="00:01:02:03:04:05", src="00:01:02:03:04:05")/IP(dst="192.168.1.2", ttl=63)

#         testutils.send_packet(self, (0,1), pkt)

#         testutils.verify_packet(self, pkt_expected, (1, 1))


def log_to_file(msg):
    f = open("/app/app.log", "w")
    f.write(msg + "\n")
    f.close()

        
