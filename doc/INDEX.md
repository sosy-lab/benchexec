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


## Glossary

In BenchExec, we use the following definitions:

- **executable**: The executable file that is used to start a tool.

- **option**: A command-line argument for a tool.

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

To avoid confusion with the term *run*, we never use the verb *to run*,
instead we use *execute*.
