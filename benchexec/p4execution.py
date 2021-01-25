import sys
import os
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
    node1 = client.containers.run("alpine", "echo hello world", detach=True)
    node2 = client.containers.run("alpine", "echo hello world", detach=True)

def get_system_info():
    return systeminfo.SystemInfo()

def main(argv=None):
    if argv is None:
        argv = sys.argv

    



    print("Hello World")

if __name__ == "__main__":
    main()