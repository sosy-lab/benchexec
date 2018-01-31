# BenchExec: Setup

## Download and Installation

BenchExec requires at least Python 3.2.
(The [runexec](runexec.md) tool and module also works with Python 2.7.)
Thus, make sure to use Python 3 for installation as described below,
otherwise only `runexec` will get installed.

Note that we recommend to additionally install
[cpu-energy-meter](https://github.com/sosy-lab/cpu-energy-meter)
in order to get energy measurements on Intel CPUs.

### Debian/Ubuntu

For installing BenchExec on Debian or Ubuntu we recommend the `.deb` package
that can be downloaded from [GitHub](https://github.com/sosy-lab/benchexec/releases):

    apt install python3-tempita
    dpkg -i benchexec_*.deb

This package also automatically configures the necessary cgroup permissions.
Just add your user to the group `benchexec` and reboot:

    adduser <USER> benchexec

Afterwards, please check whether everything works
or whether additional settings are necessary as [described below](#testing-cgroups-setup-and-known-problems).

### Other Distributions

For other distributions we recommend to use the Python package installer pip.
To automatically download and install the latest stable version and its dependencies
from the [Python Packaging Index](https://pypi.python.org/pypi/BenchExec) with pip,
run this command:

    sudo pip3 install benchexec

You can also install BenchExec only for your user with

    pip3 install --user benchexec

In the latter case you probably need to add the directory where pip installs the commands
to the PATH environment by adding the following line to your `~/.profile` file:

    export PATH=~/.local/bin:$PATH

Of course you can also install BenchExec in a virtualenv if you are familiar with Python tools.

Please make sure to configure cgroups as [described below](#setting-up-cgroups).

### Development version

To install the latest development version from the
[GitHub repository](https://github.com/sosy-lab/benchexec), run this command:

    pip3 install --user git+https://github.com/sosy-lab/benchexec.git

It is useful to install the system package `python3-lxml` before,
otherwise pip will try to download and build this module,
which needs a compiler and several development header packages.

If you want to run benchmarks under different user account than your own,
please check the [respective documentation](separate-user.md) for how to setup sudo.

Please make sure to configure cgroups as [described below](#setting-up-cgroups).


## Kernel Requirements

To execute benchmarks and reliably measure and limit their resource consumption,
BenchExec requires that the user which executes the benchmarks
can create and modify cgroups (see below for how to allow this).

For container mode of BenchExec (available since BenchExec 1.9, default starting with BenchExec 2.0),
a relatively recent kernel is needed.
Please see [container mode](container.md) for the system requirements.

Without container mode, any Linux kernel version of the last several years is
acceptable, though there have been performance improvements for the memory
controller in version 3.3, and cgroups in general are still getting improved, thus,
using a recent kernel is also a good idea.

### Warning for Users of Linux Kernel up to 3.13 (e.g., Ubuntu 14.04)

There is a race condition in the Linux kernel up to version 3.13
that sometimes causes the machine to freeze if a process hits its memory limit
([blog post with description](https://community.nitrous.io/posts/stability-and-a-linux-oom-killer-bug),
[commits fixing it](https://git.kernel.org/cgit/linux/kernel/git/torvalds/linux.git/log/?id=4d4048be8a93769350efa31d2482a038b7de73d0&qt=range&q=9853a407b97d8d066b5a865173a4859a3e69fd8a...4d4048be8a93769350efa31d2482a038b7de73d0),
[entry in Ubuntu bug tracker](https://bugs.launchpad.net/ubuntu/+source/linux/+bug/1510196)).
The kernel log then contains messages like `BUG: soft lookup`
and `Memory cgroup out of memory` or similar immediately before the crash,
and the machine needs to be rebooted.

So far we have experienced this only if the cgroup option `memory.use_hierarchy` is enabled.
Thus, if you use kernel 3.13 or older with `memory.use_hierarchy`,
please upgrade or make sure your kernel contains the above fixes.
For Ubuntu 14.04, upgrading can be done using the officially supported
[Ubuntu LTS Hardware Enablement Stack](https://wiki.ubuntu.com/Kernel/LTSEnablementStack).


## Setting up Cgroups

If you have installed the Debian package and you are running systemd
(default since Debian 8 and Ubuntu 15.04),
the package should have configured everything automatically.
Just add your user to the group `benchexec` and reboot:

    adduser <USER> benchexec

### Setting up Cgroups on Machines with systemd

This is relevant for most users of Debian >= 8, Fedora >= 15, Redhat >= 7, Suse SLES >= 12, Ubuntu >= 15.04,
and potentially other distributions.
systemd makes extensive usage of cgroups and [claims that it should be the only process that accesses cgroups directly](https://wiki.freedesktop.org/www/Software/systemd/ControlGroupInterface/).
Thus it would interfere with the cgroups usage of BenchExec.

By using a fake service we can let systemd create an appropriate cgroup for BenchExec
and prevent interference.
The following steps are necessary:

 * Put [the file `benchexec-cgroup.conf`](../debian/additional_files/lib/systemd/system.conf.d/benchexec-cgroup.conf)
   into `/etc/systemd/system.conf.d`
   to ensure systemd creates a cgroup for all our controllers.
   The setting in this file needs a reboot to take effect,
   and [potentially a regeneration of your initramdisk](http://www.freedesktop.org/software/systemd/man/systemd-system.conf.html#Options).

 * Put [the file `benchexec-cgroup.service`](../debian/benchexec-cgroup.service)
   into `/etc/systemd/system/`
   and enable the service with `systemctl daemon-reload; systemctl enable --now benchexec-cgroup`.

   By default, this gives permissions to use the BenchExec cgroup to users of
   the group `benchexec`, please adjust this as necessary or create this group
   by running `groupadd benchexec` command beforehand.

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
