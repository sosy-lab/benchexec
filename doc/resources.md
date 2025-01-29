<!--
This file is part of BenchExec, a framework for reliable benchmarking:
https://github.com/sosy-lab/benchexec

SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>

SPDX-License-Identifier: Apache-2.0
-->

# BenchExec: Resource Handling

This page intends to give an overview over how BenchExec handles certain kinds of resources.
Please also note the information on the [units used by BenchExec](INDEX.md#units).


## CPU Cores

When limiting CPU cores, BenchExec defines as a "core" the smallest hardware unit
that can execute a thread in parallel to other such units.
This is often called "virtual core", and the Linux kernel refers to this as "processor"
(in `/proc/cpuinfo`) and as "CPU" (under `/sys/devices/system/cpu/`).
When assigning more than one core to a run,
BenchExec makes sure to select cores that are as close to each other as possible
in the hardware architecture of the CPU.
This means for example that assigning 8 cores per run on a system with hyper threading
will allocate 4 physical cores (each with 2 hyper-threading cores) to each run.
The only exception is if `--no-hyperthreading` is used,
in which case all but one virtual core per physical core remain unused.
Furthermore, users of BenchExec can prevent usage of certain cores with `--allowedCores`.

## Memory

Memory measurement and limitation is delegated to the Linux kernel by BenchExec,
thus the [information from kernel documentation](https://www.kernel.org/doc/Documentation/cgroup-v1/memory.txt)
applies. For example, both is only possible with a granularity of the size of a memory page.

The measured memory usage may include memory pages that are part of the kernel's file-system cache
if the files were loaded for the current run.
Before the memory limit is reached, the kernel promises to reclaim memory from these caches,
and the tool is only killed due to out-of-memory if there is still not enough memory.

The memory as measured and limited by BenchExec includes the memory
from all processes started by the tool.
Memory pages shared across multiple processes of a single run are counted only once.
In addition, data stored by the tool on the filesystem
is measured and limited by BenchExec as part of the memory consumption
except if this is disabled with `--no-container` or `--no-tmpfs`
or if the tool writes to a directory in the full-access mode.

On systems with swap, BenchExec always measures and limits the complete memory usage of the tool,
i.e., its usage of physical RAM plus swap usage.
BenchExec also tries to disallow swapping of the benchmarked tool,
if the kernel allows this.


## Time Limit

The time limit of BenchExec always refers to the CPU time of the executed tool
unless explicitly specified otherwise.
CPU time measure the time that the tool was actually making use of CPU cores,
i.e., without times where the tool slept.
If the tool uses more than one CPU core at the same time,
the CPU time is the sum of the usage times for each of the cores.

Note that for technical reasons,
enforcement of time limits is not perfectly exact:
The tool might run for about a second longer than the time limit specifies.
If the tool terminates by itself within this time span,
BenchExec will still count this as a timeout in its `status` value.


## Wall Time

BenchExec always limits the wall time, too, if the CPU time is limited.
This is done to prevent infinitely-long hanging runs if no CPU time is used,
e.g., due to a deadlock of the tool.
The wall-time limit is set to value that is slightly higher than the CPU-time limit.
For `runexec` this can be changed by explicitly specifying a wall-time limit,
though the wall-time limit cannot be disabled completely if a CPU-time limit is given.


## Energy

BenchExec attempts to measure the energy consumption of a run where possible.
Currently measurements are implemented for the energy consumption of the CPU
(not the whole system), and only for modern Intel CPUs (since SandyBridge).

For energy measurements to work,
the tool [cpu-energy-meter](https://github.com/sosy-lab/cpu-energy-meter) needs to be installed.
It will measure up to four values for each of the CPUs:

- `cpuenergy-pkg<i>-package` is the energy consumption of the CPU `<i>` (whole "package").
- `cpuenergy-pkg<i>-core` is only the consumption of the CPU cores.
- `cpuenergy-pkg<i>-uncore` is the consumption of the so-called "uncore" parts of the CPU (this may include an integrated graphics card).
- `cpuenergy-pkg<i>-dram` is the consumption related to memory attached to CPU `<i>` (unclear what exactly this covers and might vary across systems).

The "core" and "uncore" values are included in the "package" value,
whereas for the "dram" value this is unclear.
Not all of these values may be measurable on all systems,
this depends on the CPU model.
Also the precision of the measurements
[varies across CPU models](https://tu-dresden.de/zih/forschung/ressourcen/dateien/laufende-projekte/firestarter/2015_hackenberg_hppac.pdf).
For further information about the meaning of these values,
please consult the [Intel Software Developers Manual Volume 3B Chapter 14.9](https://software.intel.com/sites/default/files/managed/7c/f1/253669-sdm-vol-3b.pdf).

BenchExec will additionally compute a value named `cpuenergy`,
which is the sum of the `cpuenergy-pkg<i>-package` values for all CPUs
that are used by a run.
However, note that BenchExec can only measure the energy consumption of each CPU as a whole.
Thus energy will be measured only if each run uses all cores of one or more CPUs,
and not if only a subset of the CPU's cores is used per run.


## Disk Space and I/O

In the default [container mode](container.md),
BenchExec redirects all write accesses to a `tmpfs` instance (a "RAM disk").
Data stored on this RAM disk are counted towards the memory limit.
Read accesses to pre-existing files are performed as usually
and are not limited or influenced by BenchExec.

Without container mode,
BenchExec does not limit or influence I/O in any way by default.
This is acceptable for benchmarking if the benchmarked tool uses only little I/O,
but for I/O-heavy tools this means that the benchmarking may be non-deterministic and unreliable.

Currently, BenchExec has an *experimental* feature for measuring the I/O of the benchmarked process.
This is reported as the values `blkio-read` and `blkio-write` (in bytes),
if the `blkio` cgroup is usable by BenchExec.
Note that because of the experimental nature the values are not shown by default in tables,
use an appropriate `<column>` tag to select them or the command-line parameter `--all-columns` for `table-generator`.
The two values only measure I/O that actually touches a block device,
so any reads and writes that are satisfied by the file-system cache
or use a RAM disk are not measured.
In certain system configurations involving LVM, RAID, encrypted disks or similar virtual block devices,
the kernel will also not manage to account disk I/O to a certain process,
so such I/O will also not be measured.
On the other hand, not all I/O to block devices is necessarily disk I/O.
So this measure may only be an approximation of disk I/O.

To prevent the benchmarked tool from filling up the whole disk
(which could make the system unusable for other users),
the container mode with a backing RAM disk should be used.
If this is not desired and `--no-tmpfs` is used,
BenchExec can limit the number and size of the files written by the benchmarked tool
with the command-line parameters `--filesCountLimit` and `--filesSizeLimit`.
Both limits are off by default.
There are a few restrictions, however:
- These limits are checked only periodically (currently every 60s),
  so intermediate violations are possible.
- With [container mode](container.md), files written directly into the host file system
  due to the use of `--full-access-dir` are not limited.
  If the tool modifies an existing file in a directory with overlay mode, the full file size is counted against the limit.
- Without container mode, almost no files are limited, only those that the tool
  writes to `$HOME` and `$TMPDIR` (which are fresh directories created by BenchExec).
So the recommendation is (as always) to use the container mode and not use the `--full-access-dir` flag.


## L3 Cache

On certain Intel CPUs, BenchExec supports isolation of L3 cache between parallel runs
if [pqos_wrapper](https://gitlab.com/sosy-lab/software/pqos-wrapper)
and the [pqos library](https://github.com/intel/intel-cmt-cat/tree/master/pqos) are installed.
If possible, the L3 cache of the CPU is separated into partitions
and each run is assigned to one partition.
This has the effect that each run has the same amount of L3 cache available
and is not influenced by other cache-hungry runs that are executing in parallel.
Furthermore, this also allows measuring cache allocation and memory-bandwidth usage.


## Processes and Threads

The number of concurrent processes and threads is limited on Linux,
thus a tool that creates a large number of them (a "fork bomb")
can create problems for parallel runs and the rest of the system.
BenchExec currently does not automatically handle this,
but if `runexec` is used this can be done easily.
Make the [`pids` cgroup](https://www.kernel.org/doc/Documentation/cgroup-v1/pids.txt)
available in the same way as the other cgroups,
and execute `runexec` with the additional parameter `--set-cgroup-value pids.max=1000`
(or any different number).
This will limit the amounts of processes and threads that can exist at the same time.
Further enhancements should be discussed in [this issue](https://github.com/sosy-lab/benchexec/issues/235).
