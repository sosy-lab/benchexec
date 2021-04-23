<!--
This file is part of BenchExec, a framework for reliable benchmarking:
https://github.com/sosy-lab/benchexec

SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>

SPDX-License-Identifier: Apache-2.0
-->

# BenchExec: Setup

## Download and Installation

### Requirements

- Python 3.6 or newer
- Linux (cf. [Kernel Requirements](#kernel-requirements) below for details)
- x86 or ARM machine (please [contact us](https://github.com/sosy-lab/benchexec/issues/new) for other architectures)

The following packages are optional but recommended dependencies:
- [cpu-energy-meter] will let BenchExec measure energy consumption on Intel CPUs.
- [libseccomp2] provides better container isolation.
- [LXCFS] provides better container isolation.
- [coloredlogs] provides nicer log output.
- [pqos_wrapper] and [pqos library][pqos]
  provide isolation of L3 cache and measurement of cache usage and memory bandwidth
  (only in `benchexec`).

Note that the `table-generator` utility requires only Python and works on all platforms.

### Debian/Ubuntu

For installing BenchExec on Debian or Ubuntu we recommend installing from our [PPA](https://launchpad.net/~sosy-lab/+archive/ubuntu/benchmarking):

    sudo add-apt-repository ppa:sosy-lab/benchmarking
    sudo apt install benchexec

Alternatively, you can download our `.deb` package from [GitHub](https://github.com/sosy-lab/benchexec/releases)
and install manually (note that the leading `./` is important, otherwise `apt` will not find the package):

    apt install --install-recommends ./benchexec_*.deb

Our package automatically configures the necessary cgroup permissions.
Just add the users that should be able to use BenchExec to the group `benchexec`
(group membership will be effective after the next login of the respective user):

    adduser <USER> benchexec

Afterwards, please check whether everything works
or whether additional settings are necessary as [described below](#testing-cgroups-setup-and-known-problems).

Note that [pqos_wrapper] is currently not available as a Debian package
and needs to be installed manually according to its documentation.

### Other Distributions

For other distributions we recommend to use the Python package installer pip.
To automatically download and install the latest stable version and its dependencies
from the [Python Packaging Index](https://pypi.python.org/pypi/BenchExec) with pip,
run this command:

    sudo pip3 install benchexec coloredlogs

You can also install BenchExec only for your user with

    pip3 install --user benchexec coloredlogs

In the latter case you probably need to add the directory where pip installs the commands
to the PATH environment by adding the following line to your `~/.profile` file:

    export PATH=~/.local/bin:$PATH

Of course you can also install BenchExec in a virtualenv if you are familiar with Python tools.

Please make sure to configure cgroups as [described below](#setting-up-cgroups)
and install [cpu-energy-meter], [libseccomp2], [LXCFS], and [pqos_wrapper] if desired.

### Development version

To install the latest development version from the
[GitHub repository](https://github.com/sosy-lab/benchexec), run this command:

    pip3 install --user git+https://github.com/sosy-lab/benchexec.git coloredlogs

It is useful to install the system package `python3-lxml` before,
otherwise pip will try to download and build this module,
which needs a compiler and several development header packages.

Please make sure to configure cgroups as [described below](#setting-up-cgroups)
and install [cpu-energy-meter], [libseccomp2], [LXCFS], and [pqos_wrapper] if desired.


## Kernel Requirements

To execute benchmarks and reliably measure and limit their resource consumption,
BenchExec requires that the user which executes the benchmarks
can create and modify cgroups (see below for how to allow this).

If you are using an Ubuntu version that is still supported,
everything else should work out of the box.
For other distributions, please read the following detailed requirements.

Except on Ubuntu, the full feature set of BenchExec is only usable
on **Linux 5.11 or newer**, so we suggest at least this kernel version.

On older kernels, you need to avoid using the overlay filesystem (cf. below),
all other features are supported.
However, we strongly recommend to use at least **Linux 4.14 or newer**
because it reduces the overhead of BenchExec's memory measurements and limits.
For even older kernel versions, please read
[our previous documentation](https://github.com/sosy-lab/benchexec/blob/e445f17/doc/INSTALL.md#kernel-requirements)
with more details.

Using BenchExec on kernels without NUMA support
is not guaranteed to work (but this is enabled by all common distributions).

In container mode (i.e., always except when using `--no-container`),
 BenchExec uses two main kernel features
that are not usable on all distributions by default:

- **User Namespaces**: This is available on most distros
  (the kernel option is `CONFIG_USER_NS`),
  but Debian and Arch Linux disable this feature for regular users,
  so the system administrator needs to enable it
  with `sudo sysctl -w kernel.unprivileged_userns_clone=1` or a respective entry
  in `/etc/sysctl.conf`.
  On CentOS it can be necessary to enable this feature with
  `sudo sysctl -w user.max_user_namespaces=10000` or a respective entry
  in `/etc/sysctl.conf` (the exact value is not important).

- **Unprivileged Overlay Filesystem**: This is only available since Linux 5.11
  (kernel option `CONFIG_OVERLAY_FS`),
  but also present in all Ubuntu kernels, even older ones.
  Users of older kernels on other distributions can still use container mode, but have to choose a different mode
  of mounting the file systems in the container, e.g., with `--read-only-dir /` (see below).

If container mode does not work, please check the [common problems](container.md#common-problems).


## Setting up Cgroups

If you have installed the Debian package and you are running systemd
(default since Debian 8 and Ubuntu 15.04),
the package should have configured everything automatically.
Just add your user to the group `benchexec` and reboot:

    adduser <USER> benchexec

### Setting up Cgroups on Machines with systemd

Most distributions today use systemd, and
systemd makes extensive usage of cgroups and [claims that it should be the only process that accesses cgroups directly](https://wiki.freedesktop.org/www/Software/systemd/ControlGroupInterface/).
Thus it would interfere with the cgroups usage of BenchExec.

By using a dummy service we can let systemd create an appropriate cgroup for BenchExec
and prevent interference.
The following steps are necessary:

 * Decide which set of users should get permissions for cgroups.
   Our recommendation is to create a group named `benchexec`
   with `groupadd benchexec` and add the respective users to this group.
   Note that users need to logout and login afterwards
   to actually get the group membership.

 * Put [the file `benchexec-cgroup.service`](../debian/benchexec-cgroup.service)
   into `/etc/systemd/system/`
   and enable the service with `systemctl daemon-reload; systemctl enable --now benchexec-cgroup`.

   By default, this gives permissions to users of the group `benchexec`,
   this can be adjusted in the `Environment` line as necessary.

By default, BenchExec will automatically attempt to use the cgroup
`system.slice/benchexec-cgroup.service` that is created by this service file.
If you use a different cgroup structure,
you need to ensure that BenchExec runs in the correct cgroup
by executing the following commands once per terminal session:
```
echo $$ > /sys/fs/cgroup/cpuset/<CGROUP>/tasks
echo $$ > /sys/fs/cgroup/cpuacct/<CGROUP>/tasks
echo $$ > /sys/fs/cgroup/memory/<CGROUP>/tasks
echo $$ > /sys/fs/cgroup/freezer/<CGROUP>/tasks
```

In any case, please check whether everything works
or whether additional settings are necessary as [described below](#testing-cgroups-setup-and-known-problems).

### Setting up Cgroups on Machines without systemd

The cgroup virtual file system is typically mounted at or below `/sys/fs/cgroup`.
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

It may be that your Linux distribution already mounts the cgroup file system
and creates a cgroup hierarchy for you.
In this case you need to adjust the above commands appropriately.
To optimally use BenchExec,
the cgroup controllers `cpuacct`, `cpuset`, `freezer`, and `memory`
should be mounted and usable,
i.e., they should be listed in `/proc/self/cgroups` and the current user
should have at least the permission to create sub-cgroups of the current cgroup(s)
listed in this file for these controllers.

In any case, please check whether everything works
or whether additional settings are necessary as [described below](#testing-cgroups-setup-and-known-problems).

### Setting up Cgroups in a Docker Container

If you want to run benchmarks within a Docker container,
and the cgroups file system is not available within the container,
please use the following command line argument
to mount the cgroup hierarchy within the container when starting it:

    docker run -v /sys/fs/cgroup:/sys/fs/cgroup:rw ...

Note that you additionally need the `--privileged` flag for container mode.
However, this gives your Docker container full root access to the host,
so please also add the `--cap-drop=all` flag,
make sure to use this only with trusted images,
and configure your Docker container such that everything in it
is executed under a different user account, not as root.
BenchExec is not designed to run as root and does not provide
any safety guarantees regarding its container under this circumstances.

### Testing Cgroups Setup and Known Problems

After installing BenchExec and setting up the cgroups file system, please run

    python3 -m benchexec.check_cgroups

This will report warnings and exit with code 1 if something is missing.
If you find that something does not work,
please check the following list of solutions.

If your machine has swap, cgroups should be configured to also track swap memory.
This is turned off by several distributions.
If the file `memory.memsw.usage_in_bytes` does not exist in the directory
`/sys/fs/cgroup/memory` (or wherever the cgroup file system is mounted),
this needs to be enabled by setting `swapaccount=1` on the command line of the kernel.
On Ubuntu, you can for example set this parameter by creating the file
`/etc/default/grub.d/swapaccount-for-benchexec.cfg` with the following content:

    GRUB_CMDLINE_LINUX_DEFAULT="${GRUB_CMDLINE_LINUX_DEFAULT} swapaccount=1"

Then run `sudo update-grub` and reboot.
On other distributions, please adjust your boot loader configuration appropriately.

In some Debian kernels (and those derived from them, e.g. Raspberry Pi kernel),
the memory cgroup controller is disabled by default, and can be enabled by
setting `cgroup_enable=memory` on the kernel command line, similar to
`swapaccount=1` above.


## Installation for Development

Please refer to the [development instructions](DEVELOPMENT.md).

[coloredlogs]: https://pypi.org/project/coloredlogs/
[cpu-energy-meter]: https://github.com/sosy-lab/cpu-energy-meter
[libseccomp2]: https://github.com/seccomp/libseccomp
[LXCFS]: https://github.com/lxc/lxcfs
[pqos]: https://github.com/intel/intel-cmt-cat/tree/master/pqos
[pqos_wrapper]: https://gitlab.com/sosy-lab/software/pqos-wrapper
