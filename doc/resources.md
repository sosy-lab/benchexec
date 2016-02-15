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
