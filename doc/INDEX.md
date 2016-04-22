# BenchExec: Documentation

BenchExec consists of three programs:

- `benchexec`: main benchmarking utility
- `table-generator`: for generating result tables
- `runexec`: for benchmarking a single tool execution (can also be integrated into other benchmarking frameworks)

The documentation for BenchExec is available in the following files:

- [General installation instructions](INSTALL.md)
- [benchexec](benchexec.md)
- [table-generator](table-generator.md)
- [runexec](runexec.md)
- [Container mode](container.md) for isolating applications
- [Resource handling](resources.md) for measuring and limiting resources like time and memory

More on the background of BenchExec can also be found in our paper
[Benchmarking and Resource Measurement](http://www.sosy-lab.org/~dbeyer/Publications/2015-SPIN.Benchmarking_and_Resource_Measurement.pdf).

Additional resources such as helper scripts can be found in the directory [contrib](../contrib),
for example [files for generating plots](../contrib/plots/README.md).

Information for developers and maintainers of BenchExec is available
in the [development documentation](DEVELOPMENT.md).

## Definitions

### Units

BenchExec always uses the SI standard units:
- The base unit for time is seconds.
- The base unit for memory is bytes, and the factor for `Kilo`, `Mega`, etc. is `1000`.
  Kibibytes, Mebibytes, etc. (with a factor of 1024) are not supported.

### Glossary

- **executable**: The executable file that is used to start a tool.

- **option**: A command-line argument for a tool.

- **result file**: A file written by a tool during a run.

- **run**: A single execution of a tool.
  It consists of the full command-line arguments (including input file)
  and the resource limits,
  and produces a result including measured values for the resource consumption.

- **run definition**: A template for runs,
  which consists of the options for a tool configuration
  and will be combined with a task to define a run.

- **task**: A combination of an input file and an expected result
  that defines a problem for a tool to solve.

- **tool**: A program that should be benchmarked with BenchExec.

- **tool info**: A Python module that tells BenchExec how to execute a specific tool.

To avoid confusion with the term *run*, we never use the verb *to run*,
instead we use *execute*.
