<!--
This file is part of BenchExec, a framework for reliable benchmarking:
https://github.com/sosy-lab/benchexec

SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>

SPDX-License-Identifier: Apache-2.0
-->

# BenchExec: Documentation

BenchExec consists of three programs:

- `benchexec`: main benchmarking utility, especially for large sets of benchmark runs
- `table-generator`: for generating result tables from `benchexec` results
- `runexec`: for benchmarking a single tool execution as a simple replacement for `time`
  with better measurement accuracy and more features,
  or for integrating into other benchmarking frameworks and scripts

The documentation for BenchExec is available in the following files:

- [General installation instructions](INSTALL.md) and [setup in containerized environments](benchexec-in-container.md)
- The tools [benchexec](benchexec.md), [table-generator](table-generator.md), and [runexec](runexec.md)
- [Benchmarking guidelines](benchmarking.md) with advice for how to get reliable benchmarks
- [Container mode](container.md) for isolating applications
- [Resource handling](resources.md) for measuring and limiting resources like time and memory
- [Tool integration](tool-integration.md) for developing tool-info modules

More on the background of BenchExec can also be found in our journal paper
[Reliable Benchmarking: Requirements and Solutions](https://doi.org/10.1007/s10009-017-0469-y) (open access)
and the respective [overview slides](https://www.sosy-lab.org/research/prs/Latest_ReliableBenchmarking.pdf).

Additional resources such as helper scripts can be found in the directory [contrib](../contrib),
for example [files for generating plots](../contrib/plots/README.md).

Information for developers and maintainers of BenchExec is available
in the [development documentation](DEVELOPMENT.md).

Information for users of BenchExec on how to [integrate a tool](tool-integration.md).


## Definitions

### Units

BenchExec always uses the SI standard units:
- The base unit for time is seconds.
- The base unit for memory is bytes, and the factor for `Kilo`, `Mega`, etc. is `1000`.
  Kibibytes, Mebibytes, etc. (with a factor of 1024) are not supported.

### Glossary

- **executable**: The executable file that is used to start a tool.

- **option**: A command-line argument for a tool.

- **property (file)**: A file that tells BenchExec which task
  defined by a task definition it should select for execution,
  and also whether it should apply use-case-specific features
  such as computing a score.
  The tool info can also decide to give the property file to the tool
  in order to tell the tool what it should do with the input files.

- **result file**: A file written by a tool during a run.

- **run**: A single execution of a tool.
  It consists of the full command-line arguments (including input file(s))
  and the resource limits,
  and produces a result including measured values for the resource consumption.

- **run definition**: A template for runs,
  which consists of the options for a tool configuration
  and will be combined with a task to define a run.

- **task**: A combination of a set of input files, a property file, and an expected verdict
  that defines a problem for a tool to solve.
  A task corresponds to exactly one row in the result tables.
  Depending on what the tool supports, the set of input files can be empty.
  Properties and expected verdicts are optional.

- **task definition**: A file in [this format](https://gitlab.com/sosy-lab/benchmarking/task-definition-format)
  that describes a set of tasks
  (all of which have the same input files, but potentially different properties).

- **tool**: A program that should be benchmarked with BenchExec.

- **tool info**: A Python module that tells BenchExec how to execute a specific tool.

To avoid confusion with the term *run*, we never use the verb *to run*,
instead we use *execute*.
