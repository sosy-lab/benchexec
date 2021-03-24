import sys
import os
import logging
import time
import re
from benchexec import systeminfo
from benchexec.model import Run
from p4.p4_run_setup import P4SetupHandler

from benchexec import tooladapter
from benchexec import util
from benchexec import benchexec
from benchexec import BenchExecException

#File handling
import zipfile
from shutil import copyfile
import json

try:
    import docker
except Exception as e:
    raise BenchExecException("Pythond-docker package not found")

try:
    from pyroute2 import IPRoute
    from pyroute2 import NetNS
except:
    raise BenchExecException("pyroute2 python package not found")


STOPPED_BY_INTERRUPT = False

class P4Execution(object):
    """
    This Class is for executing p4 benchmarks. The class creates docker containers representing each
    device in the network. It creates virutal ethenet connections between all the devices. Finally,
    it sets up a test container connected to all the nodes in the network. As of now it only supports creating 1 
    switch with 4 nodes in a tree format.
    """
    def __init__(self):
        self.nodes = None #Set by init
        self.switches = None #Set by init
        self.ptf_tester = None #Set by init

        self.client = None
        self.node_networks = []
        self.mgnt_network = None

    def init(self, config, benchmark):
        """
        This functions will set up the docker network to execute the test.
        As a result, it needs root permission for the setup part.
        """

        tool_locator = tooladapter.create_tool_locator(config)
        benchmark.executable = benchmark.tool.executable(tool_locator)
        benchmark.tool_version = benchmark.tool.version(benchmark.executable)

        self.switch_source_path, self.ptf_folder_path, self.network_config_path = self.read_folder_paths(benchmark) 

        if not os.path.isdir(self.switch_source_path):
          logging.critical("Switch folder path not found: {0}".format(self.switch_source_path)) 
          raise BenchExecException("Switch folder path not found: {0}".format(self.switch_source_path))
        if not os.path.isdir(self.ptf_folder_path):
            logging.critical("Ptf test folder path not found: {0}".format(self.ptf_folder_path))
            raise( BenchExecException("Ptf test folder path not found: {0}".format(self.ptf_folder_path)))

        if not self.switch_source_path or not self.ptf_folder_path:
            raise BenchExecException("Switch or Ptf folder path not defined." +
                "Switch path: {0} Folder path: {1}".format(self.switch_source_path, self.ptf_folder_path))

        #Extract network config info
        if not self.network_config_path:
            raise BenchExecException("No network config file was defined")
        
        with open (self.network_config_path) as json_file:
            self.network_config = json.load(json_file)

        self.client = docker.from_env()
        
        #To be replaceded by input file
        NodeImageName = "basic_node"
        SwitchImageName = "switch_bmv2"
        PtfImageName = "ptf_tester"
        SwitchTargetPath = "/app"
        self.nrOfNodes = len(self.network_config["nodes"])

        try:
            self.setup_network(self.nrOfNodes)

            #Create the ptf tester container
            mount_ptf_tester = docker.types.Mount("/app", self.ptf_folder_path, type="bind")
            try:
                self.ptf_tester = self.client.containers.create("ptf_tester",
                    detach=True,
                    name="ptfTester",
                    mounts=[mount_ptf_tester],
                    tty=True,
                    network="mgnt")
            except docker.errors.APIError:
                self.ptf_tester = self.client.containers.get("ptfTester")

            #Create node containers
            self.nodes = []
            for node_name in self.network_config["nodes"]:
                #Try get old node from previous run if it exits
                try:
                    self.nodes.append(self.client.containers.get(node_name))
                    logging.debug("Old node container find with name: " + node_name + ". Using that")
                except docker.errors.APIError:
                    self.nodes.append(self.client.containers.create(NodeImageName,
                        detach=True,
                        name=node_name,
                        network="mgnt"
                        ))

            # for device_nr in range(self.nrOfNodes):
            #     #Try get old node from previous run if it exits
            #     try:
            #         self.nodes.append(self.client.containers.get("node{0}".format(device_nr+1)))
            #         logging.debug("Old node container find with name: " + "node{0}".format(device_nr+1) + ". Using that")
            #     except docker.errors.APIError:
            #         self.nodes.append(self.client.containers.create(NodeImageName,
            #             detach=True,
            #             name="node{0}".format(device_nr+1),
            #             network="mgnt"
            #             ))

            #Switch containers
            self.switches = []
            
            mount_switch = docker.types.Mount(SwitchTargetPath, self.switch_source_path, type="bind")
            
            for switch_info in self.network_config["switches"]:
                try:
                    self.switches.append(self.client.containers.create("switch_bmv2",
                    detach=True,
                    name=switch_info,
                    mounts = [mount_switch]
                    ))
                except docker.errors.APIError as e:
                    self.switches.append(self.client.containers.get(switch_info))
            # try:
            #     self.switches.append(self.client.containers.create("switch_bmv2",
            #         detach=True,
            #         name="switch1",
            #         mounts = [mount_switch]
            #         ))
            # except docker.errors.APIError as e:
            #     self.switches.append(self.client.containers.get("switch1"))

            self.connect_nodes_to_switch_new()  

        except docker.errors.APIError as e:
            self.close()
            raise BenchExecException(str(e))

    def execute_benchmark(self, benchmark, output_handler):
        self.start_container_listening()

        test_dict = self.read_tests()
        setup_handler = P4SetupHandler(benchmark, test_dict)
        setup_handler.update_runsets()

        #Read switch setup log, including table entries
        copyfile(self.switch_source_path + "/log/switch_log.txt", benchmark.log_folder + "Switch_Setup.log")
        copyfile(self.switch_source_path + "/table_command_output.txt", benchmark.log_folder + "Switch_table_entry.log")
        
        with open(self.switch_source_path + "/log/switch_log.txt", "r+") as f:
            f.truncate()
        if output_handler.compress_results:
            self.move_file_to_zip(benchmark.log_folder + "Switch_Setup.log", output_handler, benchmark)
            self.move_file_to_zip(benchmark.log_folder + "Switch_table_entry.log", output_handler, benchmark)

        #Clear up duplicated files
        os.remove(self.switch_source_path + "/table_command_output.txt")
        os.remove(self.switch_source_path + "/table_input.txt")

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
                #Create ptf command depending on nr of nodes
                command = "ptf --test-dir /app " + run.identifier

                for i in range(self.nrOfNodes):
                    command += " --device-socket {0}-{{0-64}}@tcp://172.19.0.{1}:10001".format(i, i+3)

                command += " --platform nn"

                return_code, test_output = self._execute_benchmark(run, command)

                test_output = test_output.decode("utf-8")

                try:
                    with open(run.log_file, "w") as ouputFile:
                        for i in range(6):
                            ouputFile.write("\n")

                        #for result in test_results:
                        ouputFile.write(test_output + "\n")
                except OSError:
                    print("Failed")
                
                values = {}
                values["exitcode"] = util.ProcessExitCode.from_raw(return_code)

                test = run.cmdline()
                run._cmdline = command.split(" ")

                run.set_result(values)
                

                #Save swithc log files
                temp = run.log_file[:-4] + "_switch.log"
                run.switch_log_file = temp

                copyfile(self.switch_source_path + "/log/switch_log.txt", run.switch_log_file)

                #Clear the log file for next test
                with open(self.switch_source_path + "/log/switch_log.txt", "r+") as f:
                    f.truncate()


                print(run.identifier + ":   ", end='')
                output_handler.output_after_run(run)

                if output_handler.compress_results:
                    self.move_file_to_zip(run.switch_log_file, output_handler, benchmark)

            output_handler.output_after_benchmark(STOPPED_BY_INTERRUPT)

        self.close()
    
    def _execute_benchmark(self, run, command):

        return self.ptf_tester.exec_run(command, tty=True)
    
    def setup_network(self, nrOfNodes):
        """
            Creates the networks required to run the test. It will create 1 network for each node.
            This network represents the bridge between the node and the swtich. Further, it creates
            the management network(mgnt) used by the ptf_teter to inject packages.
        """
        
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

    def connect_nodes_to_switch(self):
        """
        This function is what creates all the connection between the devices in the network.
        It will create 1 veth-pair for each device. Put each veth-interface in the correct 
        network namspace, activate them and give them an ipv4 address.
        """

        client_low = docker.APIClient()

        self.start_containers()

        switch_name = ""
        ip = IPRoute()

        #Check if netns folder exists. If not, create one for netns to look intp
        if not os.path.exists("/var/run/netns"):
            os.mkdir("/var/run/netns")

        try:
            for switch in self.switches:
                switch_name = switch.name
                pid = client_low.inspect_container(switch.name)["State"]["Pid"]
                switch_is_setup = False

                #Wait until switch is setup
                max_wait_seconds = 10
                seconds_waited = 0
                while not switch_is_setup and seconds_waited<=max_wait_seconds:
                    switch_is_setup = os.path.exists("/proc/{0}/ns/net".format(pid))
                    time.sleep(1)
                    seconds_waited += 1
                
                #Clear up any old namespaces
                if os.path.islink("/var/run/netns/{0}".format(switch.name)):
                    os.remove("/var/run/netns/{0}".format(switch.name))
                os.symlink("/proc/{0}/ns/net".format(pid), "/var/run/netns/{0}".format(switch.name))

            node_id_nr = 1
            for node in self.nodes:
                pid = client_low.inspect_container(node.name)["State"]["Pid"]
                if os.path.islink("/var/run/netns/{0}".format(node.name)):
                    os.remove("/var/run/netns/{0}".format(node.name))

                os.symlink("/proc/{0}/ns/net".format(pid), "/var/run/netns/{0}".format(node.name))

                try:
                    #Create Veth pair and put them in the right namespace
                    ip.link("add", ifname="n{0}_veth".format(node_id_nr), peer="sv{0}_veth".format(node_id_nr), kind="veth")
                    id_node = ip.link_lookup(ifname='n{0}_veth'.format(node_id_nr))[0]
                    ip.link('set', index=id_node, net_ns_fd=node.name)
                    id_switch = ip.link_lookup(ifname='sv{0}_veth'.format(node_id_nr))[0]
                    ip.link('set', index=id_switch, net_ns_fd=switch_name)

                    ns = NetNS(node.name)
                    ns.link('set', index=id_node, state='up')
                    ns.addr('add', index=id_node, address='192.168.1.{0}'.format(node_id_nr), prefixlen=24)
                except Exception as e:
                    logging.error("Failed to setup veth pair." + str(type(e)) + " " + str(e))
                    self.close()
                    raise BenchExecException("Setup of network failed. Could not setup veth pair. ")
                    
                
                node_id_nr += 1

            #Start all veth in the switch
            ns = NetNS(switch_name)
            net_interfaces = ns.get_links()
            
            for interface in net_interfaces[2:]:
                iface_name = interface["attrs"][0][1]
                id = ns.link_lookup(ifname=iface_name)[0]
                ns.link('set', index=id, state="up")

        except Exception as e:
            ns.close()
            ip.close()
            logging.error(e)
            raise BenchExecException("Failed to setup veth pairs for containers.")

    def connect_nodes_to_switch_new(self):
        client_low = docker.APIClient()
        self.start_containers()

        ip = IPRoute()

        #Check if netns folder exists. If not, create one for netns to look intp
        if not os.path.exists("/var/run/netns"):
            os.mkdir("/var/run/netns")

        for link in self.network_config["links"]:
            device1 = link["device1"]
            device2 = link["device2"]
            pid_device1 = client_low.inspect_container(device1)["State"]["Pid"]
            pid_device2 = client_low.inspect_container(device2)["State"]["Pid"]

            #Interface names. Naming convention will be different dempending on connection type
            iface_device1 = ""
            iface_device2 = ""

            #If connectiong to switch. Make sure it is setup
            if(link["type"] == "Node_to_Switch"):
                switch_is_setup = os.path.exists("/proc/{0}/ns/net".format(pid_device2))
                #Wait until switch is setup
                max_wait_seconds = 10
                seconds_waited = 0
                while not switch_is_setup and seconds_waited<=max_wait_seconds:
                    switch_is_setup = os.path.exists("/proc/{0}/ns/net".format(pid_device2))
                    time.sleep(1)
                    seconds_waited += 1


                #Check if namespaces are addad. If not add simlinl to namespace
                if not os.path.islink("/var/run/netns/{0}".format(device1)):
                    os.symlink("/proc/{0}/ns/net".format(pid_device1), "/var/run/netns/{0}".format(device1))

                if not os.path.islink("/var/run/netns/{0}".format(device2)):
                    if not os.path.exists("/var/run/netns/{0}".format(device2)):
                        os.symlink("/proc/{0}/ns/net".format(pid_device2), "/var/run/netns/{0}".format(device2))

                iface_device1 = link["device1"] + "_{0}".format(link["node_port"])
                iface_device2 = link["device2"] + "_{0}".format(link["switch_port"])

                #Create Veth pair and put them in the right namespace
                ip.link("add", ifname=iface_device1, peer=iface_device2, kind="veth")
                id_node = ip.link_lookup(ifname=iface_device1)[0]
                ip.link('set', index=id_node, net_ns_fd=link["device1"])
                id_switch = ip.link_lookup(ifname=iface_device2)[0]
                ip.link('set', index=id_switch, net_ns_fd=link["device2"])

                #Start all veth port in Nodes
                ns = NetNS(device1)
                ns.link('set', index=id_node, state='up')
                if "ipv4_addr" in self.network_config["nodes"][device1]:
                    ns.addr('add', index=id_node, address=self.network_config["nodes"][device1]["ipv4_addr"], prefixlen=24)
                if "ipv6_addr" in link:
                    continue

            #Start all veth in all the switches
            for switch in self.switches:
                ns = NetNS(switch.name)
                net_interfaces = ns.get_links()
                
                for interface in net_interfaces[2:]:
                    iface_name = interface["attrs"][0][1]
                    id = ns.link_lookup(ifname=iface_name)[0]
                    ns.link('set', index=id, state="up")

    def read_tests(self):
        self.ptf_tester.start()

        _, test_info = self.ptf_tester.exec_run("ptf --test-dir /app --list")
        test_info = test_info.decode()

        test_dict = self.extract_info_from_test_info(test_info)

        return test_dict

    def extract_info_from_test_info(self,test_info):
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
        network_config = ""
        option_index = 0

        while option_index < len(benchmark.options):
            try:
                if "switch" in benchmark.options[option_index].lower():
                    switch_folder = benchmark.options[option_index +1]
                elif "ptf" in benchmark.options[option_index].lower():
                    ptf_folder = benchmark.options[option_index +1]
                elif "network_config" in benchmark.options[option_index].lower():
                    network_config = benchmark.options[option_index +1]
            except:
                self.close()
                raise BenchExecException(benchmark.options[option_index] + " did not match any expected options")

            option_index += 2
               
        return switch_folder, ptf_folder, network_config
            
    def stop(self):
        """
        Needed for automatic cleanup for benchec.
        """
        self.close()

    def close(self):
        """
            Cleans up all the running containers and clear all created namespaces. Should be called when test is done.
        """
        logging.debug("Closing containers and cleaning up namespace")
        for container in self.nodes:
            container.remove(force=True)
            if os.path.islink("/var/run/netns/{0}".format(container.name)):
                os.remove("/var/run/netns/{0}".format(container.name))

        for container in self.switches:
            container.remove(force=True)
            if os.path.islink("/var/run/netns/{0}".format(container.name)):
                os.remove("/var/run/netns/{0}".format(container.name))

        if self.ptf_tester:
            self.ptf_tester.remove(force=True)

    def start_containers(self):
        self.ptf_tester.start()

        for container in self.nodes:
            container.start()

        for container in self.switches:
            container.start()
        
    def start_container_listening(self):
        """
        This will start all container with the correct listening commands.
        """
        node_nr = 1
        for node_container in self.nodes:
            command = ("python3 /usr/local/src/ptf/ptf_nn/ptf_nn_agent.py --device-socket {0}@tcp://172.19.0.{1}:10001 -i {0}-1@{2}_{3}".format(node_nr - 1 , node_nr + 2, node_container.name, self.network_config["nodes"][node_container.name]["used_ports"][0]))
            node_container.exec_run(command, detach=True)

            node_nr += 1


        for switch in self.switches:
            switch_command = "simple_switch --log-file /app/log/switch_log --log-flush"

            used_ports = self.network_config["switches"][switch.name]["used_ports"]
            for port in used_ports:
                switch_command += " -i {0}@".format(port) + switch.name + "_{0}".format(port)

            switch_command += " /app/P4/simple_switch.json"
            switch.exec_run(switch_command, detach=True)
        # for switch in self.switches:
        #     switch_command = "simple_switch --log-file /app/log/switch_log --log-flush"
        #     for node_id in range(len(self.nodes)):
        #         switch_command += " -i {0}@sv{1}_veth".format(node_id, node_id + 1) #TODO

        #     switch_command += " /app/P4/simple_switch.json"
        #     switch.exec_run(switch_command, detach=True)

            #This will add table entries
            switch.exec_run("python3 /app/table_handler.py ip_table.json", detach=True)

    def move_file_to_zip(self, file_path, output_handler, benchmark): 
        log_file_path = os.path.relpath(
                file_path, os.path.join(benchmark.log_folder, os.pardir)
            )
        output_handler.log_zip.write(file_path, log_file_path)
        os.remove(file_path)
