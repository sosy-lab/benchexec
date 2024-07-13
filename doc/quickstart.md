<!--
This file is part of BenchExec, a framework for reliable benchmarking:
https://github.com/sosy-lab/benchexec

SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>

SPDX-License-Identifier: Apache-2.0
-->

# A Beginner's Guide to Reliable Benchmarking

> If your current setup looks similar to the below example (or you are thinking
> about such a setup), we strongly recommend following this guide for a much
> more reliable process.

## Audience

This guide provides a brief summary of instructions to set up reliable
benchmark measurements using BenchExec and important points to consider. It is
meant for users who either want to set up benchmarking for a small number of
executions from scratch or already have a simple setup using, e.g., 
[`time`](https://linux.die.net/man/1/time),
[`timeout`](https://linux.die.net/man/1/timeout),
[`taskset`](https://linux.die.net/man/1/taskset),
[`ulimit`](https://linux.die.net/man/3/ulimit), etc. Concretely, this guide
will show you how to use [`runexec`](runexec.md) as a simple but much more
reliable "drop-in" replacement for these tools. If you want to benchmark large
number of executions or get the most out of what BenchExec provides as a
benchmarking framework, consider using the tool [`benchexec`](benchexec.md)
instead (further details below).

## Why Should I use BenchExec?

As a simple example, suppose that you want to measure the performance of your
newly implemented tool `program` with arguments `--foo` and `--bar` on the
input files `input_1.in` to `input_9.in`. To measure the runtime of the tool,
you might execute `/usr/bin/time program --foo input_1.in` etc. and note the
results. In case resource limitations are desired (e.g. limiting to 1 CPU and
60 seconds of wallclock time), the calls might be
`taskset -c 0 timeout 60s /usr/bin/time program ...` or similar.

While useful, these utilities (i.e. `time`, `ulimit`, etc.) unfortunately are
not suitable for reliable benchmarking, especially when parallelism or
sub-processes are involved, and may give you *completely wrong* results.
For further details and insights into peculiarities and pitfalls of reliable
benchmarking (as well as how BenchExec is mitigating them where possible), we
recommend the
[overview slides](https://www.sosy-lab.org/research/prs/Latest_ReliableBenchmarking.pdf)
and [the corresponding paper](https://doi.org/10.1007/s10009-017-0469-y).

BenchExec takes care of most of the underlying problems for you, which is why
we recommend using it instead. Concretely, by following this guide, you can
significantly increase the reliability of your results without much effort.

## Reliable Benchmarking with BenchExec

The following steps show you how to increase the reliability and quality of
measurements by using BenchExec instead of the standard system utilities.

### Step 1. Install BenchExec

Depending on your distribution, the setup steps vary slightly.
On Debian/Ubuntu and similar, you can
```
sudo add-apt-repository ppa:sosy-lab/benchmarking
sudo apt update && sudo apt install benchexec
```
Otherwise, try the pip-based setup
```
pip3 install --user benchexec[systemd] coloredlogs
```
Advanced users can also directly download and run the packaged python wheel
```
PYTHONPATH=/path/to/benchexec.whl python3 -m benchexec.runexecutor <the program>
```

You should be able to execute the command
`python3 -m benchexec.check_cgroups` without issues. See
[the installation guide](INSTALL.md) for further details and troubleshooting.

> Note: To run inside a Docker (or similar) container, unfortunately some
> more tinkering might be required due to how process isolation with cgroups
> works. We provide a separate
> [step-by-step guide](#benchexec-in-container.md).

### Step 2. Consider the Setup of Your Benchmark

Consider and document the benchmarking process *beforehand*. In particular,
think about which executions you want to measure, what resource limits should
be placed on the benchmarked tool(s), such as CPU time, CPU count, memory, etc.
Also consider how timeouts should be treated.

Independently of using BenchExec, we strongly recommend the following the
guidelines of the [benchmarking guide](benchmarking.md).

### Step 3. Gather Measurements using runexec

Using the example from above, suppose that we want to measure `program` on
input `input_1.in`. Then, simply execute
```
$ runexec --output output_1_foo.log -- program --foo input_1.in
```
This executes `program --foo input_1.in`, redirecting output to
`output_1_foo.log`. Then `runexec` prints relevant measurements, such as
walltime, cputime, memory, I/O, etc., to standard output in a simple to read
and parse format, for example:
```
starttime=2000-01-01T00:01:01.000001+00:00
returnvalue=0
walltime=0.0027799380040960386s
cputime=0.002098s
memory=360448B
pressure-cpu-some=0s
pressure-io-some=0s
pressure-memory-some=0s
```
See the documentation of [run results](run-results.md) for further details on
the precise meaning of these values.

In case you want to limit the process to 60s wall time, 1 GB of memory, and one
CPU core, simply execute
`runexec --walltimelimit 60s --memlimit 1GB --cores 0 ...` instead. Note that
`--cores 0` means that the process is
[pinned](https://en.wikipedia.org/wiki/Processor_affinity) to the CPU with
*number* 0, the number does not refer to the *count* of CPUs (so `--cores 2`
would mean that the process is restricted to *one* CPU core, namely that with
number 2).

The tool `runexec` offers several other features, execute `runexec --help` for
further information or refer to the [documentation](runexec.md).

## Further Resources

BenchExec provides much more beyond this core feature of reliable measurements.

The tool `benchexec` provides ways to specify the complete set of benchmarks
and allows you to execute thousands of tool / input combinations with a single
command as well as gather, aggregate, and display all the data at the same
time. See [the documentation](benchexec.md) for further details.

Additionally, `runexec` can also be accessed through a simple
[Python API](runexec.md#integration-into-other-benchmarking-frameworks) with
which you can integrate it programmatically in your framework.

Refer to the [index](INDEX.md) for further information.
