<!-- PDX-FileCopyrightText: 2020-2021 CASTOR Software Research Centre
<https://www.castor.kth.se/>
SPDX-FileCopyrightText: 2020-2021 Johan Paulsson

SPDX-License-Identifier: Apache-2.0 -->

# P4 Extension for Benchexec
This extension allows Benchexec to be used to analyze P4 programs for programmable switches. The user can alter the way the test should
be executed by providing different input files to define the test.

## Installation

### Dependencies
#### Docker Engine
To install docker, follow the instruction on [dockers website](https://docs.docker.com/engine/install/)

On ubuntu, one can execute these commands to install the latest version of docker.
```
sudo apt-get update
sudo apt-get install \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo \
  "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io
```

Also install the required python modules,

```
sudo pip3 install docker
sudo pip3 install pyroute2
```

### Benchexec installation

To install benchexecute with p4 extensions follow these steps. First clone the repository and then install with pip. 

```
git clone https://github.com/thaprau/benchexec.git
sudo pip3 install .
```

### Dockerfile setup
To set up the required docker files, some images have to be created locally. In total, three images have to be built.
1. Node image - basic image which acts as a node in the network
2. Switch image - Image that runs the bmv2 software provided by the p4 institution
3. Ptf tester image - Image that runs PTF(package test framework) also provided by p4 institution

To build the images, run the following commands:

```
cd contrib/p4/docker_files
sudo docker build -t basic_node basic_node
sudo docker build -t switch_bmv2 switch_bmv2
sudo docker build -t ptf_tester ptf_tester
```

## Setup

To run benchexec with p4, there are a few requirements. The first one is to create a benchmark file. The structure of the benchmark file is the same as the regular benchexec, but with 3 extra option tags. The tags are:

1.    Path to ptf test folder. Format: <option name="switch_folder">path/to/switch_folder</option>
2.    Path to switch folder. Format <option name="ptf_test_folder">path/to/ptf_test_folder</option>
3.    Path to network configuration file <option name="network_config">path/tp/network_config_file</option>

### Switch folder layout
The switch folder `contrib/p4/docker_files/switch_bmv2` contains 3 folders, log, P4 and tables.

1. Log - used by the program
2. P4 - This is where the switch expect to find the setup file
3. tables - This is where the switch will look for the defined table entries

### Writing test for the switch
The program utilizes PTF to create and handle tests. To write your own test, one can look the examples in this repository(`contrib/p4/docker_files/ptf_tester/tests`) or the [PTF documentation](https://github.com/p4lang/ptf)

Finally, the user can define expected results for the test run. If the task is run with the include tag (can be replaced with the withoutfile tag), the user can include an expected results json file. An example of such a file is in `/doc/task_files_expected_results.json`. The format of the file is Modulename.testname. If no modules are defined, the module name is the file name. The test name is the name of the test. For more info, look at [PTF documentation](https://github.com/p4lang/ptf).

A complete example of the xml file is in `contrib/p4/test_unput/simpleP4Test.XML`. The given example uses a pre-compiled json file for the switch. (Replace with the p4 file to be executed)The switch is a simple ipv4 forward switch from the p4 tutorial. The file also refers to a network configuration file which sets up the configuration as the picture below. Finally, it refers to some simple ipv4 forwarding test.


### Network configuration file

The network configuration file is what defines the test setup. To create such a file, the easiest way is to use the python API. On how to use the API, see the README of that [repository](https://github.com/thaprau/p4_bench_api).

## Execution

To run the program, execute the p4-benchmark.py file located in `/contrib`. An example would be:

```
sudo python3 contrib/p4-benchmark.py contrib/p4/test_input/simpleP4Test.XML
```



