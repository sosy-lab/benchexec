# P4 Extension for Benchexec

## Installation


### Dependencies

#### Docker Engine
To install docker, follow the instruction on [dockers website](https://docs.docker.com/engine/install/)

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

To build the images, run the following commands or use the setup script provided in `/docker_files`.

```
cd contrib/p4/docker_files
sudo docker build -t basic_node basic_node
sudo docker build -t switch_bmv2 switch_bmv2
sudo docker build -t ptf_tester ptf_tester
```

## Execution

To run benchexec with p4, the first thing that is necessary is to create an benchmark file. The benchmark file is the same as
the regular benchexec, but requires two extra option tags. The option tags define the path to the test folder for 
ptf and the folder which holds the .JSON file that the bsmv2 switch should consume. Furthermore, if the task is run with the include tag(can be replaced with withoutfile tag), the user can include a expected results json file. An example of such a file is located in `/doc/task_files/expected_results.json`. The format is Modulename.testname. If no modules are defined, the module name is the file name. The test name is the name of the test.

A complete examlpe of the xml file is located in `/doc/simpleP4Test.XML`. The given example uses a pre-compiled .json file for the switch. The switch is a basic ipv4 switch, which forwards packets based on ip address. Furthermore, the file refers to a ptf test file folder with some simple tests.

To run benchexec with p4 extension. Execute the python file located in the /contrib folder. An example would be:
```
sudo python3 contrib/p4-benchexec.py doc/simpleP4Test.XML
```

## Program definition
The program can only setup a single type of network. It creates 4 nodes all connected to 1 switch. Each node gets assigned a device number and and ip address. How the numbers are set is as follows. The first Node is called Node1 and is device nr 0. Next Node is called Node2 and device nr 1. The given ip address for each node is 192.168.1.{node nr}.
So the first node would get 192.168.1.1.

The switch tries to load in the ipv4 address table into the switch. It used the file `ip_table.json`. If you use a different table name, update the table name in the file.

