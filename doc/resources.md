# BenchExec: Resource Handling

This page intends to give an overview over how BenchExec handles certain kinds of resources.
Please also note the information on the [units used by BenchExec](INDEX.md#units).


## CPU Cores

When limiting CPU cores, BenchExec defines as a "core" the smallest hardware unit
that can execute a thread in parallel to other such units.
This is often called "virtual core", and the Linux kernel refers to this as "processor"
(in `/proc/cpuinfo`) and as "CPU" (under `/sys/devices/system/cpu/`).
This means, for example that assigning 8 cores per run on a system with hyper threading
will allocate 4 physical cores (each with 2 hyper-threading cores) to each run.


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

On systems with swap, BenchExec always measures and limits the complete memory usage of the tool,
i.e., its usage of physical RAM plus swap usage.
BenchExec also tries to disallow swapping of the benchmarked tool,
if the kernel allows this.

For backwards compatibility, the memory limit when given to `benchexec` without a unit suffix
is interpreted as megabytes (a warning is shown for this).
This behavior may change in a future major version of BenchExec.
It is recommended to explicitly specify the unit to avoid confusion.
In all other cases, memory values without a unit suffix are bytes.


## Wall Time

Wall-time measurements may be inaccurate on systems with an old Python version (up to Python 3.2),
if the system time changes during the benchmarking (e.g., due to daylight-savings time).
The same is true regardless of the Python version for BenchExec 1.5 and older.

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

- `cpuenergy-pkg<i>` is the energy consumption of the CPU `<i>` (whole "package").
- `cpuenergy-pkg<i>-core` is only the consumption of the CPU cores.
- `cpuenergy-pkg<i>-uncore` is the consumption of the so-called "uncore" parts of the CPU (this may include an integrated graphics card).
- `cpuenergy-pkg<i>-dram` is the consumption of the memory attached to CPU `<i>`.

The "core" and "uncore" values are included in the "package" value,
whereas for the "dram" value this is unclear.
Not all of these values may be measurable on all systems,
this depends on the CPU model.
Also the precision of the measurements
[varies across CPU models](https://tu-dresden.de/zih/forschung/ressourcen/dateien/laufende-projekte/firestarter/2015_hackenberg_hppac.pdf).
For further information about the meaning of these values,
please consult the [Intel Software Developers Manual Volume 3B Chapter 14.9](https://software.intel.com/sites/default/files/managed/7c/f1/253669-sdm-vol-3b.pdf).

BenchExec will additionally compute a value named `cpuenergy`,
which is the sum of the `cpuenergy-pkg<i>` values for all CPUs
that are used by a run.
However, note that BenchExec can only measure the energy consumption of each CPU as a whole.
Thus energy will be measured only if each run uses all cores of one or more CPUs,
and not if only a subset of the CPU's cores is used per run.


## Disk Space and I/O

BenchExec does not limit or influence I/O in any way by default.
This is acceptable for benchmarking if the benchmarked tool uses only little I/O,
but for I/O-heavy tools this means that the benchmarking may be non-deterministic and unreliable.

Currently, BenchExec has an *experimental* feature for measuring the I/O of the benchmarked process.
This is reported as the values `blkio-read` and `blkio-write` (in bytes),
if the `blkio` cgroup is usable by BenchExec.
Note that because of the experimental nature the values are not shown by default in tables,
use an appropriate `<column>` tag to select them or the command-line parameter `--all-columns` for `table-generator`.
The two values only measure I/O that actually touches a block device,
so any reads and writes that are satisfied by the file-system cache are not measured.
In certain system configurations involving LVM, RAID, encrypted disks or similar virtual block devices,
the kernel will also not manage to account disk I/O to a certain process,
so such I/O will also not be measured.
On the other hand, not all I/O to block devices is actually disk I/O,
because for example RAM disks are also counted.
So this measure may only be an approximation of disk I/O.

To prevent the benchmarked tool from filling up the whole disk
(which could make the system unusable for other users),
BenchExec can limit the number and size of the files written by the benchmarked tool
with the command-line parameters `--filesCountLimit` and `--filesSizeLimit`.
Both limits are off by default, though this may change in a future release.
There are a few restrictions, however:
- These limits are checked only periodically (currently every 60s),
  so intermediate violations are possible.
- With [container mode](container.md), files written directly into the host file system
  due to the use of `--full-access-dir` are not limited.
  If the tool modifies an existing file in a directory with overlay mode, the full file size is counted against the limit.
- Without container mode, almost no files are limited, only those that the tool
  writes to `$HOME` and `$TMPDIR` (which are fresh directories created by BenchExec).
So the recommendation is (as always) to use the container mode and not use the `--full-access-dir` flag.
