import os
import ptf
from ptf.base_tests import BaseTest
from ptf import config
import ptf.testutils as testutils
from ptf.testutils import testtimeout


class DataplaneBaseTest(BaseTest):
    def __init__(self):
        BaseTest.__init__(self)

        self.network_config = None  # Set by test if required

    @staticmethod
    def get_network_config():
        return "/home/p4/bf_benchexec/benchexec/contrib/p4_files/docker_files/ptf_tester/p4_tutorial_tests/network_configs/4_nodes_3_switch.json"

    def setUp(self):
        self.dataplane = ptf.dataplane_instance
        self.dataplane.flush()
        if config["log_dir"] is not None:
            filename = os.path.join(config["log_dir"], str(self)) + ".pcap"
            self.dataplane.start_pcap(filename)

    def tearDown(self):
        if config["log_dir"] is not None:
            self.dataplane.stop_pcap()


class Node1ToNode2(DataplaneBaseTest):
    def __init__(self):
        DataplaneBaseTest.__init__(self)

    def runTest(self):
        pkt = testutils.simple_tcp_packet(
            pktlen=100,
            ip_dst="10.0.2.2",
            ip_ttl=64,
            eth_dst="00:01:02:03:04:05",
            eth_src="00:01:02:03:04:05",
        )
        pkt_expected = testutils.simple_tcp_packet(
            pktlen=100,
            ip_dst="10.0.2.2",
            ip_ttl=64,
            eth_dst="00:01:02:03:04:05",
            eth_src="00:01:02:03:04:05",
        )
        try:
            testutils.send_packet(self, (0, 0), pkt)
        except Exception as e:
            print(e)

        testutils.verify_packet(self, pkt_expected, (1, 0))


class Node2ToNode1(DataplaneBaseTest):
    def __init__(self):
        DataplaneBaseTest.__init__(self)

    def runTest(self):
        pkt = testutils.simple_tcp_packet(
            pktlen=100,
            ip_dst="10.0.1.1",
            ip_ttl=64,
            eth_dst="00:01:02:03:04:05",
            eth_src="00:01:02:03:04:05",
        )
        pkt_expected = testutils.simple_tcp_packet(
            pktlen=100,
            ip_dst="10.0.1.1",
            ip_ttl=64,
            eth_dst="00:01:02:03:04:05",
            eth_src="00:01:02:03:04:05",
        )
        try:
            testutils.send_packet(self, (1, 0), pkt)
        except Exception as e:
            print(e)

        testutils.verify_packet(self, pkt_expected, (0, 0))


class Node1ToNode3(DataplaneBaseTest):
    def __init__(self):
        DataplaneBaseTest.__init__(self)

    def runTest(self):
        pkt = testutils.simple_tcp_packet(
            pktlen=100,
            ip_dst="10.0.3.3",
            ip_ttl=64,
            eth_dst="00:01:02:03:04:05",
            eth_src="00:01:02:03:04:05",
        )
        pkt_expected = testutils.simple_tcp_packet(
            pktlen=100,
            ip_dst="10.0.3.3",
            ip_ttl=64,
            eth_dst="00:01:02:03:04:05",
            eth_src="00:01:02:03:04:05",
        )
        try:
            testutils.send_packet(self, (0, 0), pkt)
        except Exception as e:
            print(e)

        testutils.verify_packet(self, pkt_expected, (2, 0))


class Node3ToNode1(DataplaneBaseTest):
    def __init__(self):
        DataplaneBaseTest.__init__(self)

    def runTest(self):
        pkt = testutils.simple_tcp_packet(
            pktlen=100,
            ip_dst="10.0.1.1",
            ip_ttl=64,
            eth_dst="00:01:02:03:04:05",
            eth_src="00:01:02:03:04:05",
        )
        pkt_expected = testutils.simple_tcp_packet(
            pktlen=100,
            ip_dst="10.0.1.1",
            ip_ttl=64,
            eth_dst="00:01:02:03:04:05",
            eth_src="00:01:02:03:04:05",
        )
        try:
            testutils.send_packet(self, (2, 0), pkt)
        except Exception as e:
            print(e)

        testutils.verify_packet(self, pkt_expected, (0, 0))


class Node1ToNode4(DataplaneBaseTest):
    def __init__(self):
        DataplaneBaseTest.__init__(self)

    def runTest(self):
        pkt = testutils.simple_tcp_packet(
            pktlen=100,
            ip_dst="10.0.4.4",
            ip_ttl=64,
            eth_dst="00:01:02:03:04:05",
            eth_src="00:01:02:03:04:05",
        )
        pkt_expected = testutils.simple_tcp_packet(
            pktlen=100,
            ip_dst="10.0.4.4",
            ip_ttl=64,
            eth_dst="00:01:02:03:04:05",
            eth_src="00:01:02:03:04:05",
        )
        try:
            testutils.send_packet(self, (0, 0), pkt)
        except Exception as e:
            print(e)

        testutils.verify_packet(self, pkt_expected, (3, 0))


class Node4ToNode1(DataplaneBaseTest):
    def __init__(self):
        DataplaneBaseTest.__init__(self)

    def runTest(self):
        pkt = testutils.simple_tcp_packet(
            pktlen=100,
            ip_dst="10.0.1.1",
            ip_ttl=64,
            eth_dst="00:01:02:03:04:05",
            eth_src="00:01:02:03:04:05",
        )
        pkt_expected = testutils.simple_tcp_packet(
            pktlen=100,
            ip_dst="10.0.1.1",
            ip_ttl=64,
            eth_dst="00:01:02:03:04:05",
            eth_src="00:01:02:03:04:05",
        )
        try:
            testutils.send_packet(self, (3, 0), pkt)
        except Exception as e:
            print(e)

        testutils.verify_packet(self, pkt_expected, (0, 0))


class BigPackageTest(DataplaneBaseTest):
    def __init__(self):
        DataplaneBaseTest.__init__(self)

    def runTest(self):
        pkt = testutils.simple_tcp_packet(
            pktlen=1000,
            ip_dst="10.0.1.1",
            ip_ttl=64,
            eth_dst="00:01:02:03:04:05",
            eth_src="00:01:02:03:04:05",
        )
        pkt_expected = testutils.simple_tcp_packet(
            pktlen=1000,
            ip_dst="10.0.1.1",
            ip_ttl=64,
            eth_dst="00:01:02:03:04:05",
            eth_src="00:01:02:03:04:05",
        )
        try:
            testutils.send_packet(self, (3, 0), pkt)
        except Exception as e:
            print(e)

        testutils.verify_packet(self, pkt_expected, (0, 0))
