import sys
import os
import logging
import time
from benchexec import systeminfo
from elevate import elevate

from benchexec import tooladapter
from benchexec import util
import docker
from benchexec import benchexec

STOPPED_BY_INTERRUPT = False

class P4Execution(object):
    """
        Class for executing p4 benchmarks
    """
    def __init__(self):
        self.nodes = None #Set by init
        self.switches = None #Set by init
        self.ptf_tester = None #Set by init

        self.client = None
        self.node_networks = []
        self.mgnt_network = []


    def init(self, config, benchmark):
        """
            This functions will set up the docker network to execute the test.
            As a result, it needs root permission for the setup part.
        """

        tool_locator = tooladapter.create_tool_locator(config)
        benchmark.executable = benchmark.tool.executable(tool_locator)
        benchmark.tool_version = benchmark.tool.version(benchmark.executable)

        self.client = docker.from_env()
        

        nrOfNodes = 2
        #Setup networks
        self.setup_network(nrOfNodes)

        #Create node container
        self.nodes = []

        #To be replaceded by input file
        NodeImageName = "basic_node"
        SwitchImageName = "switch_bmv2"
        SwitchSourcePath = "/home/sdn/DockerTesting/Network_Compose/switch_bmv2"
        SwitchTargetPath = "/app"

        for device_nr in range(nrOfNodes):
            self.nodes.append(self.client.containers.create(NodeImageName,
                command="python3 /usr/local/src/ptf/ptf_nn/ptf_nn_agent.py --device-socket {0}@tcp://172.21.0.{1}:10001 -i {2}-1@eth0".format(device_nr ,device_nr+2, device_nr),
                detach=True,
                name="node{0}".format(device_nr+1),
                network="net{0}".format(device_nr+1)
                ))

        mgnt = self.client.networks.get("mgnt")
        mgnt.connect(self.nodes[0])
        mgnt.connect(self.nodes[1])

        #Switch containers
        self.switches = []
        dir_path = os.path.dirname(os.path.realpath(__file__))
        mount_switch = docker.types.Mount(SwitchTargetPath, SwitchSourcePath, type="bind")

        switch_command = "simple_switch "

        for device_nr in range(nrOfNodes):
            switch_command += "-i {0}@eth{0} ".format(device_nr)
        
        switch_command += "/app/P4/simple_switch.json"

        self.switches.append(self.client.containers.create("switch_bmv2",
            command=switch_command,
            detach=True,
            network="net1",
            name="switch1",
            mounts = [mount_switch]
            ))

        #Connect all nodes to the switch
        for device_nr in range(nrOfNodes)[1:]:
            self.client.networks.get("net{0}".format(device_nr+1)).connect(self.switches[0])
        # net2 = self.client.networks.get("net2")
        # net2.connect(self.switches[0])

        #Ptf tester container
        mount_ptf_tester = docker.types.Mount("/app", "/home/sdn/DockerTesting/Network_Compose/ptf_tester/tests", type="bind")
        self.ptf_tester = self.client.containers.create("ptf_tester",
            command="ptf --test-dir /app --device-socket 0-{0-64}@tcp://172.21.0.2:10001 --device-socket 1-{0-64}@tcp://172.21.0.3:10001 --platform nn",
            detach=True,
            network="mgnt",
            name="ptfTester",
            mounts=[mount_ptf_tester])

    def execute_benchmark(self, benchmark, output_handler):

        #Start containers used for this benchmark, except for ptf tester container
        self.start()

        for runSet in benchmark.run_sets:
            if STOPPED_BY_INTERRUPT:
                break

            if not runSet.should_be_executed():
                output_handler.output_for_skipping_run_set(runSet)

            elif not runSet.runs:
                output_handler.output_for_skipping_run_set(
                    runSet, "because it has no files"
                )

            output_handler.output_before_run_set(runSet)

            for run in runSet.runs:

                logs = self._execute_benchmark(run)

                logs = logs.decode("utf-8")
                logging.debug("Logs: " + logs)

                try:
                    with open(run.log_file, "w") as ouputFile:
                        for i in range(6):
                            ouputFile.write("Logging\n")

                        ouputFile.write(logs)
                except OSError:
                    print("Failed")
                
                values = {}
                values["exitcode"] = util.ProcessExitCode.from_raw(0)
                run.cmdline()
                
                run.set_result(values)
                
                output_handler.output_after_run(run)

            output_handler.output_after_benchmark(STOPPED_BY_INTERRUPT)

            self.close()
    
    def _execute_benchmark(self, run):

        self.ptf_tester.start()

        logging.debug('Waiting for ptf tester to finish')
        time.sleep(5)

        return self.ptf_tester.logs()
    
    def setup_network(self, nrOfNodes):
        """
            Creates the networks required to run the test. It will create 1 network for each node.
            This network represents the bridge between the node and the swtich. Further, it creates
            the management network(mgnt) used by the ptf_teter to inject packages.
        """
        for net_id in range(nrOfNodes+1)[1:]:
            try:
                network = self.client.networks.get("net{0}".format(net_id))
                self.node_networks.append(network)
            except docker.errors.NotFound:
                ipam_pool = docker.types.IPAMPool(
                    subnet="172.{0}.0.0/16".format(18+net_id),
                    gateway="172.{0}.0.1".format(18+net_id)
                )

                ipam_config = docker.types.IPAMConfig(
                    pool_configs=[ipam_pool]
                )

                self.client.networks.create(
                    "net{0}".format(net_id),
                    driver="bridge",
                    ipam=ipam_config
                )
        
        try:
            self.mgnt_network = self.client.networks.get("mgnt")
        except docker.errors.NotFound:
            ipam_pool = docker.types.IPAMPool(
                subnet="172.21.0.0/16",
                gateway="172.21.0.1"
                )

            ipam_config = docker.types.IPAMConfig(
                pool_configs=[ipam_pool]
            )

            self.mgnt_network = self.client.networks.create(
                "mgnt",
                driver="bridge",
                ipam=ipam_config
            )


    def get_system_info(self):
        return systeminfo.SystemInfo()
    
    def close(self):
        """
            Cleans up all the running containers. Should be called when test is done.
        """
        logging.debug("Closing containers")
        for container in self.nodes:
            container.remove(force=True)

        for container in self.switches:
            container.remove(force=True)

        self.ptf_tester.remove(force=True)

    def start(self):
        """
            Start all containers
        """
        for container in self.nodes:
            container.start()

        for container in self.switches:
            container.start()

def main(argv=None):
    if argv is None:
        argv = sys.argv


    print("Hello World")

if __name__ == "__main__":
    main()