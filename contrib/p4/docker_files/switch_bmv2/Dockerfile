# SPDX-FileCopyrightText: 2020-2021 CASTOR Software Research Centre
# <https://www.castor.kth.se/>
# SPDX-FileCopyrightText: 2020-2021 Johan Paulsson

# SPDX-License-Identifier: Apache-2.0

#Container for using bmv2 open source switch. See ref https://github.com/p4lang/behavioral-model
#It is capable of loading a compiled bmv2 json file

FROM ubuntu:16.04

RUN apt-get update && apt-get install -y \
    automake \
    cmake \
    libjudy-dev \
    libgmp-dev \
    libpcap-dev \
    libboost-dev \
    libboost-test-dev \
    libboost-program-options-dev \
    libboost-system-dev \
    libboost-filesystem-dev \
    libboost-thread-dev \
    libevent-dev \
    libtool \
    flex \
    bison \
    pkg-config \
    g++ \
    libssl-dev \
    libffi-dev \
    python3-dev \
    python3-pip \
    wget \
    git \
    sudo \
    && rm -rf /var/lib/apt/list/*

RUN git clone https://github.com/p4lang/behavioral-model.git /usr/local/behavioral-model
RUN cd /usr/local/behavioral-model/travis && sudo chmod +x install-thrift.sh install-nanomsg.sh install-nnpy.sh


#Instead of install_deps.sh
RUN mkdir tempdir
RUN cd tempdir && sudo /usr/local/behavioral-model/travis/install-thrift.sh
RUN cd tempdir && /usr/local/behavioral-model/travis/install-nanomsg.sh
RUN cd tempdir && /usr/local/behavioral-model/travis/install-nnpy.sh

RUN rm -rf tempdir

RUN cd /usr/local/behavioral-model/ && ./autogen.sh
RUN /usr/local/behavioral-model/configure
RUN make
RUN make install
RUN cd /usr/local/behavioral-model/ && ldconfig

CMD tail -f /dev/null
