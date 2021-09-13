# SPDX-FileCopyrightText: 2020-2021 CASTOR Software Research Centre
# <https://www.castor.kth.se/>
# SPDX-FileCopyrightText: 2020-2021 Johan Paulsson

# SPDX-License-Identifier: Apache-2.0
import os
import logging
import shutil

import time
import threading
from benchexec import systeminfo
from .p4_run_setup import P4SetupHandler
from p4_files.counter import Counter
from .constants import *
from .helper_functions import (
    parse_netlink_error,
    create_tofino_bin,
    find_bin_and_context,
    find_test_network_configs,
)

from benchexec import tooladapter
from benchexec import util
from benchexec import BenchExecException

# Handles p4 server connection and communicatiion
from .switch_utils.switch_connection import SwitchConnection
from .switch_utils.p4info_helper import P4InfoHelper


# File handling
from shutil import copyfile, rmtree
import json
from distutils.dir_util import copy_tree, remove_tree

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

SDE = "/home/p4/installations/bf-sde-9.5.0"
SDE_INSTALL = f"{SDE}/install"


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
        self.switch_connections = []

        self.terminate = False

        # Includes all nodes and switches, not the ptf tester
        self.nr_of_active_containers = Counter()

        self.switch_connections = []  # Holds all connections to the active switches

        self.lock = threading.Lock()

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

        self.tmp_folder = __file__.rpartition("/")[0] + "/tmp"

        if os.path.exists(self.tmp_folder):
            rmtree(self.tmp_folder)
        os.mkdir(self.tmp_folder)

        # Read test inputs paths
        (
            self.switch_source_path,
            self.ptf_folder_path,
            self.network_config_path,
        ) = self.read_folder_paths(benchmark)

        if not self.switch_source_path:
            self.switch_source_path = (
                __file__.rpartition("/")[0] + f"/docker_files/switch_tofino"
            )

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

        # Check if user defined network config. Else look if test has a network config
        if not self.network_config_path:
            logging.error("No network config file was defined")
            raise BenchExecException("No network config file was defined")
        else:
            with open(self.network_config_path) as json_file:
                self.network_config = json.load(json_file)

            setup_is_valid = self.network_file_isValid()

            if not setup_is_valid:
                raise BenchExecException("Network config file is not valid")

        # Read all required ptf tests folders
        self.ptf_folder_paths = self.read_ptf_folder_paths(benchmark)

        # Container setup
        self.client = docker.from_env()
        self.switch_target_path = f"{CONTAINTER_BASE_DIR}"
        self.nrOfNodes = len(self.network_config[KEY_NODES])

        try:
            # Create the ptf tester container
            mounts = []
            for path in self.ptf_folder_paths:
                folder_name = path.split("/")[-1]
                mounts.append(
                    docker.types.Mount(
                        f"{CONTAINTER_BASE_DIR}/{folder_name}",
                        path,
                        type="bind",
                    )
                )

            self.ptf_tester = self.client.containers.create(
                PTF_IMAGE_NAME,
                detach=True,
                name=PTF_IMAGE_NAME,
                mounts=mounts,
                tty=True,
            )

            # Create node containers
            self.nodes = []

            for node_name in self.network_config[KEY_NODES]:
                try:
                    self.nodes.append(
                        self.client.containers.create(
                            NODE_IMAGE_NAME, detach=True, name=node_name
                        )
                    )
                except docker.errors.APIError as e:
                    logging.error(f"Error creating container {node_name}")
                    raise BenchExecException(str(e))

            self.switches = []

            # Each switch needs their own mount copy
            for switch_info in self.network_config[KEY_SWITCHES]:

                switch_config = self.network_config[KEY_SWITCHES][switch_info]

                mount_path = self.create_tofino_switch_mount_copy(switch_info)
                mount_switch = docker.types.Mount(
                    self.switch_target_path, mount_path, type="bind"
                )

                server_port = switch_config[KEY_SERVER_PORT]

                try:
                    self.switches.append(
                        self.client.containers.create(
                            SWITCH_IMAGE_NAME,
                            detach=True,
                            name=switch_info,
                            mounts=[mount_switch],
                            privileged=True,
                            ports={f"{server_port}/tcp": ("127.0.0.1", server_port)},
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

        self.active_net_conf = None
        self.start_container_listening_tofino()

        # Wait until all nodes and switches are setup
        while self.nr_of_active_containers.value < len(self.nodes + self.switches):
            time.sleep(1)

        self.read_tests(benchmark)

        setup_handler = P4SetupHandler(benchmark)
        setup_handler.update_runsets()

        # Read if any test specific test configs
        self.test_configs = find_test_network_configs(self.ptf_folder_path)

        # Read all switch setup logs
        for switch in self.switches:
            files = os.listdir(f"{self.tmp_folder}/{switch.name}")
            model_log_file = ""
            driver_log_file = ""
            for file in files:
                if "model" in file:
                    model_log_file = f"{self.tmp_folder}/{switch.name}/{file}"
                if "driver" in file:
                    driver_log_file = f"{self.tmp_folder}/{switch.name}/{file}"

            # Store the setup logs and then clear them
            switch_model_setup = f"{benchmark.log_folder}{switch.name}_model_setup.log"

            switch_driver_setup = (
                f"{benchmark.log_folder}{switch.name}_driver_setup.log"
            )

            copyfile(model_log_file, switch_model_setup)
            copyfile(driver_log_file, switch_driver_setup)

            # Clear log file
            with open(model_log_file, "r+") as f:
                f.truncate()

            # Clear log file
            with open(driver_log_file, "r+") as f:
                f.truncate()

            if output_handler.compress_results:
                self.move_file_to_zip(switch_model_setup, output_handler, benchmark)
                self.move_file_to_zip(switch_driver_setup, output_handler, benchmark)

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
                # Check if network setup needs to be updated
                net_work_conf = self.run_network_conf_path(run)

                if not self.active_net_conf or self.active_net_conf != net_work_conf:
                    self.active_net_conf = net_work_conf

                    self.update_network_config(self.active_net_conf)

                # Create ptf command depending on nr of nodes
                command = f"ptf --test-dir /app/{run.test_folder_name} {run.identifier}"

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
                    files = os.listdir(f"{self.tmp_folder}/{switch.name}")
                    model_log_file = ""
                    driver_log_file = ""

                    for file in files:
                        if "model" in file:
                            model_log_file = f"{self.tmp_folder}/{switch.name}/{file}"
                        if "driver" in file:
                            driver_log_file = f"{self.tmp_folder}/{switch.name}/{file}"

                    model_log_file_new = f"{run.log_file[:-4]}_{switch.name}.log"

                    with open(model_log_file, "r") as log_file:
                        with open(model_log_file_new, "w") as log_file_new:
                            log_file_new.write(log_file.read().replace("\x00", ""))

                    # Clear the log file for next test
                    with open(model_log_file, "r+") as f:
                        f.truncate()

                    if output_handler.compress_results:
                        self.move_file_to_zip(
                            model_log_file_new, output_handler, benchmark
                        )

                print(run.identifier + ":   ", end="")
                output_handler.output_after_run(run)

        output_handler.output_after_benchmark(STOPPED_BY_INTERRUPT)

        self.close()

        return 0

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

    def create_docker_containers(self):
        try:
            # Create the ptf tester container
            mounts = []
            for path in self.ptf_folder_paths:
                folder_name = path.split("/")[-1]
                mounts.append(
                    docker.types.Mount(
                        f"{CONTAINTER_BASE_DIR}/{folder_name}",
                        path,
                        type="bind",
                    )
                )

            self.ptf_tester = self.client.containers.create(
                PTF_IMAGE_NAME,
                detach=True,
                name=PTF_IMAGE_NAME,
                mounts=mounts,
                tty=True,
            )

            # Create node containers
            self.nodes = []

            for node_name in self.network_config[KEY_NODES]:
                try:
                    self.nodes.append(
                        self.client.containers.create(
                            NODE_IMAGE_NAME, detach=True, name=node_name
                        )
                    )
                except docker.errors.APIError as e:
                    logging.error(f"Error creating container {node_name}")
                    raise BenchExecException(str(e))

            self.switches = []

            # Each switch needs their own mount copy
            for switch_info in self.network_config[KEY_SWITCHES]:

                switch_config = self.network_config[KEY_SWITCHES][switch_info]

                mount_path = self.create_tofino_switch_mount_copy(switch_info)
                mount_switch = docker.types.Mount(
                    self.switch_target_path, mount_path, type="bind"
                )

                server_port = switch_config[KEY_SERVER_PORT]

                try:
                    self.switches.append(
                        self.client.containers.create(
                            SWITCH_IMAGE_NAME,
                            detach=True,
                            name=switch_info,
                            mounts=[mount_switch],
                            privileged=True,
                            ports={f"{server_port}/tcp": ("127.0.0.1", server_port)},
                        )
                    )
                except docker.errors.APIError:
                    self.switches.append(self.client.containers.get(switch_info))
        except docker.errors.APIError as e:
            self.close()
            raise BenchExecException(str(e))

    @parse_netlink_error
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

        link_nr = 0

        for link in self.network_config["links"]:
            device1 = link["device1"]
            device2 = link["device2"]
            pid_device1 = client_low.inspect_container(device1)["State"]["Pid"]
            pid_device2 = client_low.inspect_container(device2)["State"]["Pid"]

            # Interface names. Naming convention will be different dempending on connection type
            iface_device1 = ""
            iface_device2 = ""

            # Check namespaces. Clear if any previous is still existing from prev runs
            if os.path.islink(f"/var/run/netns/{device1}"):
                os.remove(f"/var/run/netns/{device1}")
            os.symlink(
                f"/proc/{pid_device1}/ns/net",
                f"/var/run/netns/{device1}",
            )

            if os.path.islink(f"/var/run/netns/{device2}"):
                os.remove(f"/var/run/netns/{device2}")
            os.symlink(
                f"/proc/{pid_device2}/ns/net",
                f"/var/run/netns/{device2}",
            )

            device1_port = link["device1_port"]
            device2_port = link["device2_port"]
            iface_device1 = f"veth{device1_port}"
            iface_device2 = f"veth{device1_port+1}"

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

                # # Check if namespaces are addad. If not add simlinuk to namespace
                # if os.path.islink(f"/var/run/netns/{device1}"):
                #     os.remove(f"/var/run/netns/{device1}")

                # os.symlink(
                #     f"/proc/{pid_device1}/ns/net",
                #     f"/var/run/netns/{device1}",
                # )

                # if os.path.islink(f"/var/run/netns/{device2}"):
                #     os.remove(f"/var/run/netns/{device1}")
                # if not os.path.exists(f"/var/run/netns/{device2}"):
                #     os.symlink(
                #         f"/proc/{pid_device2}/ns/net",
                #         f"/var/run/netns/{device2}",
                #     )

                # device1_port = link["device1_port"]
                # device2_port = link["device2_port"]
                # iface_device1 = f"veth{device1_port}"
                # iface_device2 = f"veth{device1_port+1}"

                # Create Veth pair and put them in the right namespace
                ip.link("add", ifname=iface_device1, peer=iface_device2, kind="veth")

                id_node = ip.link_lookup(ifname=iface_device1)[0]
                ip.link("set", index=id_node, state="up")
                ip.link("set", index=id_node, net_ns_fd=link["device1"])

                id_device2 = ip.link_lookup(ifname=iface_device2)[0]

                # Allow for the veth to have same names. So change back
                iface_device2 = f"veth{device2_port}"

                ip.link("set", index=id_device2, ifname=iface_device2)
                ip.link("set", index=id_device2, state="up")
                ip.link("set", index=id_device2, net_ns_fd=link["device2"])

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

                # Create Veth pair and put them in the right namespace
                ip.link("add", ifname=iface_device1, peer=iface_device2, kind="veth")

                id_node = ip.link_lookup(ifname=iface_device1)[0]
                ip.link("set", index=id_node, state="up")
                ip.link("set", index=id_node, net_ns_fd=link["device1"])

                id_switch = ip.link_lookup(ifname=iface_device2)[0]

                # Allow for the veth to have same names. So change back
                iface_device2 = f"veth{device2_port}"

                ip.link("set", index=id_switch, ifname=iface_device2)
                ip.link("set", index=id_switch, state="up")
                ip.link("set", index=id_switch, net_ns_fd=link["device2"])

            link_nr += 1

        # Start all veth in all the switches
        for switch in self.switches:
            ns = NetNS(switch.name)
            net_interfaces = ns.get_links()

            for interface in net_interfaces[2:]:
                iface_name = interface["attrs"][0][1]
                id_switch = ns.link_lookup(ifname=iface_name)[0]
                ns.link("set", index=id_switch, state="up")

    def create_port_config(self, switch_config, file_path):
        """
        Create the portinfo file required for the tofino switch
        """
        port_dict = {}
        port_dict["PortToVeth"] = []
        for port_id in switch_config["used_ports"]:
            port_dict["PortToVeth"].append(
                {"device_port": port_id, "veth1": port_id, "veth2": 999}
            )

        with open(file_path, "w") as ports_file:
            ports_file.write(json.dumps(port_dict, indent=4))

    def read_tests(self, benchmark):
        """
        Asks the ptf container for
        """
        # Make sure it's started. This is a blocking call
        self.ptf_tester.start()

        for run_set in benchmark.run_sets:
            for run in run_set.runs:
                run.ptf_test_path = ""
                i = 0
                for option in run.options:

                    if option == KEY_PTF_FOLDER_PATH:
                        run.ptf_test_path = self.extract_path(run.options[i + 1])
                    i += 1

                run.test_folder_name = run.ptf_test_path.split("/")[-1]
                _, test_info = self.ptf_tester.exec_run(
                    f"ptf --test-dir /app/{run.test_folder_name} --list"
                )
                test_info = test_info.decode()

                run.test_dict = self.extract_info_from_test_info(test_info)

    def extract_info_from_test_info(self, test_info):
        """
        Extracts test infomation regarding ptf test

        Args:
            test_info ([Info string]): [Info about tests]

        Returns:
            [dict]: [Dictionary containing test names]
        """
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
        """ "
        Reads the folder paths from from the benchmark file
        """
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

    def extract_path(self, path) -> str:
        """ "
        Used to be able to enter ~ char in path
        """
        if not "~" in path:
            return path

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
        raise BenchExecException("")

    def close(self):
        """
        Cleans up all the running containers and clear all created namespaces. Should be called when test is done.
        """
        self.terminate = True

        if threading.current_thread().native_id == threading.main_thread().native_id:
            # Cancel switch connections
            for switch_con in self.switch_connections:
                switch_con.shutdown()

            container_threads = []

            if self.nodes:
                while len(self.nodes) > 0:
                    cont = self.nodes.pop(0)

                    self.thread_remove_container(cont)
                    if os.path.islink(f"/var/run/netns/{cont.name}"):
                        os.remove(f"/var/run/netns/{cont.name}")

            if self.switches:
                while len(self.switches):
                    cont = self.switches.pop(0)
                    self.thread_remove_container(cont)

                    if os.path.isdir(f"{self.tmp_folder}/{cont.name}"):
                        rmtree(f"{self.tmp_folder}/{cont.name}")
                    if os.path.islink(f"/var/run/netns/{cont.name}"):
                        os.remove(f"/var/run/netns/{cont.name}")

            if self.ptf_tester:
                self.thread_remove_container(self.ptf_tester)

            [x.start() for x in container_threads]
            [x.join() for x in container_threads]

            if self.nodes:
                self.nodes.clear()
            if self.switches:
                self.switches.clear()

            self.ptf_tester = None
            # Remove when all containers are closed
            if self.mgnt_network:
                try:
                    self.mgnt_network.remove()
                except Exception as e:
                    logging.debug(f"Failed to remove network. Error {e}")
            logging.debug("Done Cleaning")

    def thread_remove_container(self, container):
        """
        Try remove the container
        """
        try:
            container.remove(force=True)
        except:
            return

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
                node_command += " -i {0}-{1}@{2}_{1}".format(
                    node_config["id"], port_nr, node_container.name
                )

            container_threads.append(
                threading.Thread(
                    target=self.thread_setup_node, args=(node_container, node_command)
                )
            )

        for switch in self.switches:
            switch_config = self.network_config[KEY_SWITCHES][switch.name]

            prog_name = switch_config["name"]
            switch_command = f"{prog_name} --log-file /app/log/switch_log --log-flush"

            used_ports = self.network_config[KEY_SWITCHES][switch.name]["used_ports"]
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

    def start_container_listening_tofino(self):
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
                node_command += " -i {0}-{1}@veth{1}".format(node_config["id"], port_nr)

            container_threads.append(
                threading.Thread(
                    target=self.thread_setup_node,
                    args=(node_container, node_command),
                    daemon=True,
                )
            )

        for switch in self.switches:
            switch_config = self.network_config[KEY_SWITCHES][switch.name]
            server_port = switch_config[KEY_SERVER_PORT]
            command_list = [
                "rm -rf /bf-sde/install/share/ /bf-sde/build/p4-build",
                "cp -r /app/share /bf-sde/install/share",
                "cp -r /app/p4-build /bf-sde/build/p4-build",
                f"/bf-sde/run_tofino_model.sh -p {switch_config[KEY_P4_PROG_NAME]} -f /app/ports.json --log-dir /app &",
            ]

            command_list.append(
                f"/bf-sde/run_switchd.sh -p {switch_config[KEY_P4_PROG_NAME]} -r /app/log_driver.txt -- --p4rt-server 0.0.0.0:{server_port}"
            )

            # if not "p4_info_path" in switch_config:
            #     logging.ERROR("No path defined for P4 info file. Cant setup switch")
            #     raise Exception("No path defined for P4 info file. Cant setup switch")

            # if not os.path.exists(switch_config["p4_info_path"]):
            #     path = switch_config["p4_info_path"]
            #     logging.error(f"P4 info file not found.{path} doesnt exist")
            #     raise Exception(f"P4 info file not found.{path} doesnt exist")

            container_threads.append(
                threading.Thread(
                    target=self.thread_setup_switch,
                    args=(switch, command_list, switch_config),
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

    def thread_setup_switch(self, switch_container, switch_command_list, switch_conf):
        """
        Sets up a switch. Ment to be ran in a thread.
        """
        ns = NetNS(switch_container.name)

        # Check if some interface failed to start
        while len(ns.link_lookup(IFLA_OPERSTATE="DOWN")) != 0:
            self.set_link_state(ns, "UP", ns.link_lookup(IFLA_OPERSTATE="DOWN"))
            time.sleep(1)

        for command in switch_command_list:
            switch_container.exec_run(command, detach=True)

        switch_server_port = switch_conf[KEY_SERVER_PORT]

        switch_con = SwitchConnection(
            switch_container.name, f"127.0.0.1:{switch_server_port}", 0, (0, 1)
        )
        self.switch_connections.append(switch_con)

        # Wait for switch to setup
        logging.info(f"Waiting for {switch_container.name} to start")

        switch_con.wait_for_setup(timeout=120)

        if not switch_con.connected and not switch_con.do_shutdown:
            logging.debug(
                f"Failed to establish connection to switch {switch_container.name}"
            )
            raise Exception("Switch error: Failed to connect to switch")

        logging.info(f"{switch_container.name} started!")

        self.nr_of_active_containers.increment()

        # TODO Read file path automatic
        P4_INFO_PATH = switch_conf["p4_info_path"]
        # BIN_PATH = "/home/p4/P4_Runtime/out.bin"
        BIN_PATH = "/home/p4/installations/p4runtime-shell/out.bin"

        p4_helper = P4InfoHelper(switch_conf["p4_info_path"])
        msg = switch_con.SetForwadingPipelineConfig2(P4_INFO_PATH, BIN_PATH)

        if "table_entries" in self.network_config[KEY_SWITCHES][switch_container.name]:
            for table_entry_info in self.network_config[KEY_SWITCHES][
                switch_container.name
            ]["table_entries"]:
                table_entry = p4_helper.build_table_entry(
                    table_entry_info["table_name"],
                    match_fields=table_entry_info["match_fields"],
                    action_name=table_entry_info["action_name"],
                    action_params=table_entry_info["action_params"],
                )
                if switch_con.connected:
                    switch_con.write_table_entry(table_entry)

        self.nr_of_active_containers.increment()

    def thread_setup_node(self, node_container, node_command):
        node_container.exec_run(node_command, detach=True)
        self.nr_of_active_containers.increment()

    def update_network_config(self, network_config_path):
        with open(network_config_path) as json_file:
            network_config = json.load(json_file)

        if self.is_same_base_setup(self.network_config, network_config):
            for switch_name in network_config[KEY_SWITCHES]:
                switch_conf = network_config[KEY_SWITCHES][switch_name]
                p4_info_helper = P4InfoHelper(switch_conf[KEY_P4_INFO_PATH])
                switch_con = self.get_switch_connection(switch_name)
                for table_entry_info in switch_conf[KEY_TABLE_ENTRIES]:
                    # TODO Read file path automatic
                    # BIN_PATH = "/home/p4/P4_Runtime/out.bin"
                    BIN_PATH = "/home/p4/installations/p4runtime-shell/out.bin"

                    msg = switch_con.SetForwadingPipelineConfig2(
                        switch_conf[KEY_P4_INFO_PATH], BIN_PATH
                    )

                    table_entry2 = p4_info_helper.build_table_entry(
                        table_entry_info["table_name"],
                        match_fields=table_entry_info["match_fields"],
                        action_name=table_entry_info["action_name"],
                        action_params=table_entry_info["action_params"],
                    )

                    table_entry = p4_info_helper.build_table_entry(
                        table_name="Ingress.ipv4_lpm",
                        match_fields={"hdr.ipv4.dst_addr": ["10.0.2.2", 32]},
                        action_name="Ingress.ipv4_forward",
                        action_params={"egress_port": 1},
                    )

                    if switch_con.connected:
                        switch_con.write_table_entry(table_entry2)

            # if "table_entries" in network_config[KEY_SWITCHES][switch_name]:
            #     for table_entry_info in self.network_config[KEY_SWITCHES][switch_name][
            #         "table_entries"
            #     ]:
            #         table_entry2 = p4_info_helper.build_table_entry(
            #             table_entry_info["table_name"],
            #             match_fields=table_entry_info["match_fields"],
            #             action_name=table_entry_info["action_name"],
            #             action_params=table_entry_info["action_params"],
            #         )

            #     table_entry = p4_info_helper.build_table_entry(
            #         table_name="Ingress.ipv4_lpm",
            #         match_fields={"hdr.ipv4.dst_addr": ["10.10.4.4", 16]},
            #         action_name="Ingress.ipv4_forward",
            #         action_params={"egress_port": 3},
            #     )
            #     if switch_con.connected:
            #         switch_con.write_table_entry(table_entry)
        else:
            self.close()

            # Update network
            self.network_config = network_config
            self.create_docker_containers()
            self.setup_network()
            self.connect_nodes_to_switch()
            self.start_container_listening_tofino()

    def is_same_base_setup(self, conf1: dict, conff2: dict) -> bool:
        """
        Compares two network files to check if the all the nodes, switches and links are the same.
        If they are, no need remove and create new ones.

        Args:
            conf1 (dict): Path to the active network configuration
            conff2 (dict): Path to new network configuration

        Returns:
            bool:
        """
        setup_is_same = True

        # Check Nodes, Links and Switches
        for link in conff2[KEY_LINKS]:
            if not link in conf1[KEY_LINKS]:
                setup_is_same = False

        for node in conff2[KEY_NODES]:
            if not node in conf1[KEY_NODES]:
                setup_is_same = False

        active_switches = conf1["switches"].keys()
        for switch_name in conff2[KEY_SWITCHES]:

            if not switch_name in active_switches:
                setup_is_same = False
            else:
                switch = conff2[KEY_SWITCHES][switch_name]
                switch_active = conf1[KEY_SWITCHES][switch_name]
                if (
                    not switch[KEY_P4_INFO_PATH] == switch_active[KEY_P4_INFO_PATH]
                    or not switch[KEY_P4_PROG_NAME] == switch_active[KEY_P4_PROG_NAME]
                    or not switch[KEY_SERVER_PORT] == switch_active[KEY_SERVER_PORT]
                ):
                    setup_is_same = False

        return setup_is_same

    def create_tofino_switch_mount_copy(self, switch_name):
        switch_path = f"{self.tmp_folder}/{switch_name}"
        if os.path.exists(switch_path):
            shutil.rmtree(switch_path)

        os.mkdir(switch_path)

        # Share and and p4-build contains files for running the switch
        if not os.path.exists(f"{SDE_INSTALL}/share"):
            logging.debug(f"Could not find path: {SDE_INSTALL}/share")

        if not os.path.exists(f"{SDE_INSTALL}/build/p4-build"):
            logging.debug(f"Could not find path: {SDE}/build/p4-build")

        shutil.copytree(
            f"{SDE_INSTALL}/share",
            f"{switch_path}/share",
        )

        shutil.copytree(
            f"{SDE}/build/p4-build",
            f"{switch_path}/build/p4-build",
        )

        self.create_port_config(
            self.network_config[KEY_SWITCHES][switch_name],
            f"{switch_path}/ports.json",
        )

        return switch_path
        # Copy shared bf-sde folder which holds info about compiled program

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
        Simple check of the network file
        """
        if not self.network_config:
            logging.debug("No network file is defined for validation")
            return False
        else:
            # Check nodes
            if (
                "nodes" not in self.network_config
                or len(self.network_config["nodes"]) == 0
            ):
                logging.debug("No nodes defined in network config")
                return False

            # Check for duplicate node names TODO Check duplicate ids
            node_names = list(self.network_config["nodes"].keys())

            for node_name in node_names:
                if node_names.count(node_name) > 1:
                    logging.debug("Duplicate node name detected")
                    return False

            # Check switches
            if (
                KEY_SWITCHES not in self.network_config
                or len(self.network_config[KEY_SWITCHES]) < 1
            ):
                logging.debug("No switches defined")
                return False

            switch_names = list(self.network_config[KEY_SWITCHES].keys())

            for switch_name in switch_names:
                if switch_names.count(switch_name) > 1:
                    logging.debug("Duplicate switch name detected")
                    return False

            # Check links
            if "links" in self.network_config:
                all_devices = switch_names + node_names

                for link in self.network_config["links"]:
                    if (
                        not link["device1"] in all_devices
                        or not link["device2"] in all_devices
                    ):
                        logging.debug("Link between none defined devices detected")
                        return False
                    if (
                        not type(link["device1_port"]) == int
                        or not type(link["device2_port"]) == int
                    ):
                        return False

        return True

    def is_switch_setup(self, switch_name, port_nr):
        switch_path = f"{self.tmp_folder}/{switch_name}"

        logging.info(switch_path)
        files = os.listdir(switch_path)
        log_file_path = ""

        logging.info(files)

        time.sleep(30)

        for file in files:
            if "driver" in file:
                log_file_path = switch_path + f"/{file}"

        while True:
            if log_file_path:
                logging.info(log_file_path)
                with open(log_file_path, "r") as log_file:
                    if str(port_nr) in log_file.read():
                        return True

            files = os.listdir(switch_path)
            for file in files:
                if "driver" in file:
                    log_file_path = switch_path + f"/{file}"

            time.sleep(1)

    def run_network_conf_path(self, run):
        """
        Returns the most specific network config from the setup file. The order is:
        1. Run option
        2. Rundefinition option
        3 Global option

        Args:
            run ([Run]): Run to inspect
            run_net_configs(dict): Network config for specific runs
        Returns:
            string: Path to the network config file
        """

        # Get most exclusive ptf folder path
        i = 0
        ptf_folder_index = 0
        for option in run.options:
            if option == KEY_PTF_FOLDER_PATH:
                ptf_folder_index = i + 1
            i += 1

        test_configs = find_test_network_configs(
            self.extract_path(run.options[ptf_folder_index])
        )

        # Check if test a defined net conf file
        if run.identifier in test_configs:
            return test_configs[run.identifier]

        net_con_index = 0
        i = 0
        for option in run.options:
            if option == KEY_NETWORK_CONFIG:
                net_con_index = i + 1
            i += 1

        return run.options[net_con_index]

    def get_switch_connection(self, switch_name):
        for con in self.switch_connections:
            if con.switch_name == switch_name:
                return con
        return None

    def read_ptf_folder_paths(self, benchmark) -> list:
        """
        Goes through the benchmark and returns all unique ptf test folder paths.
        """
        folder_paths = []

        for run_set in benchmark.run_sets:
            for run in run_set.runs:
                i = 0
                for option in run.options:
                    if option == KEY_PTF_FOLDER_PATH:
                        if not run.options[i + 1] in folder_paths:
                            folder_paths.append(run.options[i + 1])
                    i += 1

        i = 0
        for path in folder_paths:
            folder_paths[i] = self.extract_path(path)
            i += 1

        return folder_paths
