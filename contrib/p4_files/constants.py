from enum import Enum

# Dict Keys
KEY_NODES = "nodes"
KEY_SWITCHES = "switches"
KEY_SERVER_PORT = "server_port"
KEY_TABLE_ENTRIES = "table_entries"
KEY_P4_INFO_PATH = "p4_info_path"
KEY_P4_PROG_NAME = "p4_prog_name"

# Global variables
NODE_IMAGE_NAME = "basic_node"  # Should match name of the container name
SWITCH_IMAGE_NAME = "switch_sdk_9.5.0"
PTF_IMAGE_NAME = "ptf_tester"

SDE = "/home/p4/installations/bf-sde-9.5.0"
SDE_INSTALL = f"{SDE}/install"

# Container values
CONTAINTER_BASE_DIR = "/app"

# Setup files keys
KEY_NETWORK_CONFIG = "network_config"
KEY_PTF_FOLDER_PATH = "ptf_test_folder"
KEY_LINKS = "links"
