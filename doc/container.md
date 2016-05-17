# BenchExec: Container Mode

**Note**: Container mode is currently in **beta**!
You are welcome to use it, but please note that future versions of BenchExec
may change how the container mode works or how it is configured.
If you use it, please tell us your experiences with it.

Container mode is available since BenchExec 1.9,
and BenchExec 2.0 will be the release where container mode is considered stable
and enabled by default.
Until then, it needs to be explicitly enabled with the flag `--container`
for `benchexec` and `runexec`.
The flag `--no-container` can always be given to explicitly disable container mode
and the warning about it.
There is now also an additional tool, `containerexec`,
which is similar to `runexec` but provides only isolation of an application in a container,
but no resource measurements and limitations.

The container mode isolates the benchmarked process from other processes on the same system,
in a similar way as for example Docker isolates applications
(using operating-level system virtualization).
This is recommended to improve reproducibility of results.
Contrary to using a VM, the application is still executed with native performance,
because it is run directly on the host kernel, without any additional layers.

The features of container mode are:

- Processes in the container cannot see and kill processes outside the container.
- Network access is not possible from the container,
  not even communicating with processes on the same host (configurable).
- File-system access can be restricted,
  and write accesses can be redirected such that they do not affect the host filesystem.
- Result files produced by the tool in the container can be collected and copied
  to an output directory afterwards.

Note that while BenchExec containers rely on the same kernel features as similar solutions,
they are not meant as a secure solution for restricting potentially malicious applications.
**Execution of untrusted applications in a BenchExec container is at your own risk.**


## System Requirements

Container mode uses two kernel features:

- **User Namespaces**: This is typically available in Linux 3.8 or newer,
  and most distros enable it by default (the kernel option is `CONFIG_USER_NS`).
  Debian disables this feature for regular users, so the system administrator needs to enable it
  with `sudo sysctl -w kernel.unprivileged_userns_clone=1` or a respective entry
  in `/etc/sysctl.conf`.
  Arch Linux has the feature [disabled completely](https://bugs.archlinux.org/task/36969).

- **Overlay Filesystem**: This is typically available in Linux 3.18 or newer
  (kernel option `CONFIG_OVERLAY_FS`).
  However, it seems that only Ubuntu allows regular users to create such mounts in a container.
  Users of other distributions can still use container mode, but have to choose a different mode
  of mounting the file systems in the container, e.g., with `--read-only-dir /`.
  Alternatively, you could compile your own kernel and include [this patch](http://kernel.ubuntu.com/git/ubuntu/ubuntu-xenial.git/commit?id=0c29f9eb00d76a0a99804d97b9e6aba5d0bf19b3).
  Note that creating overlays over NFS mounts is not stable at least until Linux 4.5,
  thus it is recommended to specify a different directory mode for every NFS mount on the system.

**Summary**: It is recommended to use Ubuntu since 15.04 (Vivid Vervet),
or Ubuntu 14.04 LTS with a newer kernel from the official [LTS Enablement Stack](https://wiki.ubuntu.com/Kernel/LTSEnablementStack).
Be careful with overlays over NFS.
Users of other distributions or older kernels need to avoid using overlay mounts.

If your kernel fulfills these requirements, no further setup or permissions are necessary.


## Container Configuration

This section describes how BenchExec configures the container, and how it can be customized.

### Directory Access Modes
The directory tree in the container is based on the directory tree of the host system,
but BenchExec supports isolating the container by preventing read or write access to certain directories.
For each directory in the container one of the following four access modes can be given:

- **hidden**: This host directory is hidden in the container.
  Instead a fresh, empty, writable directory will be visible in the container in this place.
  Writes to this directory will not be visible on the host.
- **read-only**: This directory is visible in the container, but read-only.
- **overlay**: This directory is visible in the container and
  an [overlay filesystem](https://www.kernel.org/doc/Documentation/filesystems/overlayfs.txt)
  is layered on top of it that redirects all write accesses.
  This means that write accesses are possible in the container, but the effect of any write
  is not visible on the host, only inside the container.
- **full-access**: This directory is visible and writable in the container,
  and writes will be directly visible on the host.

The respective mode can be specified with the command-line parameters
`--hidden-dir`, `--read-only-dir`, `--overlay-dir`, and `--full-access-dir`.
Directory modes are applied recursively,
i.e., for all subdirectories which do not have a mode specified explicitly.
For the overlay mode, please note the system requirements mentioned above.

The default configuration is `--overlay-dir / --hidden-dir /run --hidden-dir /tmp`,
i.e., to mount an overlay filesystem over all directories except for `/run` and `/tmp`,
which are replaced by empty directories.
To disable the default overlay mount and replace it by e.g. read-only access,
specify `--read-only-dir /`.

In general, for a good isolation of runs and reproducibility of results,
we advise to use directory access modes that are as restrictive as possible.
In particular, we recommend to use the full-access mode only when absolutely necessary
(maybe on systems that do not support overlays),
and to also hide any directories that might contain cache or configuration files
that could unintentionally influence the run (like the home directory).

Writes to directories in the hidden and overlay modes will be stored in a temporary directory
on the host and the produced result files will be copied to an output directory after the run.
Please see below for how to customize this.
We do not use a RAM disk for storing these files as this would allow the executed tool
to use an arbitrary amount of memory and circumvent the memory limit.

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

Note that this feature is only available with an overlay mount for `/etc`,
and thus a container that uses a different access mode for this directory
will have `--keep-system-config` set by default.


## Retrieving Result Files
Files written by the executed tool to directories in the hidden or overlay modes
are not visible on the host filesystem.
In order to allow the user to access these files after the benchmarking,
BenchExec copies them into an output directory.
Note that files written to a directory in the full-access mode will not be affected by this.
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
  and if you use Python 3.5 or newer also the recursive wildcard `**`.
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

#### `Cannot execute ...: Creating namespace for container mode failed`
Probably your kernel does not support unprivileged user namespaces, please check the system requirements above.
On Debian, please ask your system administrator to enable them for you.
Note that you cannot nest BenchExec containers currently,
and using them inside other container solutions such as Docker is untested.
You can still use BenchExec if you completely disable the container mode with `--no-container`.

#### `Failed to configure container: [Errno 19] Creating overlay mount for '...' failed: No such device`
Your kernel does not support the overlay filesystem, please check the system requirements above.
You can use a different access mode for directories, e.g., with `--read-only-dir /`.

#### `Failed to configure container: [Errno 1] Creating overlay mount for '...' failed: Operation not permitted`
Your kernel does not allow mounting the overlay filesystem inside a container
(this is apparently only possible on Ubuntu).
You can use a different access mode for directories, e.g., with `--read-only-dir /`.

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
with several versions of the Linux kernel, including at least kernel versions 4.2 to 4.5
([bug report](https://bugs.launchpad.net/ubuntu/+source/linux/+bug/1566471)).
If a kernel upgrade does not help, please use a different access mode for NFS-mounted directories,
such as `--hidden-dir` or `--read-only-dir`.
