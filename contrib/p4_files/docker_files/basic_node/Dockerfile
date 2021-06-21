# SPDX-FileCopyrightText: 2020-2021 CASTOR Software Research Centre
# <https://www.castor.kth.se/>
# SPDX-FileCopyrightText: 2020-2021 Johan Paulsson

# SPDX-License-Identifier: Apache-2.0

#This dockerfile represents a single node/client in a network.
#It uses the example from https://github.com/p4lang/ptf/ptf_nn
#to listen and forward packages

FROM ubuntu:18.04

# Packages
RUN apt-get update
RUN apt-get install -y sudo
RUN apt-get install -y iproute2
RUN apt-get install -y net-tools
RUN apt-get install -y iputils-ping
RUN apt-get install -y tcpdump
RUN apt-get install -y git
RUN apt-get install -y libnanomsg-dev
RUN apt-get install -y python3
RUN apt-get install -y python3-pip
RUN pip3 install rpyc
RUN pip3 install netifaces
RUN pip3 install nnpy
RUN git clone https://github.com/p4lang/ptf /usr/local/src/ptf
RUN cd /usr/local/src/ptf && pip3 install .

CMD tail -f /dev/null
