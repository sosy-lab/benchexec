#!/bin/sh
set -e

echo ------------------------
echo "Existing mount points:"
mount
echo ------------------------
echo "Existing users:"
getent passwd
echo ------------------------

PRIMARY_USER="$1"

# Set up cgroups
for i in blkio cpuacct cpuset freezer memory cpu; do
  if [ ! -d "/sys/fs/cgroup/$i" ]; then
    mkdir /sys/fs/cgroup/$i
    mount cgroup-$i /sys/fs/cgroup/$i -t cgroup -o $i
  fi
  chgrp "$(id -g "$PRIMARY_USER")" /sys/fs/cgroup/$i
  chmod g+rwx /sys/fs/cgroup/$i
done
