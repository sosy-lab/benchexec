# SPDX-FileCopyrightText: 2020-2021 CASTOR Software Research Centre
# <https://www.castor.kth.se/>
# SPDX-FileCopyrightText: 2020-2021 Johan Paulsson

# SPDX-License-Identifier: Apache-2.0

import os

import ptf
from ptf import config, testutils
from ptf.base_tests import BaseTest


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


class OneTest(DataplaneBaseTest):
    def __init__(self):
        DataplaneBaseTest.__init__(self)

    def runTest(self):
        pkt = testutils.simple_tcp_packet(pktlen=100)

        try:
            testutils.send_packet(self, (0, 1), pkt)
        except Exception as e:
            print(e)

        testutils.verify_packet(self, pkt, (1, 1))


def log_to_file(msg):
    with open("/app/app.log", "a") as f:
        f.write(msg + "\n")
