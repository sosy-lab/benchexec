<!--
This file is part of BenchExec, a framework for reliable benchmarking:
https://github.com/sosy-lab/benchexec

SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>

SPDX-License-Identifier: Apache-2.0
-->

# Benchmarking Guidelines

Please check the following guidelines for advice
on how to get reliable benchmark results when using BenchExec.
For more general guidelines about benchmarking,
e.g., what to do when implementing a benchmarking tool,
please read our paper [Reliable Benchmarking: Requirements and Solutions](https://www.sosy-lab.org/research/pub/2019-STTT.Reliable_Benchmarking_Requirements_and_Solutions.pdf).
There are also many other valuable resources about benchmarking,
for example this list of [Benchmarking Crimes](https://gernot-heiser.org/benchmarking-crimes.html)
and these [ACM SIGSOFT Empirical Standards for Benchmarking](https://github.com/acmsigsoft/EmpiricalStandards/blob/master/docs/Benchmarking.md).

### Document as much as possible
For correct interpretation of results, it is important that everything important
about the benchmarking is documented and archived together with the results.
BenchExec already adds lots of information (e.g., about the benchmarking host),
but it cannot know about everything (e.g., who did the benchmarking
and for which purpose, what was the version of the benchmark set, etc.).
To document such facts, write them into a text file
and pass it to `benchexec` with the parameter `--decription-file <file>`.
Furthermore, we recommend to use `benchexec --commit`
to automatically store BenchExec results in a git repository.

### Use the latest version of BenchExec
New versions of BenchExec might contain features or bug fixes
that make benchmarking more precise.

### Use container mode
The [container mode](container.md) should not be turned off
because it isolates individual runs and makes benchmarking more reliable.
Also make sure to configure the container (e.g., directory access)
as restrictive as possible.

### Specify memory limit
Without a fixed memory limit, the amount of memory available for benchmarking
is non-deterministic.

### Check warnings of BenchExec
In certain situations, BenchExec will issue a warning during benchmarking,
e.g., if Turbo Boost is enabled, the system overheated etc.
Check the output of BenchExec for such warnings and resolve them.

### Use parallel runs with caution
When multiple runs are executed in parallel by BenchExec,
this can potentially influence their performance.
The details on how large this effect is and whether this is acceptable
depend on the characteristics of your hardware.
In many cases, one parallel run per CPU is safe,
but this is not guaranteed.

### Avoid large amounts of I/O
Runs with I/O suffer from non-deterministic performance.
If possible, ensure that I/O is reduced to a minimum.
For example, if a tool produces large outputs,
check whether this can be disabled or at least redirected to `/dev/null`.

### Check documentation of benchmarked tool for advice
Some tools may require specific configuration for reliable benchmarking,
for example for disabling unnecessary output,
making random behavior deterministic by using a constant initial seed value,
or for adjusting memory usage to the memory limit.
So check the tool documentation for advice on this.

### Use a recent Linux kernel
This is required for container mode,
but in general a newer Linux version might also include improvements
for the kernel features that BenchExec uses,
and better support for your hardware.
For example, BenchExec's memory measurements and limits
have less overhead on Linux 4.14 and newer.

On LTS versions of Ubuntu, consider the [LTS Enablement Stack](https://wiki.ubuntu.com/Kernel/LTSEnablementStack).

### Ensure time gets synchronized using NTP
As described in [this paper on benchmarking](http://raptor.cs.arizona.edu/~rts/pubs/spe16.pdf),
time measurements can be imprecise if the hardware clock is not fully precise
and there is no time synchronization via NTP.
Time-synchronization daemons such as [ntpd](http://ntp.org/),
[systemd-timesyncd](https://www.freedesktop.org/software/systemd/man/systemd-timesyncd.service.html]),
or [chrony](https://chrony.tuxfamily.org/),
do not only synchronize the machine's time with external sources
(which is not necessary for measurements),
but also apply corrections to the frequency of the local clock,
which makes time measurements more precise.
Note that other solutions without such a daemon,
for example simple periodic time synchronizations,
do not achieve this.
