FROM ubuntu:22.04

# Install BenchExec dependencies
RUN apt-get update && apt-get install -y \
    software-properties-common \
    sudo \
    python3 \
    python3-pip \
    && add-apt-repository ppa:sosy-lab/benchmarking \
    && apt-get update \
    && apt-get install -y benchexec

WORKDIR /workspace

