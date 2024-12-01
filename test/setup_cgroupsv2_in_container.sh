#!/bin/sh

# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2024 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

# This script can be run inside a container to prepare cgroups for BenchExec.
# If parameters are passed, it will execute them afterwards.

set -eu

# Create new sub-cgroups
# Note: While "init" can be renamed, the name "benchexec" is important
mkdir -p /sys/fs/cgroup/init /sys/fs/cgroup/benchexec
# Move all processes to that cgroup
while read pid; do
  echo $pid > /sys/fs/cgroup/init/cgroup.procs
done < /sys/fs/cgroup/cgroup.procs

# Enable controllers in subtrees for benchexec to use
for controller in $(cat /sys/fs/cgroup/cgroup.controllers); do
  echo "+$controller" > /sys/fs/cgroup/cgroup.subtree_control
  echo "+$controller" > /sys/fs/cgroup/benchexec/cgroup.subtree_control
done

if [ ! -z "${1:-}" ]; then
  exec "$@"
fi
