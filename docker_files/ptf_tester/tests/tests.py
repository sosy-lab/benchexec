import ptf
from ptf.base_tests import BaseTest
from ptf import config
import ptf.testutils as testutils
from scapy.all import *

import re

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



class OneTest(DataplaneBaseTest):
    def __init__(self):
        DataplaneBaseTest.__init__(self)

    def runTest(self):
        #pkt = "ab" * 20
        #pkt = pkt.encode()
        pkt = testutils.simple_tcp_packet(pktlen=200)

        #pkt = Ether() / Raw(load="Hello World")

        testutils.send_packet(self, (0, 1), pkt)
        print("packet sent")

        pkt2 = Raw(load="Hello World")

        testutils.verify_packet(self, pkt, (1, 1))
        # pkt = "cd" * 20
        # pkt = pkt.encode()

        # nrOfPack = 1

        # string = "Sending {0} packages".format(nrOfPack)
        # print(string)

        # for i in range(nrOfPack):
        #     pkt = str(i) * 2 * 20
        #     pkt = pkt.encode()
        #     testutils.send_packet(self, (0, 1), pkt)

        # for i in range(nrOfPack):
        #     pkt = str(i) * 2 * 20
        #     pkt = pkt.encode()
        #     result = self.dataplane.poll(1, 1)
        #     print("Result", result)
        #     testutils.verify_packet(self, pkt, (1, 1))
