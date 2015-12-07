# BenchExec: Setup

## Download and Installation

BenchExec requires at least Python 3.2.
(Then [runexec](runexec.md) tool and module also work with Python 2.7.)
Thus, make sure to use Python 3 for installation as described below,
otherwise only `runexec` will get installed.

To install BenchExec we recommend to use the Python package installer pip
(installable for example with `sudo apt-get install pip3` on Debian/Ubuntu).

To automatically download and install the latest stable version and its dependencies
from the [Python Packaging Index](https://pypi.python.org/pypi/BenchExec),
run this command:

    sudo pip3 install benchexec

Users of Debian and related distributions like Ubuntu can also download
a Debian package from [GitHub](https://github.com/sosy-lab/benchexec/releases)
and install it with `dpkg -i` (after installing the package `python3-tempita`).

You can also install BenchExec only for your user with

    pip3 install --user benchexec

In this case you probably need to add the directory where pip installs the commands
to the PATH environment by adding the following line to your `~/.profile` file:

    export PATH=~/.local/bin:$PATH

Of course you can also install BenchExec in a virtualenv if you are familiar with Python tools.

To install the latest development version from the
[GitHub repository](https://github.com/sosy-lab/benchexec), run this command:

    pip3 install --user git+https://github.com/sosy-lab/benchexec.git

If you want to run benchmarks under different user account than your own,
please check the [respective documentation](separate-user.md) for how to setup sudo.


## System Requirements

To execute benchmarks and reliably measure and limit their resource consumption,
BenchExec requires that the user which executes the benchmarks
can create and modify cgroups.

Any Linux kernel version of the last years is
acceptable, though there have been performance improvements for the memory
controller in version 3.3, and cgroups in general are still getting improved, thus,
using a recent kernel is a good idea.

### Note for Users of Ubuntu 14.04

There are appears to be a problem in the Linux kernel 3.13 used by Ubuntu 14.04.
On some machines the kernel sporadically crashes
with the message `BUG: soft lockup` in `/var/log/kern.org`
and needs to be rebooted
when the benchmarked process hits its memory limit.

If you are affected by this problem, please upgrade to kernel 3.16 or newer, which is not affected,
using the officially supported
[Ubuntu LTS Hardware Enablement Stack](https://wiki.ubuntu.com/Kernel/LTSEnablementStack).


## Setting up Cgroups

The cgroup virtual file system is typically mounted at `/sys/fs/cgroup`.
If it is not, you can mount it with

    sudo mount -t cgroup cgroup /sys/fs/cgroup

To give all users on the system the ability to create their own cgroups,
you can use

    sudo chmod o+wt,g+w /sys/fs/cgroup/

Of course permissions can also be assigned in a more fine-grained way if necessary.

Alternatively, software such as `cgrulesengd` from
the [cgroup-bin](http://libcg.sourceforge.net/) package
can be used to setup the cgroups hierarchy.

Note that `cgrulesengd` might interfere with the cgroups of processes,
if configured to do so via `cgrules.conf`.
This can invalidate the measurements.
BenchExec will try to prevent such interference automatically,
but for this it needs write access to `/run/cgred.socket`.

If your machine has swap, cgroups should be configured to also track swap memory.
If the file `memory.memsw.usage_in_bytes` does not exist in the directory
where the cgroup file system is mounted, this needs to be enabled by setting
`swapaccount=1` on the command line of the kernel.
To do so, you typically need to edit your bootloader configuration
(under Ubuntu for example in `/etc/default/grub`, line `GRUB_CMDLINE_LINUX`),
update the bootloader (`sudo update-grub`), and reboot.

All the above requirements can be checked easily by running

    python3 -m benchexec.check_cgroups

after BenchExec has been installed.
It will report warnings and exit with code 1 if something is missing.
We recommend running this check to ensure benchmarks will get executed reliably.

It may be that your Linux distribution already mounts the cgroup file system
and creates a cgroup hierarchy for you.
In this case you need to adjust the above commands appropriately.
To optimally use BenchExec,
the cgroup controllers `cpuacct`, `cpuset`, `freezer`, and `memory`
should be mounted and usable,
i.e., they should be listed in `/proc/self/cgroups` and the current user
should have at least the permission to create sub-cgroups of the current cgroup(s)
listed in this file for these controllers.

### Setting up Cgroups on Systems with systemd

This affects most users of Debian >= 8, Fedora >= 15, Redhat >= 7, Suse SLES >= 12, Ubuntu >= 15.04,
and potentially other distributions.
systemd makes extensive usage of cgroups and [claims that it should be the only process that accesses cgroups directly](https://wiki.freedesktop.org/www/Software/systemd/ControlGroupInterface/).
Thus it may interfere with the cgroups usage of BenchExec.

By using a fake service we can let systemd create an appropriate cgroup for BenchExec
and prevent interference.
The following steps are necessary:

 * Add `JoinControllers=cpuset,cpuacct,memory,freezer` to `/etc/systemd/system.conf`
   to ensure systemd creates a cgroup for all of these controllers for us.
   This setting needs a reboot to take effect,
   and [potentially a regeneration of your initramdisk](http://www.freedesktop.org/software/systemd/man/systemd-system.conf.html#Options).

 * Put the following into a file `/usr/local/sbin/benchexec-cgroup.sh`.
   By default, this gives permissions to use the BenchExec cgroup
   to users of the group `benchexec`, please adjust this as necessary.
   Do not forget to make the file executable.
```
#!/bin/bash
# Fill in set of allowed CPUs and memory regions (default is empty).
cp /sys/fs/cgroup/cpuset/cpuset.cpus /sys/fs/cgroup/cpuset/system.slice/
cp /sys/fs/cgroup/cpuset/cpuset.mems /sys/fs/cgroup/cpuset/system.slice/
cp /sys/fs/cgroup/cpuset/cpuset.cpus /sys/fs/cgroup/cpuset/system.slice/benchexec-cgroup.service/
cp /sys/fs/cgroup/cpuset/cpuset.mems /sys/fs/cgroup/cpuset/system.slice/benchexec-cgroup.service/

echo $$ > /sys/fs/cgroup/cpuset/system.slice/benchexec-cgroup.service/tasks

# Adjust permissions of cgroup (change as appropriate for you).
chgrp -vR benchexec /sys/fs/cgroup/*/system.slice/benchexec-cgroup.service/
chmod -vR g+w /sys/fs/cgroup/*/system.slice/benchexec-cgroup.service/

# Sleep for 10 years.
exec sleep $(( 10 * 365 * 24 * 3600 ))
```

 * Put the following into a file `/etc/systemd/system/benchexec-cgroup.service`
   and enable the service with `systemctl daemon-reload; systemctl enable benchexec-cgroup; systemctl start benchexec-cgroup`:
```
[Unit]
Description=Cgroup for BenchExec
Documentation=https://github.com/sosy-lab/benchexec/blob/master/doc/INSTALL.md
Documentation=https://github.com/sosy-lab/benchexec/blob/master/doc/INDEX.md

[Service]
Type=simple
ExecStart=/usr/local/sbin/benchexec-cgroup.sh
Restart=always
Delegate=true
CPUAccounting=true
MemoryAccounting=true

[Install]
WantedBy=multi-user.target
```

Before running BenchExec, you now need to ensure it runs in the correct cgroup
by executing the following commands once per terminal session:
```
echo $$ > /sys/fs/cgroup/cpuset/system.slice/benchexec-cgroup.service/tasks
echo $$ > /sys/fs/cgroup/cpuacct/system.slice/benchexec-cgroup.service/tasks
echo $$ > /sys/fs/cgroup/memory/system.slice/benchexec-cgroup.service/tasks
echo $$ > /sys/fs/cgroup/freezer/system.slice/benchexec-cgroup.service/tasks
```

Please check the correct cgroup setup with `python3 -m benchexec.check_cgroups` as described above.

Note that using systemd with BenchExec is still experimental.
Please report back your experience and whether you have found a better solution than the above.


### Setting up Cgroups in a Docker container

If you want to run benchmarks within a Docker container,
please use the following command line argument
to mount the cgroup hierarchy within the container when starting it:

    docker run -v /sys/fs/cgroup:/sys/fs/cgroup:rw ...


## Installation for Development

Please refer to the [development instructions](DEVELOPMENT.md).
