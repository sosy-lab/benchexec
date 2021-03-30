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
        #log_to_file("Staring first test")
        pkt = testutils.simple_tcp_packet(pktlen=100)
        pkt_failed = testutils.simple_tcp_packet(pktlen=11)

        try:
            testutils.send_packet(self, (0, 1), pkt)
        except Exception as e:
            print(e)
        
        testutils.verify_packet(self, pkt, (1, 1))

def log_to_file(msg):
    f = open("/app/app.log", "a")
    f.write(msg + "\n")
    f.close()

        
