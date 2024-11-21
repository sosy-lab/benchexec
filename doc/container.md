<!--
This file is part of BenchExec, a framework for reliable benchmarking:
https://github.com/sosy-lab/benchexec

SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>

SPDX-License-Identifier: Apache-2.0
-->

# BenchExec: Container Mode

> Note: If you are looking for information on running BenchExec inside a
> container, consult [this document](benchexec-in-container.md) instead.

The container mode isolates the benchmarked process from other processes on the same system,
in a similar way as for example Docker isolates applications
(using namespaces for operating-level system virtualization).
This improves reliability of benchmarking and reproducibility of results.
Contrary to using a VM, the application is still executed with native performance,
because it is run directly on the host kernel, without any additional layers.
By using an overlay filesystem (if available), the benchmarked process can still read from the host filesystem,
but not modify any files except where specifically allowed.
You can read more about it in our paper
[Reliable Benchmarking: Requirements and Solutions](https://www.sosy-lab.org/research/pub/2019-STTT.Reliable_Benchmarking_Requirements_and_Solutions.pdf).
There is also an additional tool, `containerexec`,
which is similar to `runexec` but provides only isolation of an application in a container,
but no resource measurements and limitations.

Container mode is available since BenchExec 1.9
and enabled by default since BenchExec 2.0.
It can be disabled with the flag `--no-container` in case of problems,
but instead we recommend configuring and troubleshooting
the container appropriately as described below.

The features of container mode are:

- Processes in the container cannot see and kill processes outside the container.
- Network access is not possible from the container,
  not even communicating with processes on the same host (configurable).
- File-system access can be restricted,
  and write accesses are redirected such that they do not affect the host filesystem (configurable).
  By default, file writes in the container are kept in memory (in a "RAM disk")
  and are not written to disk and not visible outside of the container.
  This reduces disk I/O and increases reproducibility.
  Furthermore, data written to this RAM disk are counted towards the run's memory limit.
- Result files produced by the tool in the container can be collected and copied
  to an output directory afterwards.

Note that while BenchExec containers rely on the same kernel features as similar solutions,
they are not meant as a secure solution for restricting potentially malicious applications.
**Execution of untrusted applications in a BenchExec container is at your own risk.**
In particular, while the code in the tool-info modules of BenchExec
is also executed within a container,
there are known ways how a malicious tool-info module would be able to execute code outside of the container.


## Container Configuration

This section describes how BenchExec configures the container, and how it can be customized.

### Directory Access Modes
The directory tree in the container is based on the directory tree of the host system,
but BenchExec supports isolating the container by preventing read or write access to certain directories.
For each directory in the container one of the following four access modes can be given:

- **hidden**: This host directory is hidden in the container.
  Instead a fresh, empty, writable, memory-backed directory (i.e., an empty RAM disk)
  will be visible in the container in this place.
  Writes to this directory will not be visible on the host.
- **read-only**: This directory is visible in the container, but read-only.
- **overlay**: This directory is visible in the container and
  an overlay filesystem (either from the
  [kernel](https://www.kernel.org/doc/Documentation/filesystems/overlayfs.txt)
  or [fuse-overlayfs])
  is layered on top of it that redirects all write accesses.
  This means that write accesses are possible in the container, but the effect of any write
  is not visible on the host, only inside the container, and not written to disk.
- **full-access**: This directory is visible and writable in the container,
  and writes will be directly visible on the host.

The respective mode can be specified with the command-line parameters
`--hidden-dir`, `--read-only-dir`, `--overlay-dir`, and `--full-access-dir`.
Directory modes are applied recursively,
i.e., for all subdirectories which do not have a mode specified explicitly.
For the overlay mode, please note the [system requirements](INSTALL.md#kernel-requirements).

The default configuration is `--overlay-dir / --hidden-dir /run --hidden-dir /tmp`,
i.e., to mount an overlay filesystem over all directories except for `/run` and `/tmp`,
which are replaced by empty directories.
Furthermore, all partitions with FAT or NTFS file systems
as well as all autofs and FUSE mount points are mounted read-only,
because overlay does not work for these.

To overwrite the default configuration,
simply specify other directory modes for one or more of these directories.
Note that if you specify a different directory mode for one of them,
the default configuration for the other directories will still be used.
Of course you can always specify additional directory modes for other directories.
So for example, to disable the overlay mount (e.g., on systems that do not support it)
and keep the default modes for `/run` and `/tmp`, simply specify `--read-only-dir /`,
and if additionally you need certain directories to be writable,
add `--full-access-dir ...` for them.

Writes to directories in the hidden and overlay modes will be stored in a fresh RAM disk
(a [tmpfs](https://www.kernel.org/doc/Documentation/filesystems/tmpfs.txt) instance)
and the produced result files will be copied to an output directory after the run
(cf. below for how to customize the latter).
All data stored in such directories are measured as part of the memory consumption of the run
and are counted towards the memory limit:
The sum of the memory consumption of the process(es) of the run
and the sum of the sizes of the existing files written by the run
needs to be always less than the memory limit.
If this is not desired, specify the parameter `--no-tmpfs`.
Note, however, that this parameter has two disadvantages:
With it, writes performed by the tool will produce actual disk I/O,
which decreases reproducibility,
and the tool can fill up the host's filesystem.
Writes to directories in the full-access mode will be performed as if they were done outside of the container,
and thus the same disadvantages apply.

In general, for a good isolation of runs and reproducibility of results,
we advise to use directory access modes that are as restrictive as possible.
In particular, we recommend to use the full-access mode only when absolutely necessary
(maybe on systems that do not support overlays),
and to also hide any directories that might contain cache or configuration files
that could unintentionally influence the run (like the home directory).

### Network Access
By default, a container has no access to the network.
It has a loopback interface such that processes inside the container can communicate with each other,
but there is no connection to any interfaces that are visible outside of the container.
By using `--network-access`, the container can be given full access to the network
like any application running outside of the container has.

### User, Group, and Host Lookups
By default, a container uses its own list of users and groups.
This is done to avoid failures during user lookups if some remote user database is configured
on the system (e.g., NIS or LDAP), and network access is disabled in the container.
For the same reason, DNS lookups for host names are disabled.
All of these can be re-enabled with `--keep-system-config`,
which also lets the container use the same user list as the host.


## Retrieving Result Files
Files written by the executed tool to directories in the hidden or overlay modes
are not visible on the host filesystem.
In order to allow the user to access these files after the benchmarking,
BenchExec copies them into an output directory.

Note that files written to a directory in the full-access mode will not be affected by this
(they already exist on the host filesystem).
If you cannot use the hidden or overlay modes but still need to retrieve output files,
you need to mark some directory as writable with `--full-access-dir`.
But note that this has the disadvantage that the tool can then make arbitrary changes
to existing files and directories at this location,
so full isolation is no longer guaranteed.

Patterns matching the following rules can be given
to select only a subset of created files to be copied:
- A file is retrieved if any of the given patterns match it.
- If the pattern is a relative path (does not start with `/`),
  it is interpreted as relative to the working directory of the tool.
  If all given patterns are relative,
  the directory tree that is created in the output directory will also start at this point.
- Absolute paths are also valid as patterns,
  and in this case the directory tree in the output directory
  will start at the root of the filesystem.
- Relative patterns that traverse upwards out of the working directory (e.g., `..`) are not allowed.
- The shell wildcards `?` and `*` are supported,
  and also the recursive wildcard `**`.
- If a directory is matched by the pattern, all files in the directory will be copied recursively.
- Only regular files are copied; symlinks, empty directories, etc. are ignored.

This means that if you want to retrieve all files written by the tool below its working directory,
use the pattern `.` or `*` (this is the default).
If you want to retrieve all files written anywhere use `/`.
For disabling the retrieval of result files altogether, use the empty string as pattern.

For `containerexec` and `runexec`, the command-line parameters
`--result-files` and `--output-directory` can be used
to specify the pattern(s) for matching result files and the directory where they should be placed.
For `benchexec`, the patterns are given within `<resultfiles>` tags
in the benchmark-definition XML file,
and the result files are placed in a directory besides the result XML file.


## Common Problems

Note that for investigating container-related problems, it can be easier to start an interactive shell
in a container with `containerexec` than using `benchexec` or `runexec`.

#### `Cannot execute ...: Unprivileged user namespaces forbidden on this system...`
Unprivileged user namespaces are forbidden on your system
(this is the default on some distributions like Debian, Arch Linux, CentOS, and Ubuntu since 24.04).
Please check the [system requirements](INSTALL.md#kernel-requirements)
how to enable them.

#### `Cannot execute ...: Creating namespace for container mode failed`
It seems your kernel does not support unprivileged user namespaces.
Please check the [system requirements](INSTALL.md#kernel-requirements)
and make sure that the kernel is compiled with `CONFIG_USER_NS`.
Furthermore note that running BenchExec inside other container solutions
such as Docker may or may not work depending on how the outer container
is configured (for example for Docker, `--privileged` is necessary).
You can still use BenchExec if you completely disable the container mode with `--no-container`.

#### `Failed to configure container: [Errno 19] Creating overlay mount for '...' failed: No such device`
Your kernel does not support the overlay filesystem,
please check the [system requirements](INSTALL.md#kernel-requirements).
You can use [fuse-overlayfs] or a different access mode for directories, e.g., with `--read-only-dir /`.
If some directories need to be writable, specify other directory modes for these directories as described above.

#### `Failed to configure container: [Errno 1] Creating overlay mount for '...' failed: Operation not permitted`
Your kernel does not allow mounting the overlay filesystem inside a container.
For this you need either Ubuntu, [fuse-overlayfs], or kernel version 5.11 or newer.
Alternatively, if you cannot use any of these,
you can use a different access mode for directories, e.g., with `--read-only-dir /`.
If some directories need to be writable, specify other directory modes for these directories as described above.

#### `Failed to configure container: [Errno 22] Creating overlay mount for '...' failed: Invalid argument`
Your kernel does not allow mounting an overlay filesystem in this place.
Often an explanation appears in the system log,
so check for error messages with `journalctl -e -k -g overlayfs`.

One known problem is [this kernel regression](https://github.com/sosy-lab/benchexec/issues/776),
which prevents overlays from being used if there is another mountpoint somewhere below the target directory.
Another limitation of the kernel is that one can only nest overlays twice,
so if you want to run a container inside a container inside a container,
at least one of these needs to use a non-overlay mode for this path.

We recommend the installation of [fuse-overlayfs] in version 1.10 or newer,
which supports all of these use cases.

#### `Cannot change into working directory inside container: [Errno 2] No such file or directory`
Either you have specified an invalid directory as working directory with `--dir`,
or your current directory on the host is hidden inside the container
(note that by default everything below `/tmp` is hidden).
Specify a valid working directory for the container with `--dir`.

#### `Cannot start process: [Errno 2] No such file or directory`
The executable to start was not found in the container.
Make sure that the executable exists and it is visible inside the container
(note that by default everything below `/tmp` is hidden).

#### Problems when accessing files in container: process dies, `Operation not supported`, `No such device or address`
These are symptoms that occur when an overlay is mounted over an NFS share
with several versions of the Linux kernel, including at least kernel versions up to 4.5
([bug report](https://bugs.launchpad.net/ubuntu/+source/linux/+bug/1566471)).
If a kernel upgrade does not help, please use a different access mode for NFS-mounted directories,
such as `--hidden-dir` or `--read-only-dir`.

### BenchExec sometimes hangs if many parallel runs are executed
This happens if we clone the Python process while it is in an inconsistent state.
Make sure to use BenchExec 3.14 or newer,
where [#435](https://github.com/sosy-lab/benchexec/issues/435) is fixed
and a workaround for [#656](https://github.com/sosy-lab/benchexec/issues/656) is present.
If it still occurs, please attach to all child process of BenchExec
with `sudo gdb -p <PID>`, get a stack trace with `bt`,
and [report an issue](https://github.com/sosy-lab/benchexec/issues/new) with as much information as possible.
BenchExec will usually be able to continue if the hanging child process is killed.

[fuse-overlayfs]: https://github.com/containers/fuse-overlayfs
