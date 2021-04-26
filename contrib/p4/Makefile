# SPDX-FileCopyrightText: 2020-2021 CASTOR Software Research Centre
# <https://www.castor.kth.se/>
# SPDX-FileCopyrightText: 2020-2021 Johan Paulsson

# SPDX-License-Identifier: Apache-2.0

@NOW = $(shell date)
namespaces = $(shell ls /var/run/netns/)
containers = $(shell docker ps -a -q)
interfaces = $(shell ls /sys/class/net/ | grep -m1 Node)

make clean:
ifneq ("$(namespaces)", "")
	sudo rm /var/run/netns/*
endif

ifneq ("$(containers)", "")
	docker rm -f $(containers)
endif

ifneq ("$(interfaces)", "")
	sudo ip link delete $(interfaces)
endif

make run:
	sudo python3 -m pdb ../p4-benchmark.py ../../doc/simpleP4Test.XML
