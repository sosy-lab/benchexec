#!/bin/sh

set -e

for cgroups in $(cut -d : -f 3 /proc/self/cgroup | sort -u); do
  for path in /sys/fs/cgroup/*/"$cgroups"; do
    echo Running "$@" "$path"
    "$@" "$path"
  done
done
