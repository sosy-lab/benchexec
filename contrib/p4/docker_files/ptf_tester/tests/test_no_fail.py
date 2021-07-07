# SPDX-FileCopyrightText: 2020-2021 CASTOR Software Research Centre
# <https://www.castor.kth.se/>
# SPDX-FileCopyrightText: 2020-2021 Johan Paulsson

# SPDX-License-Identifier: Apache-2.0

import os
import ptf
from ptf.base_tests import BaseTest
from ptf import config
import ptf.testutils as testutils

TYPE_IPV4 = 0x0800


class DataplaneBaseTest(BaseTest):
    def __init__(self):
        BaseTest.__init__(self)

    def setUp(self):
        self.dataplane = ptf.dataplane_instance
        self.dataplane.flush()
        if config["log_dir"] is not None:
            filename = os.path.join(config["log_dir"], str(self)) + ".pcap"
            self.dataplane.start_pcap(filename)

    def tearDown(self):
        if config["log_dir"] is not None:
            self.dataplane.stop_pcap()


class IPV4OneSwitchTest(DataplaneBaseTest):
    def __init__(self):
        DataplaneBaseTest.__init__(self)

    def runTest(self):
        pkt = testutils.simple_tcp_packet(
            pktlen=100,
            ip_dst="192.168.1.2",
            ip_ttl=64,
            eth_dst="00:01:02:03:04:05",
            eth_src="00:01:02:03:04:05",
        )
        pkt_expected = testutils.simple_tcp_packet(
            pktlen=100,
            ip_dst="192.168.1.2",
            ip_ttl=63,
            eth_dst="00:01:02:03:04:05",
            eth_src="00:01:02:03:04:05",
        )
        try:
            testutils.send_packet(self, (0, 0), pkt)
        except Exception as e:
            print(e)

        testutils.verify_packet(self, pkt_expected, (1, 0))


class IPV4OneSwitchTest2(DataplaneBaseTest):
    def __init__(self):
        DataplaneBaseTest.__init__(self)

    def runTest(self):
        pkt = testutils.simple_tcp_packet(
            pktlen=100,
            ip_dst="192.168.1.3",
            ip_ttl=64,
            eth_dst="00:01:02:03:04:05",
            eth_src="00:01:02:03:04:05",
        )
        pkt_expected = testutils.simple_tcp_packet(
            pktlen=100,
            ip_dst="192.168.1.3",
            ip_ttl=63,
            eth_dst="00:01:02:03:04:05",
            eth_src="00:01:02:03:04:05",
        )
        try:
            testutils.send_packet(self, (1, 1), pkt)
        except Exception as e:
            print(e)

        testutils.verify_packet(self, pkt_expected, (2, 0))


class Ipv4TwoSwitchesTest(DataplaneBaseTest):
    def __init__(self):
        DataplaneBaseTest.__init__(self)

    def runTest(self):
        pkt = testutils.simple_tcp_packet(
            pktlen=100,
            ip_dst="192.168.1.4",
            ip_ttl=64,
            eth_dst="00:01:02:03:04:05",
            eth_src="00:01:02:03:04:05",
        )
        pkt_expected = testutils.simple_tcp_packet(
            pktlen=100,
            ip_dst="192.168.1.4",
            ip_ttl=62,
            eth_dst="00:01:02:03:04:05",
            eth_src="00:01:02:03:04:05",
        )

        testutils.send_packet(self, (0, 0), pkt)

        testutils.verify_packet(self, pkt_expected, (3, 0))


class LongChainOfSwitches(DataplaneBaseTest):
    def __init__(self):
        DataplaneBaseTest.__init__(self)

    def runTest(self):
        pkt = testutils.simple_tcp_packet(
            pktlen=100,
            ip_dst="192.168.1.16",
            ip_ttl=64,
            eth_dst="00:01:02:03:04:05",
            eth_src="00:01:02:03:04:05",
        )

        pkt_expected = testutils.simple_tcp_packet(
            pktlen=100,
            ip_dst="192.168.1.16",
            ip_ttl=58,
            eth_dst="00:01:02:03:04:05",
            eth_src="00:01:02:03:04:05",
        )

        testutils.send_packet(self, (0, 0), pkt)

        testutils.verify_packet(self, pkt_expected, (15, 0))


def log_to_file(msg):
    f = open("/app/app.log", "w")
    f.write(msg + "\n")
    f.close()
