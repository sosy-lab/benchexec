import sys
import os
import logging
from benchexec import systeminfo
from elevate import elevate

import docker
from benchexec import benchexec



def init(config, benchmark):
    """
        This functions will set up the docker network to execute the test.
        As a result, it needs root permission for the setup part.
    """
    print("In P4Execution")

    client = docker.from_env()

    #Node containers
    node1 = client.containers.run("basic_node",
        command="python3 /usr/local/src/ptf/ptf_nn/ptf_nn_agent.py --device-socket 0@tcp://172.21.0.3:10001 -i 0-1@eth0", 
        detach=True,
        name="node1",
        network="net1")
    node2 = client.containers.run("basic_node", 
        command="python3 /usr/local/src/ptf/ptf_nn/ptf_nn_agent.py --device-socket 0@tcp://172.21.0.4:10002 -i 1-1@eth0", 
        detach=True,
        name="node2",
        network="net2"
    )

    #Switch containers
    dir_path = os.path.dirname(os.path.realpath(__file__))
    mount1 = docker.types.Mount("/app", "/home/sdn/DockerTesting/Network_Compose/switch/switchDocs", type="bind")


    switch1 = client.containers.run("switch_test",
        command="python3 /app/ptf_nn_test_bridge.py -ifrom eth0 -ito eth1",
        detach=True,
        network="net1",
        name="switch1",
        mounts = [mount1]
        )

    ptf_tester = client.containers.run("ptf_tester",
        command="tail -f /dev/null",
        detach=True,
        network="mgnt",
        name="ptfTester")

    


def get_system_info():

    return systeminfo.SystemInfo()

def main(argv=None):
    if argv is None:
        argv = sys.argv


    print("Hello World")

if __name__ == "__main__":
    main()