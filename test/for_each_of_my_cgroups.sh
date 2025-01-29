#!/bin/sh

# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

set -e

for cgroups in $(cut -d : -f 3 /proc/self/cgroup | sort -u); do
  for path in /sys/fs/cgroup/*/"$cgroups"; do
    echo Running "$@" "$path"
    "$@" "$path"
  done
done
