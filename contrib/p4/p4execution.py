# SPDX-FileCopyrightText: 2020-2021 CASTOR Software Research Centre
# <https://www.castor.kth.se/>
# SPDX-FileCopyrightText: 2020-2021 Johan Paulsson

# SPDX-License-Identifier: Apache-2.0

import os
import logging

import time
import threading
from benchexec import systeminfo
from p4.p4_run_setup import P4SetupHandler
from p4.counter import Counter

from benchexec import tooladapter
from benchexec import util
from benchexec import BenchExecException

# File handling
from shutil import copyfile, rmtree
import json
from distutils.dir_util import copy_tree

try:
    import docker
except ModuleNotFoundError:
    raise BenchExecException(
        "Python-docker package not found. Try reinstalling python docker module"
    )

try:
    from pyroute2 import IPRoute
    from pyroute2 import NetNS
except ModuleNotFoundError:
    raise BenchExecException(
        "pyroute2 python package not found. Try reinstalling pyroute2"
    )


STOPPED_BY_INTERRUPT = False

# Static Parameters
MGNT_NETWORK_SUBNET = "172.19"  # Subnet 192.19.x.x/16
NODE_IMAGE_NAME = "basic_node"
SWITCH_IMAGE_NAME = "switch_bmv2"
PTF_IMAGE_NAME = "ptf_tester"


class P4Execution(object):
    """
    This Class is for executing p4 benchmarks. The class creates docker containers representing each
    device in the network. It creates virutal ethenet connections between all the devices. Finally,
    it sets up a test container connected to all the nodes in the network.
    """

    def __init__(self):
        self.nodes = None  # Set by init
        self.switches = None  # Set by init
        self.ptf_tester = None  # Set by init

        # Includes all nodes and switches, not the ptf tester
        self.nr_of_active_containers = Counter()

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

        # Read test inputs paths
        (
            self.switch_source_path,
            self.ptf_folder_path,
            self.network_config_path,
        ) = self.read_folder_paths(benchmark)

        if not os.path.isdir(self.switch_source_path):
            logging.critical(
                "Switch folder path not found: %s, {self.switch_source_path}"
            )
            raise BenchExecException(
                "Switch folder path not found. Look over setup definition"
            )
        if not os.path.isdir(self.ptf_folder_path):
            logging.critical(
                "Ptf test folder path not found: %s, {self.ptf_folder_path}"
            )
            raise (
                BenchExecException(
                    f"Ptf test folder path not found: {self.ptf_folder_path}"
                )
            )

        if not self.switch_source_path or not self.ptf_folder_path:
            raise BenchExecException(
                "Switch or Ptf folder path not defined."
                f"Switch path: {self.switch_source_path} Folder path: {self.ptf_folder_path}"
            )

        # Extract network config info
        if not self.network_config_path:
            logging.error("No network config file was defined")
            raise BenchExecException("No network config file was defined")

        with open(self.network_config_path) as json_file:
            self.network_config = json.load(json_file)

        setup_is_valid = self.network_file_isValid()

        if not setup_is_valid:
            raise BenchExecException("Network config file is not valid")

        # Container setup
        self.client = docker.from_env()
        self.switch_target_path = "/app"
        self.nrOfNodes = len(self.network_config["nodes"])

        try:
            # Create the ptf tester container
            mount_ptf_tester = docker.types.Mount(
                "/app", self.ptf_folder_path, type="bind"
            )
            try:
                self.ptf_tester = self.client.containers.create(
                    PTF_IMAGE_NAME,
                    detach=True,
                    name="ptfTester",
                    mounts=[mount_ptf_tester],
                    tty=True,
                )
            except docker.errors.APIError:
                self.ptf_tester = self.client.containers.get("ptfTester")

            # Create node containers
            self.nodes = []

            for node_name in self.network_config["nodes"]:
                try:
                    self.nodes.append(
                        self.client.containers.create(
                            NODE_IMAGE_NAME, detach=True, name=node_name
                        )
                    )
                except docker.errors.APIError:
                    logging.error("Failed to setup node container.")

            self.switches = []

            # Each switch needs their own mount copy
            for switch_info in self.network_config["switches"]:
                mount_path = self.create_switch_mount_copy(switch_info)
                mount_switch = docker.types.Mount(
                    self.switch_target_path, mount_path, type="bind"
                )

                try:
                    self.switches.append(
                        self.client.containers.create(
                            SWITCH_IMAGE_NAME,
                            detach=True,
                            name=switch_info,
                            mounts=[mount_switch],
                        )
                    )
                except docker.errors.APIError:
                    self.switches.append(self.client.containers.get(switch_info))

            logging.info("Setting up network")
            self.setup_network()
            self.connect_nodes_to_switch()

        except docker.errors.APIError as e:
            self.close()
            raise BenchExecException(str(e))

    def execute_benchmark(self, benchmark, output_handler):
        """
        Excecutes the benchmark.
        """

        self.start_container_listening()

        # Wait until all nodes and switches are setup
        while self.nr_of_active_containers.value < len(self.nodes + self.switches):
            time.sleep(1)

        test_dict = self.read_tests()
        setup_handler = P4SetupHandler(benchmark, test_dict)
        setup_handler.update_runsets()

        # Read all switch setup logs
        for switch in self.switches:
            switch_log_file = (
                f"{self.switch_source_path}/{switch.name}/log/switch_log.txt"
            )
            switch_command_output = (
                f"{self.switch_source_path}/{switch.name}/table_command_output.txt"
            )

            switch_log_file_new = f"{benchmark.log_folder}{switch.name}_Setup.log"
            switch_command_output_new = (
                f"{benchmark.log_folder}{switch.name}_table_entry.log"
            )

            copyfile(switch_log_file, switch_log_file_new)

            # Check for table output file
            if os.path.exists(switch_command_output):
                copyfile(switch_command_output, switch_command_output_new)
            else:
                logging.info("No tables was loaded for switch: %s, {switch.name}")

            # Clear log file
            with open(switch_log_file, "r+") as f:
                f.truncate()

            if output_handler.compress_results:
                self.move_file_to_zip(switch_log_file_new, output_handler, benchmark)

                if os.path.exists(switch_command_output):
                    self.move_file_to_zip(
                        switch_command_output_new, output_handler, benchmark
                    )

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
                # Create ptf command depending on nr of nodes
                command = f"ptf --test-dir /app {run.identifier}"

                for node in self.nodes:
                    node_config = self.network_config["nodes"][node.name]

                    command += f" --device-socket {node_config['id']}-{{0-64}}@tcp://{MGNT_NETWORK_SUBNET}.0.{node_config['id'] + 3}:10001"

                command += " --platform nn"

                return_code, test_output = self._execute_benchmark(run, command)

                test_output = test_output.decode("utf-8")

                try:
                    with open(run.log_file, "w") as ouputFile:
                        for _i in range(6):
                            ouputFile.write("\n")

                        # for result in test_results:
                        ouputFile.write(test_output + "\n")
                except OSError:
                    print("Failed")

                values = {}
                values["exitcode"] = util.ProcessExitCode.from_raw(return_code)
                run._cmdline = command.split(" ")

                run.set_result(values)

                # Save all switch log_files
                for switch in self.switches:
                    switch_log_file = (
                        f"{self.switch_source_path}/{switch.name}/log/switch_log.txt"
                    )

                    switch_log_file_new = f"{run.log_file[:-4]}_{switch.name}.log"

                    copyfile(switch_log_file, switch_log_file_new)

                    # Clear the log file for next test
                    with open(switch_log_file, "r+") as f:
                        f.truncate()

                    if output_handler.compress_results:
                        self.move_file_to_zip(
                            switch_log_file_new, output_handler, benchmark
                        )

                print(run.identifier + ":   ", end="")
                output_handler.output_after_run(run)

            output_handler.output_after_benchmark(STOPPED_BY_INTERRUPT)

        self.close()

    def _execute_benchmark(self, run, command):
        return self.ptf_tester.exec_run(command, tty=True)

    def setup_network(self):
        """
        Creates the managment network, connectes all nodes and the ptf tester
        to the network.
        """
        try:
            ipam_pool = docker.types.IPAMPool(
                subnet=MGNT_NETWORK_SUBNET + ".0.0/16",  # "172.19.0.0/16",
                gateway=MGNT_NETWORK_SUBNET + ".0.1",  # "172.19.0.1"
            )

            ipam_config = docker.types.IPAMConfig(pool_configs=[ipam_pool])

            self.mgnt_network = self.client.networks.create(
                "mgnt", driver="bridge", ipam=ipam_config
            )
        except docker.errors.APIError as error:
            # Check if error is network overlap
            if "overlap" in str(error):
                self.mgnt_network = self.client.networks.get("mgnt")
            else:
                raise error

        self.mgnt_network.connect(
            self.ptf_tester, ipv4_address=MGNT_NETWORK_SUBNET + ".0.2"
        )

        for node in self.nodes:
            node_config = self.network_config["nodes"][node.name]

            ip_addr = f"{MGNT_NETWORK_SUBNET}.0.{node_config['id'] + 3}"
            self.mgnt_network.connect(node, ipv4_address=ip_addr)

    def connect_nodes_to_switch(self):
        """
        This will create veth pairs for all links definid in the network config.
        Each veth will also be moved to the correct network namespace.
        """
        client_low = docker.APIClient()
        self.start_containers()

        ip = IPRoute()

        # Check if netns folder exists. If not, create one for netns to look intp
        if not os.path.exists("/var/run/netns"):
            os.mkdir("/var/run/netns")

        for link in self.network_config["links"]:
            device1 = link["device1"]
            device2 = link["device2"]
            pid_device1 = client_low.inspect_container(device1)["State"]["Pid"]
            pid_device2 = client_low.inspect_container(device2)["State"]["Pid"]

            # Interface names. Naming convention will be different dempending on connection type
            iface_device1 = ""
            iface_device2 = ""

            # If connectiong to switch. Make sure it is setup
            if link["type"] == "Node_to_Switch":
                switch_is_setup = os.path.exists(f"/proc/{pid_device2}/ns/net")
                # Wait until switch is setup
                max_wait_seconds = 10
                seconds_waited = 0
                while not switch_is_setup and seconds_waited <= max_wait_seconds:
                    switch_is_setup = os.path.exists(f"/proc/{pid_device2}/ns/net")
                    time.sleep(1)
                    seconds_waited += 1

                # Check if namespaces are addad. If not add simlinuk to namespace
                if not os.path.islink(f"/var/run/netns/{device1}"):
                    os.symlink(
                        f"/proc/{pid_device1}/ns/net",
                        f"/var/run/netns/{device1}",
                    )

                if not os.path.islink(f"/var/run/netns/{device2}"):
                    if not os.path.exists(f"/var/run/netns/{device2}"):
                        os.symlink(
                            f"/proc/{pid_device2}/ns/net",
                            f"/var/run/netns/{device2}",
                        )

                iface_device1 = f"{link['device1']}_{link['device1_port']}"
                iface_device2 = f"{link['device2']}_{link['device2_port']}"

                # Create Veth pair and put them in the right namespace
                ip.link("add", ifname=iface_device1, peer=iface_device2, kind="veth")

                id_node = ip.link_lookup(ifname=iface_device1)[0]
                ip.link("set", index=id_node, state="up")
                ip.link("set", index=id_node, net_ns_fd=link["device1"])

                id_switch = ip.link_lookup(ifname=iface_device2)[0]
                ip.link("set", index=id_switch, state="up")
                ip.link("set", index=id_switch, net_ns_fd=link["device2"])

                # Start all veth port in Nodes
                ns = NetNS(device1)
                ns.link("set", index=id_node, state="up")
                if "ipv4_addr" in self.network_config["nodes"][device1]:
                    ns.addr(
                        "add",
                        index=id_node,
                        address=self.network_config["nodes"][device1]["ipv4_addr"],
                        prefixlen=24,
                    )
                if "ipv6_addr" in link:
                    continue

            if link["type"] == "Switch_to_Switch":
                switch_is_setup1 = os.path.exists(f"/proc/{pid_device1}/ns/net")
                switch_is_setup2 = os.path.exists(f"/proc/{pid_device2}/ns/net")

                max_wait_seconds = 10
                seconds_waited = 0
                while not switch_is_setup1 and switch_is_setup2:
                    switch_is_setup1 = os.path.exists(f"/proc/{pid_device1}/ns/net")
                    switch_is_setup2 = os.path.exists(f"/proc/{pid_device2}/ns/net")
                    time.sleep(1)
                    seconds_waited += 1

                # Check if namespaces are addad. If not add simlink to namespace
                if not os.path.islink(f"/var/run/netns/{device1}"):
                    os.symlink(
                        f"/proc/{pid_device1}/ns/net",
                        f"/var/run/netns/{device1}",
                    )

                if not os.path.islink(f"/var/run/netns/{device2}"):
                    if not os.path.exists(f"/var/run/netns/{device2}"):
                        os.symlink(
                            f"/proc/{pid_device2}/ns/net",
                            f"/var/run/netns/{device2}",
                        )

                iface_switch1 = f"{link['device1']}_{link['device1_port']}"
                iface_switch2 = f"{link['device2']}_{link['device2_port']}"

                # Create Veth pair and put them in the right namespace
                ip.link("add", ifname=iface_switch1, peer=iface_switch2, kind="veth")
                id_switch1 = ip.link_lookup(ifname=iface_switch1)[0]
                ip.link("set", index=id_switch1, state="up")
                ip.link("set", index=id_switch1, net_ns_fd=link["device1"])

                id_switch2 = ip.link_lookup(ifname=iface_switch2)[0]
                ip.link("set", index=id_switch2, state="up")
                ip.link("set", index=id_switch2, net_ns_fd=link["device2"])

        # Start all veth in all the switches
        for switch in self.switches:
            ns = NetNS(switch.name)
            net_interfaces = ns.get_links()

            for interface in net_interfaces[2:]:
                iface_name = interface["attrs"][0][1]
                id_switch = ns.link_lookup(ifname=iface_name)[0]
                ns.link("set", index=id_switch, state="up")

    def read_tests(self):
        """
        Read the test from the ptf container
        """
        # Make sure it's started. This is a blocking call
        self.ptf_tester.start()

        _, test_info = self.ptf_tester.exec_run("ptf --test-dir /app --list")
        test_info = test_info.decode()

        test_dict = self.extract_info_from_test_info(test_info)

        return test_dict

    def extract_info_from_test_info(self, test_info):
        test_info = test_info.split("Test List:")[1]
        test_modules = test_info.split("Module ")
        nr_of_modules = len(test_modules) - 1
        test_modules[len(test_modules) - 1] = test_modules[len(test_modules) - 1].split(
            f"\n{nr_of_modules}"
        )[0]

        test_dict = {}

        for i in range(nr_of_modules):
            test = test_modules[i + 1].split("\n")
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
            if "switch" in benchmark.options[option_index].lower():
                switch_folder = benchmark.options[option_index + 1]
            elif "ptf" in benchmark.options[option_index].lower():
                ptf_folder = benchmark.options[option_index + 1]
            elif "network_config" in benchmark.options[option_index].lower():
                network_config = benchmark.options[option_index + 1]

            option_index += 2

        if "~" in switch_folder:
            switch_folder = self.extract_path(switch_folder)
        if "~" in ptf_folder:
            ptf_folder = self.extract_path(ptf_folder)
        if "~" in network_config:
            network_config = self.extract_path(network_config)

        return switch_folder, ptf_folder, network_config

    def extract_path(self, path):
        import subprocess

        split = subprocess.run(["pwd"], capture_output=True).stdout.decode().split("/")
        home_dir = f"/{split[1]}/{split[2]}"

        new_path = path.replace("~", home_dir)

        return new_path

    def stop(self):
        """
        Needed for automatic cleanup for benchec.
        """
        self.close()

    def close(self):
        """
        Cleans up all the running containers and clear all created namespaces. Should be called when test is done.
        """
        logging.info("Closing containers and cleaning up namespace")
        container_threads = []

        for container in self.nodes:
            container_threads.append(
                threading.Thread(
                    target=lambda x: x.remove(force=True), args=(container,)
                )
            )
            if os.path.islink(f"/var/run/netns/{container.name}"):
                os.remove(f"/var/run/netns/{container.name}")

        for container in self.switches:
            if os.path.isdir(f"{self.switch_source_path}/{container.name}"):
                rmtree(f"{self.switch_source_path}/{container.name}")

            container_threads.append(
                threading.Thread(
                    target=lambda x: x.remove(force=True), args=(container,)
                )
            )
            if os.path.islink(f"/var/run/netns/{container.name}"):
                os.remove(f"/var/run/netns/{container.name}")

        if self.ptf_tester:
            container_threads.append(
                threading.Thread(
                    target=lambda x: x.remove(force=True), args=(self.ptf_tester,)
                )
            )

        [x.start() for x in container_threads]
        [x.join() for x in container_threads]

        # Remove when all containers are closed
        if self.mgnt_network:
            self.mgnt_network.remove()

    def thread_remove_container(self, container):
        container.remove(force=True)

    def start_containers(self):
        """
        Start all containers. This is done with thread. This function does not gurantees that
        containers are started.
        """
        containers_to_start = self.nodes + self.switches
        containers_to_start.append(self.ptf_tester)

        container_threads = []

        for container in containers_to_start:
            container_threads.append(
                threading.Thread(target=lambda x: x.start(), args=(container,))
            )

        # Start and wait for all to finish
        [x.start() for x in container_threads]
        [x.join() for x in container_threads]

    def thread_container_start(self, container):
        container.start()

    def start_container_listening(self):
        """
        This will set all the nodes and switches up for testing. This means all nodes runs
        the ptf agent script and all switches run the switch starup command. All the ports and their
        configuration are set automatically.
        """

        container_threads = []

        for node_container in self.nodes:
            # Read node info
            node_config = self.network_config["nodes"][node_container.name]

            node_command = (
                f"python3 /usr/local/src/ptf/ptf_nn/ptf_nn_agent.py --device-socket "
                f"{node_config['id']}@tcp://{MGNT_NETWORK_SUBNET}.0.{node_config['id'] + 3}:10001"
            )
            used_ports = self.network_config["nodes"][node_container.name]["used_ports"]

            for port_nr in used_ports:
                node_command += (
                    f" -i {node_config['id']}-{port_nr}@{node_container.name}_{port_nr}"
                )

            container_threads.append(
                threading.Thread(
                    target=self.thread_setup_node, args=(node_container, node_command)
                )
            )

        for switch in self.switches:
            switch_config = self.network_config["switches"][switch.name]

            switch_command = "simple_switch --log-file /app/log/switch_log --log-flush"

            used_ports = self.network_config["switches"][switch.name]["used_ports"]
            for port in used_ports:
                switch_command += f" -i {port}@{switch.name}_{port}"

            switch_command += f" /app/P4/{switch_config['p4_file_name']}"

            container_threads.append(
                threading.Thread(
                    target=self.thread_setup_switch, args=(switch, switch_command)
                )
            )

        # Wait for all to setup befor leaveing the method
        [x.start() for x in container_threads]
        [x.join() for x in container_threads]

    def set_link_state(self, ns, state, iface_ids):
        available_states = ["UP", "DOWN"]

        if state in available_states:
            for iface_id in iface_ids:
                ns.link("set", index=iface_id, state=state)

    def thread_setup_switch(self, switch_container, switch_command):
        """
        Sets up a switch. Ment to be ran in a thread.
        """
        ns = NetNS(switch_container.name)

        # Check if some interface failed to start
        while len(ns.link_lookup(IFLA_OPERSTATE="DOWN")) != 0:
            self.set_link_state(ns, "UP", ns.link_lookup(IFLA_OPERSTATE="DOWN"))
            time.sleep(1)

        switch_container.exec_run(switch_command, detach=True)
        switch_is_setup = False
        switch_log_file_path = (
            f"{self.switch_source_path}/{switch_container.name}/log/switch_log.txt"
        )

        # This loop will wait until server is started up
        while not switch_is_setup:
            with open(switch_log_file_path, "r") as f:
                info_string = f.read()
                switch_is_setup = "Thrift server was started" in info_string

            time.sleep(1)

        # Load tables
        if "table_entries" in self.network_config["switches"][switch_container.name]:
            for table_name in self.network_config["switches"][switch_container.name][
                "table_entries"
            ]:
                table_file_path = f"{self.switch_source_path}/{switch_container.name}/tables/{table_name}"
                if os.path.exists(table_file_path):
                    switch_container.exec_run(
                        f"python3 /app/table_handler.py "
                        f"{self.switch_target_path}/tables/{table_name}",
                        detach=True,
                    )
                else:
                    logging.info("Could not find table: \n %s", table_file_path)

        self.nr_of_active_containers.increment()

    def thread_setup_node(self, node_container, node_command):
        node_container.exec_run(node_command, detach=True)
        self.nr_of_active_containers.increment()

    def create_switch_mount_copy(self, switch_name):
        switch_path = f"{self.switch_source_path}/{switch_name}"
        os.mkdir(switch_path)

        # Copy relevant folders
        os.mkdir(switch_path + "/log")
        os.mkdir(switch_path + "/P4")
        os.mkdir(switch_path + "/tables")

        # Create log file for switch to use
        open(switch_path + "/log/switch_log.txt", "x")
        copy_tree(self.switch_source_path + "/P4", switch_path + "/P4")
        copy_tree(self.switch_source_path + "/tables", switch_path + "/tables")

        copyfile(
            self.switch_source_path + "/table_handler.py",
            switch_path + "/table_handler.py",
        )

        return switch_path

    def move_file_to_zip(self, file_path, output_handler, benchmark):
        log_file_path = os.path.relpath(
            file_path, os.path.join(benchmark.log_folder, os.pardir)
        )
        output_handler.log_zip.write(file_path, log_file_path)
        os.remove(file_path)

    def network_file_isValid(self):
        """
        Simple chech throught the network file
        """
        if not self.network_config:
            logging.debug("No network file is defined for validation")
            return False
        else:
            # Check nodes
            if "nodes" not in self.network_config:
                logging.debug("No nodes defined in network config")
                return False
            elif len(self.network_config["nodes"]) == 0:
                logging.debug("No nodes defined in network config")
                return False

            # Check for duplicate node names TODO Check duplicate ids
            node_names = list(self.network_config["nodes"].keys())

            for node_name in node_names:
                if node_names.count(node_name) > 1:
                    logging.debug("Duplicate node name detected")
                    return False

            # Check switches
            if "switches" not in self.network_config:
                logging.debug("No switches defined")
                return False
            elif len(self.network_config["switches"]) == 0:
                logging.debug("No nodes defined in network config")
                return False

            switch_names = list(self.network_config["switches"].keys())

            for switch_name in switch_names:
                if switch_names.count(switch_name) > 1:
                    logging.debug("Duplicate switch name detected")
                    return False

            # Check links
            if "links" in self.network_config:
                all_devices = switch_names + node_names

                for link in self.network_config["links"]:
                    if (
                        link["device1"] not in all_devices
                        or link["device2"] not in all_devices
                    ):
                        logging.debug("Link between none defined devices detected")
                        return False
                    if not isinstance(link["device1_port"], int) or not isinstance(
                        link["device2_port"], int
                    ):
                        return False

        return True
