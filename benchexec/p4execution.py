import sys
import os
import logging
import time
from benchexec import systeminfo
from benchexec.model import Run
from benchexec.p4_run_setup import P4SetupHandler

from benchexec import tooladapter
from benchexec import util
import docker
from benchexec import benchexec
from benchexec import BenchExecException

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

        switch_source_path, ptf_folder_path = self.read_folder_paths(benchmark) 

        if not os.path.isdir(switch_source_path):
          logging.critical("Switch folder path not found: {0}".format(switch_source_path)) 
          raise BenchExecException("Switch folder path not found: {0}".format(switch_source_path))
        if not os.path.isdir(ptf_folder_path):
            logging.critical("Ptf test folder path not found: {0}".format(ptf_folder_path))
            raise( BenchExecException("Ptf test folder path not found: {0}".format(ptf_folder_path)))

        if not switch_source_path or not ptf_folder_path:
            raise BenchExecException("Switch or Ptf folder path not defined." +
                "Switch path: {0} Folder path: {1}".format(switch_source_path, ptf_folder_path))

        self.client = docker.from_env()
        
        #To be replaceded by input file
        NodeImageName = "basic_node"
        SwitchImageName = "switch_bmv2"
        SwitchTargetPath = "/app"
        nrOfNodes = 4

        #Setup networks
        self.setup_network(nrOfNodes)

        #Create node container
        self.nodes = []

        for device_nr in range(nrOfNodes):
            self.nodes.append(self.client.containers.create(NodeImageName,
                command="python3 /usr/local/src/ptf/ptf_nn/ptf_nn_agent.py --device-socket {0}@tcp://172.19.0.{1}:10001 -i {2}-1@eth0".format(device_nr ,device_nr+3, device_nr),
                detach=True,
                name="node{0}".format(device_nr+1),
                network="net{0}".format(device_nr+1)
                ))

        #Switch containers
        self.switches = []
        
        mount_switch = docker.types.Mount(SwitchTargetPath, switch_source_path, type="bind")

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

        #Ptf tester container
        mount_ptf_tester = docker.types.Mount("/app", ptf_folder_path, type="bind")
        self.ptf_tester = self.client.containers.create("ptf_tester",
            detach=True,
            name="ptfTester",
            mounts=[mount_ptf_tester],
            tty=True)

        #Setup mgnt network
        mgnt = self.client.networks.get("mgnt")
        mgnt.connect(self.ptf_tester)
        for node in self.nodes:
            mgnt.connect(node)

    def execute_benchmark(self, benchmark, output_handler):
        self.start_containers()

        test_dict = self.read_tests()

        setup_handler = P4SetupHandler(benchmark, test_dict)
        setup_handler.update_runsets()

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
                command = ("ptf --test-dir /app " + run.identifier + " " + 
                "--device-socket 0-{0-64}@tcp://172.19.0.3:10001 " + 
                "--device-socket 1-{0-64}@tcp://172.19.0.4:10001 " + 
                "--device-socket 2-{0-64}@tcp://172.19.0.5:10001 " + 
                "--device-socket 3-{0-64}@tcp://172.19.0.6:10001 " + 
                "--platform nn")

                return_code, test_output = self._execute_benchmark(run, command)

                test_output = test_output.decode("utf-8")
                test_output_list = test_output.split("\r\n")

                #Extract simple information to determine results
                #_ , test_names = self._execute_benchmark(run,"ptf --test-dir /app/test_with_fail --list-test-names")
                #test_names = test_names.decode("utf-8")
                #test_names = test_names.split("\r\n")
                
                if os.path.exists("/home/sdn/benchexec/test.txt"):
                    os.remove("/home/sdn/benchexec/test.txt")
                f = open("/home/sdn/benchexec/test.txt", "w+")
                f.write(test_output)
                
                

                #f.write(str(test_names))

                # f.write("Extract result")
                # test_results = []
                # for test in test_names:
                #     if test:
                #         matching = [s for s in test_output_list if test in s]
                #         test_results.append(matching[0])
                #         f.write(matching[0] + "\n")
                # f.close()

                logging.debug("Logs: " + test_output)

                try:
                    with open(run.log_file, "w") as ouputFile:
                        for i in range(6):
                            ouputFile.write("Logging\n")

                        #for result in test_results:
                        ouputFile.write(test_output + "\n")
                except OSError:
                    print("Failed")
                
                values = {}
                values["exitcode"] = util.ProcessExitCode.from_raw(return_code)
                test = run.cmdline()
                
                run.set_result(values)
                
                output_handler.output_after_run(run)

            output_handler.output_after_benchmark(STOPPED_BY_INTERRUPT)

        self.close()
        #self.clear_networks()
    
    def _execute_benchmark(self, run, command):

        return self.ptf_tester.exec_run(command, tty=True)
    
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
                    subnet="172.{0}.0.0/16".format(19+net_id),
                    gateway="172.{0}.0.1".format(19+net_id)
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
                subnet="172.19.0.0/16",
                gateway="172.19.0.1"
                )

            ipam_config = docker.types.IPAMConfig(
                pool_configs=[ipam_pool]
            )

            self.mgnt_network = self.client.networks.create(
                "mgnt",
                driver="bridge",
                ipam=ipam_config
            )

    def read_tests(self):
        self.ptf_tester.start()

        _, test_info = self.ptf_tester.exec_run("ptf --test-dir /app --list")
        test_info = test_info.decode()

        test_dict = self.extract_info_from_test_info(test_info)

        return test_dict

    def extract_info_from_test_info(self,test_info):
        testing = test_info.split("\n")
        test_info = test_info.split("Test List:")[1]
        test_modules = test_info.split("Module ")
        nr_of_modules = len(test_modules) - 1
        test_modules[len(test_modules)-1] = test_modules[len(test_modules)-1].split("\n{0}".format(nr_of_modules))[0]
        

        test_dict = {}

        for i in range(nr_of_modules):
            test = test_modules[i+1].split("\n")
            module_name = test.pop(0).split(":")[0]

            test_names = []
            for test_string in test:
                if not str.isspace(test_string) and test_string:
                    test_names.append(test_string.split(":")[0].strip())
            
            test_dict[module_name] = test_names
        
        return test_dict

    def get_system_info(self):
        return systeminfo.SystemInfo()
    
    def read_folder_paths(self, benchmark):

        switch_folder = ""
        ptf_folder = ""
        option_index = 0

        while option_index < len(benchmark.options):
            try:
                if "switch" in benchmark.options[option_index].lower():
                    switch_folder = benchmark.options[option_index +1]
                elif "ptf" in benchmark.options[option_index].lower():
                    ptf_folder = benchmark.options[option_index +1]
            except:
                test = ""

            option_index += 2
               
        return switch_folder, ptf_folder
            
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

    def start_containers(self):
        self.ptf_tester.start()

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