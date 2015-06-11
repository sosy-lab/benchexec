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

You can also install BenchExec only for your user with

    pip3 install --user benchexec

In this case you probably need to add the directory where pip installs the commands
to the PATH environment by adding the following line to your `~/.profile` file:

    export PATH=~/.local/bin:$PATH

Of course you can also install BenchExec in a virtualenv if you are familiar with Python tools.

To install the latest development version from the
[GitHub repository](https://github.com/dbeyer/benchexec), run this command:

    pip3 install --user git+https://github.com/dbeyer/benchexec.git


## Setting up Cgroups

To execute benchmarks and reliably measure and limit their resource consumption,
BenchExec requires that the user which executes the benchmarks
can create and modify cgroups.

Any Linux kernel version of the last years is
acceptable, though there have been performance improvements for the memory
controller in version 3.3, and cgroups in general are still getting improved, thus,
using a recent kernel is a good idea.

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
Alternatively, start BenchExec with `cgexec --sticky` to tell `cgrulesengd`
that it should not interfere with BenchExec and its child processes.

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


## Installation for Development

After cloning the [GitHub repository](https://github.com/dbeyer/benchexec),
BenchExec can be used directly from within the working directory.
Scripts for starting the three programs are available in the `bin` directory.
For `table-generator`, the [Python package Tempita](https://pypi.python.org/pypi/Tempita)
needs to be installed on the system.

The alternative (recommended) way is to create a virtual Python environment
and to install BenchExec in development mode within this environment:

    virtualenv -p /usr/bin/python3 path/to/venv
    source path/to/venv/bin/activate
    pip install -e path/to/benchexec/working/directory

This will automatically install all dependencies
and place appropriate start scripts on the PATH.