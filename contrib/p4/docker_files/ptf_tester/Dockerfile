# SPDX-FileCopyrightText: 2020-2021 CASTOR Software Research Centre
# <https://www.castor.kth.se/>
# SPDX-FileCopyrightText: 2020-2021 Johan Paulsson

# SPDX-License-Identifier: Apache-2.0

#This dockerfile defines the container responisble for executing the tests.
#It uses the ptf test framework to do so

FROM ubuntu:18.04

RUN apt-get update
RUN apt-get install -y python3
RUN apt-get install -y python3-pip

RUN apt-get install -y libnanomsg-dev
RUN pip3 install nnpy
RUN apt-get install -y git
RUN apt install -y iproute2
RUN apt-get install -y iputils-ping
RUN pip3 install scapy

#PTF install
RUN git clone https://github.com/p4lang/ptf /usr/local/src/ptf

RUN cd /usr/local/src/ptf && pip3 install .

CMD tail -f /dev/null


