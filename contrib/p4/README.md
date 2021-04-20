# P4 Extension for Benchexec

## Installation


### Dependencies

Pyroute2 python package is required to handle network setup. Install via:
```
sudo pip3 install pyroute2
```

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

Also install the extension for docker to be excecuted through python:

```
sudo pip3 install docker
```

### Benchexec installation

To install benchexecute with p4 extensions follow these steps. First clone the repository, switch to correct
branch and install the application:

```
git clone https://github.com/thaprau/benchexec.git
cd benchexec
git checkout bench_p4
pip3 install .
```

### Docker file setup
To setup the required docker files, some images has to be created locally. In total, three images has to be built.
1. Node image - basic image which acts as a node in the network
2. Switch image - Image that runs the bmv2 software provided by the p4 institution
3. Ptf tester image - Image that runs PTF(package test framwork) also provided by p4 institution

To build the images, run the following commands:

```
cd contrib/p4/docker_files
sudo docker build -t basic_node basic_node
sudo docker build -t switch_bmv2 switch_bmv2
sudo docker build -t ptf_tester ptf_tester
```

## Setup

To run benchexec with p4, there are a few requirements. The first one is to create a benchmark file. The structure of the benchmark file is the same as the regular benchexec, but with 3 extra option tags. The tags are:


1.	Path to ptf test folder. Format: <option name="switch_folder">path/to/switch_folder</option>
2.	Path to switch folder. Format <option name="ptf_test_folder">path/to/ptf_test_folder</option>
3.	Path to network configuration file <option name="network_config">path/tp/network_config_file<option/>

Finally, the user can define expected results for the test run. If the task is run with the include tag (can be replaced with the withoutfile tag), the user can include an expected results json file. An example of such a file is in `/doc/task_files_expected_results.json`. The format of the file is Modulename.testname. If no modules are defined, the module name is the file name. The test name is the name of the test.

A complete example of the xml file is in `/doc/simpleP4Test.XML`. The given example uses a pre-compiled json file for the switch. The switch is a simple ipv4 forward switch from the p4 tutorial. The file also refers to a network configuration file which sets up the configuration as the picture below. Finally, it refers to some simple ipv4 forwarding test.


### Network configuration file

The network configuration file is what defines the test setup. To create such a file, the easiest way is to use the python API. On how to use the API, see the README of that repository.

## Execution

To run the program, execute the p4-benchmark.py file located in `/contrib`. An example would be:

```
sudo python3 contrib/p4-benchmark.py doc/simpleP4.XML
```
