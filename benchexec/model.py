# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import collections.abc
import logging
import os
import re
import sys
import yaml
from xml.etree import ElementTree

from benchexec import BenchExecException
from benchexec import intel_cpu_energy
from benchexec import result
from benchexec import tooladapter
from benchexec import util


MEMLIMIT = "memlimit"
TIMELIMIT = "timelimit"
CORELIMIT = "cpuCores"

SOFTTIMELIMIT = "softtimelimit"
HARDTIMELIMIT = "hardtimelimit"
WALLTIMELIMIT = "walltimelimit"

_BYTE_FACTOR = 1000  # byte in kilobyte

_ERROR_RESULTS_FOR_TERMINATION_REASON = {
    "cputime": result.RESULT_TIMEOUT,
    "cputime-soft": result.RESULT_TIMEOUT,
    "walltime": result.RESULT_TIMEOUT,
    "memory": "OUT OF MEMORY",
    "killed": "KILLED",
    "failed": "FAILED",
    "files-count": "FILES-COUNT LIMIT",
    "files-size": "FILES-SIZE LIMIT",
}

_EXPECTED_RESULT_FILTER_VALUES = {True: "true", False: "false", None: "unknown"}
_WARNED_ABOUT_UNSUPPORTED_EXPECTED_RESULT_FILTER = False

_TASK_DEF_VERSIONS = frozenset(["0.1", "1.0", "2.0"])


def substitute_vars(oldList, runSet=None, task_file=None):
    """
    This method replaces special substrings from a list of string
    and return a new list.
    """
    keyValueList = []
    if runSet:
        benchmark = runSet.benchmark

        # list with tuples (key, value): 'key' is replaced by 'value'
        keyValueList = [
            ("benchmark_name", benchmark.name),
            ("benchmark_date", benchmark.instance),
            ("benchmark_path", benchmark.base_dir or "."),
            ("benchmark_path_abs", os.path.abspath(benchmark.base_dir)),
            ("benchmark_file", os.path.basename(benchmark.benchmark_file)),
            (
                "benchmark_file_abs",
                os.path.abspath(os.path.basename(benchmark.benchmark_file)),
            ),
            ("logfile_path", os.path.dirname(runSet.log_folder) or "."),
            ("logfile_path_abs", os.path.abspath(runSet.log_folder)),
            ("rundefinition_name", runSet.real_name if runSet.real_name else ""),
            ("test_name", runSet.real_name if runSet.real_name else ""),
        ]

    if task_file:
        var_prefix = "taskdef_" if task_file.endswith(".yml") else "inputfile_"
        keyValueList.append((var_prefix + "name", os.path.basename(task_file)))
        keyValueList.append((var_prefix + "path", os.path.dirname(task_file) or "."))
        keyValueList.append(
            (var_prefix + "path_abs", os.path.dirname(os.path.abspath(task_file)))
        )

    # do not use keys twice
    assert len({key for (key, value) in keyValueList}) == len(keyValueList)

    return [util.substitute_vars(s, keyValueList) for s in oldList]


def load_task_definition_file(task_def_file):
    """Open and parse a task-definition file in YAML format."""
    try:
        with open(task_def_file) as f:
            task_def = yaml.safe_load(f)
    except OSError as e:
        raise BenchExecException(f"Cannot open task-definition file: {e}")
    except yaml.YAMLError as e:
        raise BenchExecException(f"Invalid task definition: {e}")

    if not task_def:
        raise BenchExecException("Invalid task definition: empty file " + task_def_file)

    format_version = str(task_def.get("format_version"))
    if format_version not in _TASK_DEF_VERSIONS:
        raise BenchExecException(
            f"Task-definition file {task_def_file} specifies "
            f"invalid format_version '{task_def.get('format_version')}'."
        )

    if format_version != "2.0" and "options" in task_def:
        raise BenchExecException(
            f"Task-definition file {task_def_file} specifies invalid key 'options', "
            f"format_version needs to be at least 2.0 for this."
        )

    return task_def


def handle_files_from_task_definition(patterns, task_def_file):
    """
    Handle content of a key like input_files in a task-definition file and return list
    of matching files.
    @param patterns: the content of such a key (None, list, or string)
    @param task_def_file: name of task-definition file
    """
    if patterns is None:
        return []
    result = []
    if isinstance(patterns, str) or not isinstance(patterns, collections.abc.Iterable):
        # accept single string in addition to list of strings
        patterns = [patterns]
    for pattern in patterns:
        expanded = util.expand_filename_pattern(
            str(pattern), os.path.dirname(task_def_file)
        )
        if not expanded:
            raise BenchExecException(
                f"Pattern '{pattern}' in task-definition file {task_def_file} "
                f"did not match any paths."
            )
        expanded.sort()
        result.extend(expanded)
    return result


def load_tool_info(tool_name: str, config):
    """
    Load the tool-info class.
    @param tool_name: The name of the tool-info module.
    Either a full Python package name or a name within the benchexec.tools package.
    @return: A tuple of the full name of the used tool-info module and an instance of the tool-info class.
    """
    tool_module = tool_name if "." in tool_name else f"benchexec.tools.{tool_name}"
    try:
        if config.container:
            # lazy import because it can fail if container mode is not supported
            from benchexec import containerized_tool

            tool = containerized_tool.ContainerizedTool(tool_module, config)
        else:
            tool = __import__(tool_module, fromlist=["Tool"]).Tool()
            tool = tooladapter.adapt_to_current_version(tool)
    except ImportError as ie:
        logging.debug(
            "Did not find module '%s'. "
            "Python probably looked for it in one of the following paths:\n  %s",
            tool_module,
            "\n  ".join(path or "." for path in sys.path),
        )
        sys.exit(f'Unsupported tool "{tool_name}" specified. ImportError: {ie}')
    except AttributeError as ae:
        sys.exit(
            f'Unsupported tool "{tool_name}" specified, class "Tool" is missing: {ae}'
        )
    except TypeError as te:
        sys.exit(f'Unsupported tool "{tool_name}" specified. TypeError: {te}')
    assert isinstance(tool, tooladapter.CURRENT_BASETOOL)
    return tool_module, tool


def cmdline_for_run(
    tool,
    executable,
    options,
    sourcefiles,
    identifier,
    propertyfile,
    task_options,
    rlimits,
):
    working_directory = tool.working_directory(executable)

    def relpath(path):
        return path if os.path.isabs(path) else os.path.relpath(path, working_directory)

    rel_executable = relpath(executable)
    if os.path.sep not in rel_executable:
        rel_executable = os.path.join(os.curdir, rel_executable)

    task = tooladapter.CURRENT_BASETOOL.Task(
        input_files=map(relpath, sourcefiles),
        identifier=None if sourcefiles else identifier,  # only for <withoutfile>
        property_file=relpath(propertyfile) if propertyfile else None,
        options=task_options,
    )

    args = tool.cmdline(rel_executable, list(options), task, rlimits)
    assert all(args), f"Tool cmdline contains empty or None argument: {args}"
    args = [os.path.expandvars(arg) for arg in args]
    args = [os.path.expanduser(arg) for arg in args]
    return args


def get_propertytag(parent):
    tag = util.get_single_child_from_xml(parent, "propertyfile")
    if tag is None:
        return None
    expected_verdict = tag.get("expectedverdict")
    if (
        expected_verdict is not None
        and expected_verdict not in _EXPECTED_RESULT_FILTER_VALUES.values()
        and not re.match("false(.*)", expected_verdict)
    ):
        raise BenchExecException(
            f"Invalid value '{expected_verdict}' for expectedverdict of <propertyfile> "
            f"in tag <{parent.tag}>: "
            f"Only 'true', 'false', 'false(<subproperty>)' and 'unknown' are allowed!"
        )
    return tag


class Benchmark(object):
    """
    The class Benchmark manages the import of source files, options, columns and
    the tool from a benchmark_file.
    This class represents the <benchmark> tag.
    """

    def __init__(self, benchmark_file, config, start_time):
        """
        The constructor of Benchmark reads the source files, options, columns and the tool
        from the XML in the benchmark_file..
        """
        logging.debug("I'm loading the benchmark %s.", benchmark_file)

        self.config = config
        self.benchmark_file = benchmark_file
        self.base_dir = os.path.dirname(self.benchmark_file)

        # get benchmark-name
        self.name = os.path.basename(benchmark_file)[:-4]  # remove ending ".xml"
        if config.name:
            self.name += "." + config.name

        self.description = None
        if config.description_file is not None:
            try:
                self.description = util.read_file(config.description_file)
            except (OSError, UnicodeDecodeError) as e:
                raise BenchExecException(
                    f"File '{config.description_file}' given for description "
                    f"could not be read: {e}"
                )

        self.start_time = start_time
        self.instance = start_time.strftime(util.TIMESTAMP_FILENAME_FORMAT)

        self.output_base_name = f"{config.output_path}{self.name}.{self.instance}"
        self.log_folder = f"{self.output_base_name}.logfiles{os.path.sep}"
        self.log_zip = f"{self.output_base_name}.logfiles.zip"
        self.result_files_folder = f"{self.output_base_name}.files"

        # parse XML
        try:
            rootTag = ElementTree.ElementTree().parse(benchmark_file)
        except ElementTree.ParseError as e:
            sys.exit(f"Benchmark file {benchmark_file} is invalid: {e}")
        if "benchmark" != rootTag.tag:
            sys.exit(
                f"Benchmark file {benchmark_file} is invalid: "
                f"Its root element is not named 'benchmark'."
            )

        # get tool
        tool_name = rootTag.get("tool")
        if not tool_name:
            sys.exit("A tool needs to be specified in the benchmark definition file.")
        (self.tool_module, self.tool) = load_tool_info(tool_name, config)
        self.tool_name = self.tool.name()
        # will be set from the outside if necessary (may not be the case in SaaS environments)
        self.tool_version = None
        self.executable = None
        self.display_name = rootTag.get("displayName")

        def parse_memory_limit(value):
            # In a future BenchExec version, we could treat unit-less limits as bytes
            try:
                value = int(value)
            except ValueError:
                return util.parse_memory_value(value)
            else:
                raise ValueError(
                    f"Memory limit must have a unit suffix, e.g., '{value} MB'"
                )

        rlimits = {}

        def handle_limit_value(name, from_key, to_key, cmdline_value, parse_fn):
            value = rootTag.get(from_key, None)
            # override limit from XML with values from command line
            if cmdline_value is not None:
                if cmdline_value.strip() == "-1":  # infinity
                    value = None
                else:
                    value = cmdline_value

            if value is not None:
                try:
                    rlimits[to_key] = parse_fn(value)
                except ValueError as e:
                    sys.exit(f"Invalid value for {name.lower()} limit: {e}")
                if rlimits[to_key] <= 0:
                    sys.exit(
                        f'{name} limit "{value}" is invalid, '
                        f"it needs to be a positive number "
                        f"(or -1 on the command line for disabling it)."
                    )

        handle_limit_value(
            "Time", TIMELIMIT, "cputime", config.timelimit, util.parse_timespan_value
        )
        handle_limit_value(
            "Hard time",
            HARDTIMELIMIT,
            "cputime_hard",
            config.timelimit,
            util.parse_timespan_value,
        )
        handle_limit_value(
            "Wall time",
            WALLTIMELIMIT,
            "walltime",
            config.walltimelimit,
            util.parse_timespan_value,
        )
        handle_limit_value(
            "Memory", MEMLIMIT, "memory", config.memorylimit, parse_memory_limit
        )
        handle_limit_value("Core", CORELIMIT, "cpu_cores", config.corelimit, int)

        self.rlimits = tooladapter.CURRENT_BASETOOL.ResourceLimits(**rlimits)

        if self.rlimits.cputime:
            if self.rlimits.cputime_hard:
                # if both cputime and cputime_hard are given, might need to adjust
                if self.rlimits.cputime_hard < self.rlimits.cputime:
                    logging.warning(
                        "Hard timelimit %d is smaller than timelimit %d, ignoring the former.",
                        self.rlimits.cputime_hard,
                        self.rlimits.cputime,
                    )
                    self.rlimits = self.rlimits._replace(
                        cputime_hard=self.rlimits.cputime
                    )
            else:
                # if only cputime is given, set cputime_hard to same value
                self.rlimits = self.rlimits._replace(cputime_hard=self.rlimits.cputime)
        elif self.rlimits.cputime_hard:
            # if only cputime_hard is given, set cputime to same value
            self.rlimits = self.rlimits._replace(cputime=self.rlimits.cputime_hard)

        self.num_of_threads = int(rootTag.get("threads", 1))
        if config.num_of_threads is not None:
            self.num_of_threads = config.num_of_threads
        if self.num_of_threads < 1:
            logging.error("At least ONE thread must be given!")
            sys.exit()

        # get global options and property file
        self.options = util.get_list_from_xml(rootTag)
        self.propertytag = get_propertytag(rootTag)

        # get columns
        self.columns = Benchmark.load_columns(rootTag.find("columns"))

        # get global source files, they are used in all run sets
        if rootTag.findall("sourcefiles"):
            sys.exit(
                f"Benchmark file {benchmark_file} has unsupported old format. "
                f"Rename <sourcefiles> tags to <tasks>."
            )
        globalSourcefilesTags = rootTag.findall("tasks")

        # get required files
        self._required_files = set()
        for required_files_tag in rootTag.findall("requiredfiles"):
            required_files = util.expand_filename_pattern(
                required_files_tag.text, self.base_dir
            )
            if not required_files:
                logging.warning(
                    "Pattern %s in requiredfiles tag did not match any file.",
                    required_files_tag.text,
                )
            self._required_files = self._required_files.union(required_files)

        # get requirements
        self.requirements = Requirements(
            rootTag.findall("require"), self.rlimits, config
        )

        result_files_tags = rootTag.findall("resultfiles")
        if result_files_tags:
            self.result_files_patterns = [
                os.path.normpath(p.text) for p in result_files_tags if p.text
            ]
            for pattern in self.result_files_patterns:
                if pattern.startswith(".."):
                    sys.exit(f"Invalid relative result-files pattern '{pattern}'.")
        else:
            # default is "everything below current directory"
            self.result_files_patterns = ["."]

        # get benchmarks
        self.run_sets = []
        for i, rundefinitionTag in enumerate(rootTag.findall("rundefinition")):
            self.run_sets.append(
                RunSet(rundefinitionTag, self, i + 1, globalSourcefilesTags)
            )

        if not self.run_sets:
            logging.warning(
                "Benchmark file %s specifies no runs to execute "
                "(no <rundefinition> tags found).",
                benchmark_file,
            )

        if not any(runSet.should_be_executed() for runSet in self.run_sets):
            logging.warning(
                "No <rundefinition> tag selected, nothing will be executed."
            )
            if config.selected_run_definitions:
                logging.warning(
                    "The selection %s does not match any run definitions of %s.",
                    config.selected_run_definitions,
                    [runSet.real_name for runSet in self.run_sets],
                )
        elif config.selected_run_definitions:
            for selected in config.selected_run_definitions:
                if not any(
                    util.wildcard_match(run_set.real_name, selected)
                    for run_set in self.run_sets
                ):
                    logging.warning(
                        'The selected run definition "%s" is not present in the input file, '
                        "skipping it.",
                        selected,
                    )

    def required_files(self):
        assert self.executable is not None, "executor needs to set tool executable"
        return self._required_files.union(self.tool.program_files(self.executable))

    def working_directory(self):
        assert self.executable is not None, "executor needs to set tool executable"
        return self.tool.working_directory(self.executable)

    def environment(self):
        assert self.executable is not None, "executor needs to set tool executable"
        return self.tool.environment(self.executable)

    @staticmethod
    def load_columns(columnsTag):
        """
        @param columnsTag: the columnsTag from the XML file
        @return: a list of Columns()
        """

        logging.debug("I'm loading some columns for the outputfile.")
        columns = []
        if columnsTag is not None:  # columnsTag is optional in XML file
            for columnTag in columnsTag.findall("column"):
                pattern = columnTag.text
                title = columnTag.get("title", pattern)
                number_of_digits = columnTag.get("numberOfDigits")
                column = Column(pattern, title, number_of_digits)
                columns.append(column)
                logging.debug(
                    'Column "%s" with title "%s" loaded from XML file.',
                    column.text,
                    column.title,
                )
        return columns


class RunSet(object):
    """
    The class RunSet manages the import of files and options of a run set.
    """

    def __init__(self, rundefinitionTag, benchmark, index, globalSourcefilesTags=[]):
        """
        The constructor of RunSet reads run-set name and the source files from rundefinitionTag.
        Source files can be included or excluded, and imported from a list of
        names in another file. Wildcards and variables are expanded.
        @param rundefinitionTag: a rundefinitionTag from the XML file
        """

        self.benchmark = benchmark

        # get name of run set, name is optional, the result can be "None"
        self.real_name = rundefinitionTag.get("name")

        # index is the number of the run set
        self.index = index

        self.log_folder = benchmark.log_folder
        self.result_files_folder = benchmark.result_files_folder
        if self.real_name:
            self.log_folder += self.real_name + "."
            self.result_files_folder = os.path.join(
                self.result_files_folder, self.real_name
            )

        # get all run-set-specific options from rundefinitionTag
        self.options = benchmark.options + util.get_list_from_xml(rundefinitionTag)
        self.propertytag = get_propertytag(rundefinitionTag)
        if self.propertytag is None:
            self.propertytag = benchmark.propertytag

        # get run-set specific required files
        required_files_pattern = {
            tag.text for tag in rundefinitionTag.findall("requiredfiles")
        }

        # get all runs, a run contains one sourcefile with options
        if rundefinitionTag.findall("sourcefiles"):
            sys.exit(
                f"Benchmark file {benchmark.benchmark_file} has unsupported old format. "
                f"Rename <sourcefiles> tags to <tasks>."
            )
        self.blocks = self.extract_runs_from_xml(
            globalSourcefilesTags + rundefinitionTag.findall("tasks"),
            required_files_pattern,
            self.real_name,
        )
        self.runs = [run for block in self.blocks for run in block.runs]

        names = [self.real_name]
        if len(self.blocks) == 1:
            # there is exactly one source-file set to run, append its name to run-set name
            names.append(self.blocks[0].real_name)
        self.name = ".".join(filter(None, names))
        self.full_name = self.benchmark.name + (f".{self.name}" if self.name else "")

        # Currently we store logfiles as "basename.log",
        # so we cannot distinguish sourcefiles in different folder with same basename.
        # For a 'local benchmark' this causes overriding of logfiles after reading them,
        # so the result is correct, only the logfile is gone.
        # For 'cloud-mode' the logfile is overridden before reading it,
        # so the result will be wrong and every measured value will be missing.
        if self.should_be_executed():
            sourcefilesSet = set()
            for run in self.runs:
                base = os.path.basename(run.identifier)
                if base in sourcefilesSet:
                    logging.warning(
                        "Input file with name '%s' appears twice in run definition. "
                        "This could cause problems with equal logfile-names.",
                        base,
                    )
                else:
                    sourcefilesSet.add(base)
            del sourcefilesSet

    def should_be_executed(self):
        return not self.benchmark.config.selected_run_definitions or any(
            util.wildcard_match(self.real_name, run_definition)
            for run_definition in self.benchmark.config.selected_run_definitions
        )

    def extract_runs_from_xml(
        self, sourcefilesTagList, global_required_files_pattern, rundef_name
    ):
        """
        This function builds a list of SourcefileSets (containing filename with options).
        The files and their options are taken from the list of sourcefilesTags.
        """
        base_dir = self.benchmark.base_dir
        # runs are structured as sourcefile sets, one set represents one sourcefiles tag
        blocks = []

        for index, sourcefilesTag in enumerate(sourcefilesTagList):
            sourcefileSetName = sourcefilesTag.get("name")
            matchName = sourcefileSetName or str(index)
            if self.benchmark.config.selected_sourcefile_sets and not any(
                util.wildcard_match(matchName, sourcefile_set)
                for sourcefile_set in self.benchmark.config.selected_sourcefile_sets
            ):
                continue

            required_files_pattern = global_required_files_pattern.union(
                {tag.text for tag in sourcefilesTag.findall("requiredfiles")}
            )

            # get lists of filenames
            task_def_files = self.get_task_def_files_from_xml(sourcefilesTag, base_dir)

            # get file-specific options for filenames
            fileOptions = util.get_list_from_xml(sourcefilesTag)
            local_propertytag = get_propertytag(sourcefilesTag)

            # some runs need more than one sourcefile,
            # the first sourcefile is a normal 'include'-file, we use its name as identifier
            # for logfile and result-category all other files are 'append'ed.
            appendFileTags = sourcefilesTag.findall("append")

            currentRuns = []
            for identifier in task_def_files:
                if identifier.endswith(".yml"):
                    if appendFileTags:
                        raise BenchExecException(
                            "Cannot combine <append> and task-definition files in the same <tasks> tag."
                        )
                    run = self.create_run_from_task_definition(
                        identifier,
                        fileOptions,
                        local_propertytag,
                        required_files_pattern,
                    )
                else:
                    run = self.create_run_for_input_file(
                        identifier,
                        fileOptions,
                        local_propertytag,
                        required_files_pattern,
                        appendFileTags,
                    )
                if run:
                    currentRuns.append(run)

            # add runs for cases without source files
            for run in sourcefilesTag.findall("withoutfile"):
                currentRuns.append(
                    Run(
                        run.text,
                        [],
                        None,
                        fileOptions,
                        self,
                        local_propertytag,
                        required_files_pattern,
                    )
                )

            blocks.append(SourcefileSet(sourcefileSetName, index, currentRuns))

        if self.benchmark.config.selected_sourcefile_sets:
            for selected in self.benchmark.config.selected_sourcefile_sets:
                if not any(
                    util.wildcard_match(sourcefile_set.real_name, selected)
                    for sourcefile_set in blocks
                ):
                    logging.warning(
                        'For run definition "%s" the selected tasks "%s" '
                        "do not exist in the benchmark definition, skipping them.",
                        rundef_name,
                        selected,
                    )
        return blocks

    def get_task_def_files_from_xml(self, sourcefilesTag, base_dir):
        """Get the task-definition files from the XML definition. Task-definition files are files
        for which we create a run (typically an input file or a YAML task definition).
        """
        # Use dict as convenient set with insertion order, values are always None.
        taskdefs = {}

        def add_to_taskdefs(keys):
            for key in keys:
                taskdefs[key] = None

        def remove_from_taskdefs(keys):
            for key in keys:
                taskdefs.pop(key, None)

        def _read_set_file(filename):
            dirname = os.path.dirname(filename)
            with open(filename, "rt") as f:
                for line in f:
                    line = line.strip()  # necessary to remove line separator
                    # ignore comments and empty lines
                    if not util.is_comment(line):
                        yield from self.expand_filename_pattern(line, dirname)

        # get included taskdefs
        for includedFiles in sourcefilesTag.findall("include"):
            add_to_taskdefs(self.expand_filename_pattern(includedFiles.text, base_dir))

        # get taskdefs from list in file
        for includesFilesFile in sourcefilesTag.findall("includesfile"):
            for file in self.expand_filename_pattern(includesFilesFile.text, base_dir):
                input_files_in_set = list(_read_set_file(file))
                if not input_files_in_set:
                    sys.exit(
                        f"Error: Nothing in includes file '{file}' "
                        f"matches existing files."
                    )
                add_to_taskdefs(input_files_in_set)

        # remove excluded taskdefs
        for excludedFiles in sourcefilesTag.findall("exclude"):
            old_size = len(taskdefs)
            remove_from_taskdefs(
                self.expand_filename_pattern(excludedFiles.text, base_dir)
            )
            if old_size == len(taskdefs):
                logging.warning(
                    "The exclude pattern '%s' did not match any of the included tasks.",
                    excludedFiles.text,
                )

        for excludesFilesFile in sourcefilesTag.findall("excludesfile"):
            for file in self.expand_filename_pattern(excludesFilesFile.text, base_dir):
                old_size = len(taskdefs)
                remove_from_taskdefs(_read_set_file(file))
                if old_size == len(taskdefs):
                    logging.warning(
                        "The exclude file '%s' did not match any of the included tasks.",
                        file,
                    )

        return list(taskdefs)

    def create_run_for_input_file(
        self,
        input_file,
        options,
        local_propertytag,
        required_files_pattern,
        append_file_tags,
    ):
        """Create a Run from a direct definition of the main input file (without task definition)"""
        input_files = [input_file]
        base_dir = os.path.dirname(input_file)
        for append_file in append_file_tags:
            input_files.extend(
                self.expand_filename_pattern(
                    append_file.text, base_dir, sourcefile=input_file
                )
            )

        run = Run(
            input_file,
            util.get_files(input_files),  # expand directories to get their sub-files
            None,
            options,
            self,
            local_propertytag,
            required_files_pattern,
        )

        if not run.propertyfile:
            return run

        prop = result.Property.create(run.propertyfile)
        run.properties = [prop]

        if run.propertytag.get("expectedverdict"):
            global _WARNED_ABOUT_UNSUPPORTED_EXPECTED_RESULT_FILTER
            if not _WARNED_ABOUT_UNSUPPORTED_EXPECTED_RESULT_FILTER:
                _WARNED_ABOUT_UNSUPPORTED_EXPECTED_RESULT_FILTER = True
                logging.warning(
                    "Ignoring filter based on expected verdict "
                    "for tasks without task-definition file. "
                    "Expected verdicts for such tasks will be removed in BenchExec 3.0 "
                    "(cf. https://github.com/sosy-lab/benchexec/issues/439)."
                )

        return run

    def create_run_from_task_definition(
        self, task_def_file, options, local_propertytag, required_files_pattern
    ):
        """Create a Run from a task definition in yaml format"""
        task_def = load_task_definition_file(task_def_file)

        input_files = handle_files_from_task_definition(
            task_def.get("input_files"), task_def_file
        )
        if not input_files:
            raise BenchExecException(
                f"Task-definition file {task_def_file} does not define any input files."
            )
        required_files = handle_files_from_task_definition(
            task_def.get("required_files"), task_def_file
        )

        run = Run(
            task_def_file,
            input_files,
            task_def.get("options"),
            options,
            self,
            local_propertytag,
            required_files_pattern,
            required_files,
        )

        # run.propertyfile of Run is fully determined only after Run is created,
        # thus we handle it and the expected results here.
        if not run.propertyfile:
            return run

        # TODO: support "property_name" attribute in yaml
        prop = result.Property.create(run.propertyfile)
        run.properties = [prop]

        for prop_dict in task_def.get("properties", []):
            if not isinstance(prop_dict, dict) or "property_file" not in prop_dict:
                raise BenchExecException(
                    f"Missing property file for property "
                    f"in task-definition file {task_def_file}."
                )
            expanded = util.expand_filename_pattern(
                prop_dict["property_file"], os.path.dirname(task_def_file)
            )
            if len(expanded) != 1:
                raise BenchExecException(
                    f"Property pattern '{prop_dict['property_file']}' "
                    f"in task-definition file {task_def_file} "
                    f"does not refer to exactly one file."
                )

            # TODO We could reduce I/O by checking absolute paths and using os.path.samestat
            # with cached stat calls.
            if prop.filename == expanded[0] or os.path.samefile(
                prop.filename, expanded[0]
            ):
                expected_result = prop_dict.get("expected_verdict")
                if expected_result is not None and not isinstance(
                    expected_result, bool
                ):
                    raise BenchExecException(
                        f"Invalid expected result '{expected_result}' "
                        f"for property {prop_dict['property_file']} "
                        f"in task-definition file {task_def_file}."
                    )
                run.expected_results[prop.filename] = result.ExpectedResult(
                    expected_result, prop_dict.get("subproperty")
                )

        if not run.expected_results:
            logging.debug(
                "Ignoring run '%s' because it does not have the property from %s.",
                run.identifier,
                run.propertyfile,
            )
            return None
        elif len(run.expected_results) > 1:
            raise BenchExecException(
                f"Property '{prop.filename}' specified multiple times "
                f"in task-definition file {task_def_file}."
            )
        assert len(run.expected_results) == 1

        expected_result_filter = run.propertytag.get("expectedverdict")
        # Valid value of expected_result_filter has been confirmed before.
        if expected_result_filter is not None:
            expected_result = next(iter(run.expected_results.values()))
            expected_result_str = _EXPECTED_RESULT_FILTER_VALUES[expected_result.result]
            if (
                expected_result.result is False
                and expected_result.subproperty
                and "(" in expected_result_filter
            ):
                expected_result_str += f"({expected_result.subproperty})"
            if expected_result_str != expected_result_filter:
                logging.debug(
                    "Ignoring run '%s' because "
                    "it does not have the expected verdict '%s' for %s.",
                    run.identifier,
                    expected_result_filter,
                    prop,
                )
                return None

        return run

    def expand_filename_pattern(self, pattern, base_dir, sourcefile=None):
        """
        The function expand_filename_pattern expands a filename pattern to a sorted list
        of filenames. The pattern can contain variables and wildcards.
        If base_dir is given and pattern is not absolute, base_dir and pattern are joined.
        """

        # replace vars like ${benchmark_path},
        # with converting to list and back, we can use the function 'substitute_vars()'
        expandedPattern = substitute_vars([pattern], self, sourcefile)
        assert len(expandedPattern) == 1
        expandedPattern = expandedPattern[0]

        if expandedPattern != pattern:
            logging.debug(
                "Expanded variables in expression %r to %r.", pattern, expandedPattern
            )

        fileList = util.expand_filename_pattern(expandedPattern, base_dir)

        # sort alphabetical,
        fileList.sort()

        if not fileList:
            logging.warning("No files found matching %r.", pattern)

        return fileList


class SourcefileSet(object):
    """
    A SourcefileSet contains a list of runs and a name.
    """

    def __init__(self, name, index, runs):
        self.real_name = name  # this name is optional
        self.name = name or str(index)  # this name is always non-empty
        self.runs = runs


_logged_missing_property_files = set()


class Run(object):
    """
    A Run contains some sourcefile, some options, propertyfiles and some other stuff, that is needed for the Run.
    """

    def __init__(
        self,
        identifier,
        sourcefiles,
        task_options,
        fileOptions,
        runSet,
        local_propertytag=None,
        required_files_patterns=[],
        required_files=[],
        expected_results={},
    ):
        # identifier is used for name of logfile, substitution, result-category
        assert identifier
        self.identifier = identifier
        self.sourcefiles = sourcefiles
        self.task_options = task_options
        self.runSet = runSet
        self.specific_options = fileOptions  # options that are specific for this run
        self.log_file = f"{runSet.log_folder}{os.path.basename(self.identifier)}.log"
        self.result_files_folder = os.path.join(
            runSet.result_files_folder, os.path.basename(self.identifier)
        )
        self.expected_results = expected_results or {}  # filled externally

        self.required_files = set(required_files)
        rel_sourcefile = os.path.relpath(self.identifier, runSet.benchmark.base_dir)
        for pattern in required_files_patterns:
            this_required_files = runSet.expand_filename_pattern(
                pattern, runSet.benchmark.base_dir, rel_sourcefile
            )
            if not this_required_files:
                logging.warning(
                    "Pattern %s in requiredfiles tag did not match any file for task %s.",
                    pattern,
                    self.identifier,
                )
            self.required_files.update(this_required_files)

        # combine all options to be used when executing this run
        # (reduce memory-consumption: if 2 lists are equal, do not use the second one)
        self.options = runSet.options + fileOptions if fileOptions else runSet.options
        substitutedOptions = substitute_vars(self.options, runSet, self.identifier)
        if substitutedOptions != self.options:
            self.options = substitutedOptions  # for less memory again

        self.propertytag = (
            local_propertytag if local_propertytag is not None else runSet.propertytag
        )
        self.propertyfile = util.text_or_none(self.propertytag)
        self.properties = []  # filled externally

        def log_property_file_once(msg):
            if self.propertyfile not in _logged_missing_property_files:
                _logged_missing_property_files.add(self.propertyfile)
                logging.warning(msg)

        # replace run-specific stuff in the propertyfile and add it to the set of required files
        if self.propertyfile is None:
            log_property_file_once(
                "No propertyfile specified. Score computation will ignore the results."
            )
        else:
            # we check two cases: direct filename or user-defined substitution, one of them must be a 'file'
            # TODO: do we need the second case? it is equal to previous used option "-spec ${inputfile_path}/ALL.prp"
            expandedPropertyFiles = util.expand_filename_pattern(
                self.propertyfile, self.runSet.benchmark.base_dir
            )
            substitutedPropertyfiles = substitute_vars(
                [self.propertyfile], runSet, self.identifier
            )
            assert len(substitutedPropertyfiles) == 1

            if expandedPropertyFiles:
                if len(expandedPropertyFiles) > 1:
                    log_property_file_once(
                        f"Pattern {self.propertyfile} for input file {self.identifier} "
                        f"in propertyfile tag matches more than one file. "
                        f"Only {expandedPropertyFiles[0]} will be used."
                    )
                self.propertyfile = expandedPropertyFiles[0]
            elif substitutedPropertyfiles and os.path.isfile(
                substitutedPropertyfiles[0]
            ):
                self.propertyfile = substitutedPropertyfiles[0]
            else:
                # It seems there is no way to get the line number of a tag?
                tag = ElementTree.tostring(self.propertytag, encoding="unicode").strip()
                raise BenchExecException(
                    f"The pattern for the propertyfile in tag {tag} "
                    f"of the benchmark definition does not match any file."
                )

        if self.propertyfile:
            self.required_files.add(self.propertyfile)

        self.required_files = list(self.required_files)

        # Copy columns for having own objects in run
        # (we need this for storing the results in them).
        self.columns = [
            Column(c.text, c.title, c.number_of_digits)
            for c in self.runSet.benchmark.columns
        ]

        # here we store the optional result values, e.g. memory usage, energy, host name
        # keys need to be strings, if first character is "@" the value is marked as hidden (e.g., debug info)
        self.values = {}

        # dummy values, for output in case of interrupt
        self.status = ""
        self.category = result.CATEGORY_UNKNOWN

    def cmdline(self):
        assert (
            self.runSet.benchmark.executable is not None
        ), "executor needs to set tool executable"
        self._cmdline = cmdline_for_run(
            self.runSet.benchmark.tool,
            self.runSet.benchmark.executable,
            self.options,
            self.sourcefiles,
            self.identifier,
            self.propertyfile,
            self.task_options,
            self.runSet.benchmark.rlimits,
        )
        return self._cmdline

    def set_result(self, values, visible_columns={}):
        """Set the result of this run.
        @param values: a dictionary with result values as returned by RunExecutor.execute_run(),
            may also contain arbitrary additional values
        @param visible_columns: a set of keys of values that should be visible by default
            (i.e., not marked as hidden), apart from those that BenchExec shows by default anyway
        """
        exitcode = values.pop("exitcode", None)
        if exitcode is not None:
            if exitcode.signal:
                self.values["@exitsignal"] = exitcode.signal
            else:
                self.values["@returnvalue"] = exitcode.value

        for key, value in values.items():
            if key == "cpuenergy" and not isinstance(value, (str, bytes)):
                energy = intel_cpu_energy.format_energy_results(value)
                for energy_key, energy_value in energy.items():
                    if energy_key != "cpuenergy":
                        energy_key = "@" + energy_key
                    self.values[energy_key] = energy_value
            elif key in ["walltime", "cputime", "memory", "cpuenergy"]:
                self.values[key] = value
            elif key in visible_columns:
                self.values[key] = value
            else:
                self.values["@" + key] = value

        termination_reason = values.get("terminationreason")

        # read output
        try:
            with open(self.log_file, "rt", errors="ignore") as outputFile:
                output = outputFile.readlines()
                # first 6 lines are for logging, rest is output of subprocess, see runexecutor.py for details
                output = output[6:]
        except OSError as e:
            logging.warning("Cannot read log file: %s", e.strerror)
            output = []
        output = tooladapter.CURRENT_BASETOOL.RunOutput(output)

        self.status = self._analyze_result(exitcode, output, termination_reason)
        self.category = result.get_result_category(
            self.expected_results, self.status, self.properties
        )

        for column in self.columns:
            substitutedColumnText = substitute_vars(
                [column.text], self.runSet, self.sourcefiles[0]
            )[0]
            column.value = self.runSet.benchmark.tool.get_value_from_output(
                output, substitutedColumnText
            )

    def _analyze_result(self, exitcode, output, termination_reason):
        """Return status according to result and output of tool."""

        # Ask tool info.
        tool_status = None
        if exitcode is not None:
            logging.debug("My subprocess returned %s.", exitcode)
            tool_status = self.runSet.benchmark.tool.determine_result(
                tooladapter.CURRENT_BASETOOL.Run(
                    self._cmdline, exitcode, output, termination_reason
                )
            )

            if tool_status in result.RESULT_LIST_OTHER:
                # for unspecific results provide some more information if possible
                if exitcode.signal == 6:
                    tool_status = "ABORTED"
                elif exitcode.signal == 11:
                    tool_status = "SEGMENTATION FAULT"
                elif exitcode.signal == 15:
                    tool_status = "KILLED"
                elif exitcode.signal:
                    tool_status = f"KILLED BY SIGNAL {exitcode.signal}"

                elif exitcode.value and tool_status != result.RESULT_UNKNOWN:
                    tool_status = f"{result.RESULT_ERROR} ({exitcode.value})"

        # Tools sometimes produce a result even after violating a resource limit.
        # This should not be counted, so we overwrite the result with TIMEOUT/OOM
        # here, if this is the case.
        # However, we don't want to forget more specific results like SEGFAULT,
        # so we do this only if the result is a "normal" one like TRUE/FALSE
        # or an unspecific one like UNKNOWN/ERROR.
        status = None
        if self._is_timeout():
            # Termination reason was not fully precise for timeouts, so we double check
            # the consumed time against the limits. Since removal of ulimit time limit
            # this should not be necessary, but also does not harm.
            status = result.RESULT_TIMEOUT
        elif termination_reason:
            status = _ERROR_RESULTS_FOR_TERMINATION_REASON.get(
                termination_reason, termination_reason
            )

        if not status:
            # regular termination
            status = tool_status
        elif tool_status and tool_status not in (
            result.RESULT_LIST_OTHER + [status, "KILLED", "KILLED BY SIGNAL 9"]
        ):
            # timeout/OOM but tool still returned some result
            status = f"{status} ({tool_status})"

        return status

    def _is_timeout(self):
        """try to find out whether the tool terminated because of a timeout"""
        rlimits = self.runSet.benchmark.rlimits
        cputime = self.values.get("cputime")
        walltime = self.values.get("walltime")

        is_cpulimit = cputime and rlimits.cputime and cputime > rlimits.cputime
        is_walllimit = walltime and rlimits.walltime and walltime > rlimits.walltime

        return is_cpulimit or is_walllimit


class Column(object):
    """
    The class Column contains text, title and number_of_digits of a column.
    """

    def __init__(self, text, title, numOfDigits):
        self.text = text
        self.title = title
        self.number_of_digits = numOfDigits
        self.value = ""


class Requirements(object):
    """
    This class wrappes the values for the requirements.
    It parses the tags from XML to get those values.
    If no values are found, at least the limits are used as requirements.
    If the user gives a cpu_model in the config, it overrides the previous cpu_model.
    """

    def __init__(self, tags, rlimits, config):
        self.cpu_model = None
        self.memory = None
        self.cpu_cores = None

        for requireTag in tags:
            cpu_model = requireTag.get("cpuModel", None)
            if cpu_model:
                if self.cpu_model is None:
                    self.cpu_model = cpu_model
                else:
                    raise Exception("Double specification of required CPU model.")

            cpu_cores = requireTag.get("cpuCores", None)
            if cpu_cores:
                if self.cpu_cores is None:
                    if cpu_cores is not None:
                        self.cpu_cores = int(cpu_cores)
                else:
                    raise Exception("Double specification of required CPU cores.")

            memory = requireTag.get("memory", None)
            if memory:
                if self.memory is None:
                    if memory is not None:
                        try:
                            self.memory = int(memory) * _BYTE_FACTOR * _BYTE_FACTOR
                            logging.warning(
                                'Value "%s" for memory requirement interpreted as MB for backwards compatibility, '
                                "specify a unit to make this unambiguous.",
                                memory,
                            )
                        except ValueError:
                            self.memory = util.parse_memory_value(memory)
                else:
                    raise Exception("Double specification of required memory.")

        # TODO check, if we have enough requirements to reach the limits
        # TODO is this really enough? we need some overhead!
        if self.cpu_cores is None:
            self.cpu_cores = rlimits.cpu_cores

        if self.memory is None:
            self.memory = rlimits.memory

        if hasattr(config, "cpu_model") and config.cpu_model is not None:
            # user-given model -> override value
            self.cpu_model = config.cpu_model

        if self.cpu_cores is not None and self.cpu_cores <= 0:
            raise Exception(f"Invalid value {self.cpu_cores} for required CPU cores.")

        if self.memory is not None and self.memory <= 0:
            raise Exception(f"Invalid value {self.memory} for required memory.")

    def __str__(self):
        s = ""
        if self.cpu_model:
            s += f" CPU='{self.cpu_model}'"
        if self.cpu_cores:
            s += f" Cores={self.cpu_cores}"
        if self.memory:
            s += f" Memory={self.memory / _BYTE_FACTOR / _BYTE_FACTOR} MB"

        return f"Requirements: {s or ' None'}"
