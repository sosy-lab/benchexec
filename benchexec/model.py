# BenchExec is a framework for reliable benchmarking.
# This file is part of BenchExec.
#
# Copyright (C) 2007-2015  Dirk Beyer
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# prepare for Python 3
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import os
import time
import sys
from xml.etree import ElementTree

from benchexec import result
from benchexec import util

MEMLIMIT = "memlimit"
TIMELIMIT = "timelimit"
CORELIMIT = "cpuCores"

SOFTTIMELIMIT = 'softtimelimit'
HARDTIMELIMIT = 'hardtimelimit'

PROPERTY_TAG = "propertyfile"

_BYTE_FACTOR = 1000 # byte in kilobyte

def substitute_vars(oldList, runSet=None, sourcefile=None):
    """
    This method replaces special substrings from a list of string
    and return a new list.
    """
    keyValueList = []
    if runSet:
        benchmark = runSet.benchmark

        # list with tuples (key, value): 'key' is replaced by 'value'
        keyValueList = [('${benchmark_name}',     benchmark.name),
                        ('${benchmark_date}',     benchmark.instance),
                        ('${benchmark_path}',     benchmark.base_dir or '.'),
                        ('${benchmark_path_abs}', os.path.abspath(benchmark.base_dir)),
                        ('${benchmark_file}',     os.path.basename(benchmark.benchmark_file)),
                        ('${benchmark_file_abs}', os.path.abspath(os.path.basename(benchmark.benchmark_file))),
                        ('${logfile_path}',       os.path.dirname(runSet.log_folder) or '.'),
                        ('${logfile_path_abs}',   os.path.abspath(runSet.log_folder)),
                        ('${rundefinition_name}', runSet.real_name if runSet.real_name else ''),
                        ('${test_name}',          runSet.real_name if runSet.real_name else '')]

    if sourcefile:
        keyValueList.append(('${inputfile_name}', os.path.basename(sourcefile)))
        keyValueList.append(('${inputfile_path}', os.path.dirname(sourcefile) or '.'))
        keyValueList.append(('${inputfile_path_abs}', os.path.dirname(os.path.abspath(sourcefile))))
        # The following are deprecated: do not use anymore.
        keyValueList.append(('${sourcefile_name}', os.path.basename(sourcefile)))
        keyValueList.append(('${sourcefile_path}', os.path.dirname(sourcefile) or '.'))
        keyValueList.append(('${sourcefile_path_abs}', os.path.dirname(os.path.abspath(sourcefile))))

    # do not use keys twice
    assert len(set((key for (key, value) in keyValueList))) == len(keyValueList)

    newList = []

    for oldStr in oldList:
        newStr = oldStr
        for (key, value) in keyValueList:
            newStr = newStr.replace(key, value)
        if '${' in newStr:
            logging.warning("A variable was not replaced in '%s'.", newStr)
        newList.append(newStr)

    return newList


def load_tool_info(tool_name):
    """
    Load the tool-info class.
    @param tool_name: The name of the tool-info module.
    Either a full Python package name or a name within the benchexec.tools package.
    @return: A tuple of the full name of the used tool-info module and an instance of the tool-info class.
    """
    tool_module = tool_name if '.' in tool_name else ("benchexec.tools." + tool_name)
    try:
        tool = __import__(tool_module, fromlist=['Tool']).Tool()
    except ImportError as ie:
        sys.exit('Unsupported tool "{0}" specified. ImportError: {1}'.format(tool_name, ie))
    except AttributeError:
        sys.exit('The module "{0}" does not define the necessary class "Tool", '
                 'it cannot be used as tool info for BenchExec.'.format(tool_module))
    return (tool_module, tool)


def cmdline_for_run(tool, executable, options, sourcefiles, propertyfile, rlimits):
    working_directory = tool.working_directory(executable)
    def relpath(path):
        return path if os.path.isabs(path) \
            else os.path.relpath(path, working_directory)

    rel_executable = relpath(executable)
    if os.path.sep not in rel_executable:
        rel_executable = os.path.join(os.curdir, rel_executable)
    args = tool.cmdline(
        rel_executable, options,
        list(map(relpath, sourcefiles)),
        relpath(propertyfile) if propertyfile else None,
        rlimits)
    assert all(args), "Tool cmdline contains empty or None argument: " + str(args)
    args = [os.path.expandvars(arg) for arg in args]
    args = [os.path.expanduser(arg) for arg in args]
    return args;


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
        self.name = os.path.basename(benchmark_file)[:-4] # remove ending ".xml"
        if config.name:
            self.name += "."+config.name

        self.start_time = start_time
        self.instance = time.strftime("%Y-%m-%d_%H%M", self.start_time)

        self.output_base_name = config.output_path + self.name + "." + self.instance
        self.log_folder = self.output_base_name + ".logfiles" + os.path.sep
        self.log_zip = self.output_base_name + ".logfiles.zip"
        self.result_files_folder = self.output_base_name + ".files"

        # parse XML
        try:
            rootTag = ElementTree.ElementTree().parse(benchmark_file)
        except ElementTree.ParseError as e:
            sys.exit('Benchmark file {} is invalid: {}'.format(benchmark_file, e))
        if 'benchmark' != rootTag.tag:
            sys.exit("Benchmark file {} is invalid: "
                "It's root element is not named 'benchmark'.".format(benchmark_file))

        # get tool
        tool_name = rootTag.get('tool')
        if not tool_name:
            sys.exit('A tool needs to be specified in the benchmark definition file.')
        (self.tool_module, self.tool) = load_tool_info(tool_name)
        self.tool_name = self.tool.name()
        # will be set from the outside if necessary (may not be the case in SaaS environments)
        self.tool_version = None
        self.executable = None

        logging.debug("The tool to be benchmarked is %s.", self.tool_name)

        def parse_memory_limit(value):
            try:
                value = int(value)
                logging.warning(
                    'Value "%s" for memory limit interpreted as MB for backwards compatibility, '
                    'specify a unit to make this unambiguous.',
                    value)
                return value * _BYTE_FACTOR * _BYTE_FACTOR
            except ValueError:
                return util.parse_memory_value(value)

        def handle_limit_value(name, key, cmdline_value, parse_fn):
            value = rootTag.get(key, None)
            # override limit from XML with values from command line
            if cmdline_value is not None:
                if cmdline_value.strip() == "-1": # infinity
                    value = None
                else:
                    value = cmdline_value

            if value is not None:
                try:
                    self.rlimits[key] = parse_fn(value)
                except ValueError as e:
                    sys.exit('Invalid value for {} limit: {}'.format(name.lower(), e))
                if self.rlimits[key] <= 0:
                    sys.exit('{} limit "{}" is invalid, it needs to be a positive number '
                         '(or -1 on the command line for disabling it).'.format(name, value))

        self.rlimits = {}
        keys = list(rootTag.keys())
        handle_limit_value("Time", TIMELIMIT, config.timelimit, util.parse_timespan_value)
        handle_limit_value("Hard time", HARDTIMELIMIT, config.timelimit, util.parse_timespan_value)
        handle_limit_value("Memory", MEMLIMIT, config.memorylimit, parse_memory_limit)
        handle_limit_value("Core", CORELIMIT, config.corelimit, int)

        if HARDTIMELIMIT in self.rlimits:
            hardtimelimit = self.rlimits.pop(HARDTIMELIMIT)
            if TIMELIMIT in self.rlimits:
                if hardtimelimit < self.rlimits[TIMELIMIT]:
                    logging.warning(
                        'Hard timelimit %d is smaller than timelimit %d, ignoring the former.',
                        hardtimelimit, self.rlimits[TIMELIMIT])
                elif hardtimelimit > self.rlimits[TIMELIMIT]:
                    self.rlimits[SOFTTIMELIMIT] = self.rlimits[TIMELIMIT]
                    self.rlimits[TIMELIMIT] = hardtimelimit
            else:
                self.rlimits[TIMELIMIT] = hardtimelimit

        # get number of threads, default value is 1
        self.num_of_threads = int(rootTag.get("threads")) if ("threads" in keys) else 1
        if config.num_of_threads != None:
            self.num_of_threads = config.num_of_threads
        if self.num_of_threads < 1:
            logging.error("At least ONE thread must be given!")
            sys.exit()

        # get global options and property file
        self.options = util.get_list_from_xml(rootTag)
        self.propertyfile = util.text_or_none(util.get_single_child_from_xml(rootTag, PROPERTY_TAG))

        # get columns
        self.columns = Benchmark.load_columns(rootTag.find("columns"))

        # get global source files, they are used in all run sets
        globalSourcefilesTags = rootTag.findall("tasks") + rootTag.findall("sourcefiles")

        # get required files
        self._required_files = set()
        for required_files_tag in rootTag.findall('requiredfiles'):
            required_files = util.expand_filename_pattern(required_files_tag.text, self.base_dir)
            if not required_files:
                logging.warning('Pattern %s in requiredfiles tag did not match any file.',
                                required_files_tag.text)
            self._required_files = self._required_files.union(required_files)

        # get requirements
        self.requirements = Requirements(rootTag.findall("require"), self.rlimits, config)

        result_files_tags = rootTag.findall("resultfiles")
        if result_files_tags:
            self.result_files_patterns = [
                os.path.normpath(p.text) for p in result_files_tags if p.text]
            for pattern in self.result_files_patterns:
                if pattern.startswith(".."):
                    sys.exit("Invalid relative result-files pattern '{}'.".format(pattern))
        else:
            # default is "everything below current directory"
            self.result_files_patterns = ["."]

        # get benchmarks
        self.run_sets = []
        for (i, rundefinitionTag) in enumerate(rootTag.findall("rundefinition")):
            self.run_sets.append(RunSet(rundefinitionTag, self, i+1, globalSourcefilesTags))

        if not self.run_sets:
            for (i, rundefinitionTag) in enumerate(rootTag.findall("test")):
                self.run_sets.append(RunSet(rundefinitionTag, self, i+1, globalSourcefilesTags))
            if self.run_sets:
                logging.warning("Benchmark file %s uses deprecated <test> tags. "
                                "Please rename them to <rundefinition>.",
                                benchmark_file)
            else:
                logging.warning("Benchmark file %s specifies no runs to execute "
                                "(no <rundefinition> tags found).",
                                benchmark_file)

        if not any(runSet.should_be_executed() for runSet in self.run_sets):
            logging.warning("No <rundefinition> tag selected, nothing will be executed.")
            if config.selected_run_definitions:
                logging.warning("The selection %s does not match any run definitions of %s.",
                                config.selected_run_definitions,
                                [runSet.real_name for runSet in self.run_sets])
        elif config.selected_run_definitions:
            for selected in config.selected_run_definitions:
                if not any(util.wildcard_match(run_set.real_name, selected) for run_set in self.run_sets):
                    logging.warning(
                        'The selected run definition "%s" is not present in the input file, '
                        'skipping it.',
                        selected)


    def required_files(self):
        assert self.executable is not None, "executor needs to set tool executable"
        return self._required_files.union(self.tool.program_files(self.executable))


    def add_required_file(self, filename=None):
        if filename is not None:
            self._required_files.add(filename)


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
        if columnsTag != None: # columnsTag is optional in XML file
            for columnTag in columnsTag.findall("column"):
                pattern = columnTag.text
                title = columnTag.get("title", pattern)
                number_of_digits = columnTag.get("numberOfDigits") # digits behind comma
                column = Column(pattern, title, number_of_digits)
                columns.append(column)
                logging.debug('Column "%s" with title "%s" loaded from XML file.',
                              column.text, column.title)
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
            self.result_files_folder = os.path.join(self.result_files_folder, self.real_name)

        # get all run-set-specific options from rundefinitionTag
        self.options = benchmark.options + util.get_list_from_xml(rundefinitionTag)
        self.propertyfile = util.text_or_none(util.get_single_child_from_xml(rundefinitionTag, PROPERTY_TAG)) or benchmark.propertyfile

        # get run-set specific required files
        required_files_pattern = set(tag.text for tag in rundefinitionTag.findall('requiredfiles'))

        # get all runs, a run contains one sourcefile with options
        self.blocks = self.extract_runs_from_xml(
            globalSourcefilesTags + rundefinitionTag.findall("tasks") + rundefinitionTag.findall("sourcefiles"),
            required_files_pattern)
        self.runs = [run for block in self.blocks for run in block.runs]

        names = [self.real_name]
        if len(self.blocks) == 1:
            # there is exactly one source-file set to run, append its name to run-set name
            names.append(self.blocks[0].real_name)
        self.name = '.'.join(filter(None, names))
        self.full_name = self.benchmark.name + (("." + self.name) if self.name else "")

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
                    logging.warning("Input file with name '%s' appears twice in runset. "
                                    "This could cause problems with equal logfile-names.",
                                    base)
                else:
                    sourcefilesSet.add(base)
            del sourcefilesSet


    def should_be_executed(self):
        return not self.benchmark.config.selected_run_definitions \
            or any(util.wildcard_match(self.real_name, run_definition) for run_definition in self.benchmark.config.selected_run_definitions)


    def extract_runs_from_xml(self, sourcefilesTagList, global_required_files_pattern):
        '''
        This function builds a list of SourcefileSets (containing filename with options).
        The files and their options are taken from the list of sourcefilesTags.
        '''
        # runs are structured as sourcefile sets, one set represents one sourcefiles tag
        blocks = []

        for index, sourcefilesTag in enumerate(sourcefilesTagList):
            sourcefileSetName = sourcefilesTag.get("name")
            matchName = sourcefileSetName or str(index)
            if self.benchmark.config.selected_sourcefile_sets \
                and not any(util.wildcard_match(matchName, sourcefile_set) for sourcefile_set in self.benchmark.config.selected_sourcefile_sets):
                    continue

            required_files_pattern = set(tag.text for tag in sourcefilesTag.findall('requiredfiles'))

            # get lists of filenames
            sourcefiles = self.get_sourcefiles_from_xml(sourcefilesTag, self.benchmark.base_dir)

            # get file-specific options for filenames
            fileOptions = util.get_list_from_xml(sourcefilesTag)
            propertyfile = util.text_or_none(util.get_single_child_from_xml(sourcefilesTag, PROPERTY_TAG))

            currentRuns = []
            for sourcefile in sourcefiles:
                currentRuns.append(Run(sourcefile, fileOptions, self, propertyfile,
                                       global_required_files_pattern.union(required_files_pattern)))

            blocks.append(SourcefileSet(sourcefileSetName, index, currentRuns))

        if self.benchmark.config.selected_sourcefile_sets:
            for selected in self.benchmark.config.selected_sourcefile_sets:
                if not any(util.wildcard_match(sourcefile_set.real_name, selected) for sourcefile_set in blocks):
                    logging.warning(
                        'The selected tasks "%s" are not present in the input file, '
                        'skipping them.',
                        selected)
        return blocks


    def get_sourcefiles_from_xml(self, sourcefilesTag, base_dir):
        sourcefiles = []

        # get included sourcefiles
        for includedFiles in sourcefilesTag.findall("include"):
            sourcefiles += self.expand_filename_pattern(includedFiles.text, base_dir)

        # get sourcefiles from list in file
        for includesFilesFile in sourcefilesTag.findall("includesfile"):

            for file in self.expand_filename_pattern(includesFilesFile.text, base_dir):

                # check for code (if somebody confuses 'include' and 'includesfile')
                if util.is_code(file):
                    logging.error(
                        "'%s' seems to contain code instead of a set of source file names.\n"
                        "Please check your benchmark definition file "
                        "or remove bracket '{' from this file.",
                        file)
                    sys.exit()

                # read files from list
                fileWithList = open(file, 'rt')
                for line in fileWithList:

                    # strip() removes 'newline' behind the line
                    line = line.strip()

                    # ignore comments and empty lines
                    if not util.is_comment(line):
                        sourcefiles += self.expand_filename_pattern(line, os.path.dirname(file))

                fileWithList.close()

        # remove excluded sourcefiles
        for excludedFiles in sourcefilesTag.findall("exclude"):
            excludedFilesList = self.expand_filename_pattern(excludedFiles.text, base_dir)
            for excludedFile in excludedFilesList:
                sourcefiles = util.remove_all(sourcefiles, excludedFile)

        for excludesFilesFile in sourcefilesTag.findall("excludesfile"):
            for file in self.expand_filename_pattern(excludesFilesFile.text, base_dir):
                # read files from list
                fileWithList = open(file, 'rt')
                for line in fileWithList:

                    # strip() removes 'newline' behind the line
                    line = line.strip()

                    # ignore comments and empty lines
                    if not util.is_comment(line):
                        excludedFilesList = self.expand_filename_pattern(line, os.path.dirname(file))
                        for excludedFile in excludedFilesList:
                            sourcefiles = util.remove_all(sourcefiles, excludedFile)

                fileWithList.close()

        # add runs for cases without source files
        for run in sourcefilesTag.findall("withoutfile"):
            sourcefiles.append(run.text)

        # some runs need more than one sourcefile,
        # the first sourcefile is a normal 'include'-file, we use its name as identifier for logfile and result-category
        # all other files are 'append'ed.
        sourcefilesLists = []
        appendFileTags = sourcefilesTag.findall("append")
        for sourcefile in sourcefiles:
            files = [sourcefile]
            for appendFile in appendFileTags:
                files.extend(self.expand_filename_pattern(appendFile.text, base_dir, sourcefile=sourcefile))
            sourcefilesLists.append(files)

        return sourcefilesLists


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
            logging.debug("Expanded variables in expression %r to %r.",
                          pattern, expandedPattern)

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
        self.real_name = name # this name is optional
        self.name = name or str(index) # this name is always non-empty
        self.runs = runs


_logged_missing_property_files = set()


class Run(object):
    """
    A Run contains some sourcefile, some options, propertyfiles and some other stuff, that is needed for the Run.
    """

    def __init__(self, sourcefiles, fileOptions, runSet, propertyfile=None, required_files_patterns=[]):
        assert sourcefiles
        self.identifier = sourcefiles[0] # used for name of logfile, substitution, result-category
        self.sourcefiles = util.get_files(sourcefiles) # expand directories to get their sub-files
        self.runSet = runSet
        self.specific_options = fileOptions # options that are specific for this run
        self.log_file = runSet.log_folder + os.path.basename(self.identifier) + ".log"
        self.result_files_folder = os.path.join(runSet.result_files_folder, os.path.basename(self.identifier))

        self.required_files = set()
        rel_sourcefile = os.path.relpath(self.identifier, runSet.benchmark.base_dir)
        for pattern in required_files_patterns:
            this_required_files = runSet.expand_filename_pattern(pattern, runSet.benchmark.base_dir, rel_sourcefile)
            if not this_required_files:
                logging.warning(
                    'Pattern %s in requiredfiles tag did not match any file for task %s.',
                    pattern, self.identifier)
            self.required_files.update(this_required_files)
        self.required_files = list(self.required_files)

        # lets reduce memory-consumption: if 2 lists are equal, do not use the second one
        self.options = runSet.options + fileOptions if fileOptions else runSet.options # all options to be used when executing this run
        substitutedOptions = substitute_vars(self.options, runSet, self.identifier)
        if substitutedOptions != self.options:
            self.options = substitutedOptions # for less memory again

        self.propertyfile = propertyfile or runSet.propertyfile

        def log_property_file_once(msg):
            if not self.propertyfile in _logged_missing_property_files:
                _logged_missing_property_files.add(self.propertyfile)
                logging.warning(msg)

        # replace run-specific stuff in the propertyfile and add it to the set of required files
        if self.propertyfile is None:
            log_property_file_once('No propertyfile specified. Results for C programs will be handled as UNKNOWN.')
        else:
            # we check two cases: direct filename or user-defined substitution, one of them must be a 'file'
            # TODO: do we need the second case? it is equal to previous used option "-spec ${sourcefile_path}/ALL.prp"
            expandedPropertyFiles = util.expand_filename_pattern(self.propertyfile, self.runSet.benchmark.base_dir)
            substitutedPropertyfiles = substitute_vars([self.propertyfile], runSet, self.identifier)
            assert len(substitutedPropertyfiles) == 1

            if expandedPropertyFiles:
                if len(expandedPropertyFiles) > 1:
                    log_property_file_once('Pattern {0} for sourcefile {1} in propertyfile tag matches more than one file. Only {2} will be used.'
                                           .format(self.propertyfile, self.identifier, expandedPropertyFiles[0]))
                self.propertyfile = expandedPropertyFiles[0]
            elif substitutedPropertyfiles and os.path.isfile(substitutedPropertyfiles[0]):
                self.propertyfile = substitutedPropertyfiles[0]
            else:
                log_property_file_once('Pattern {0} for sourcefile {1} in propertyfile tag did not match any file. It will be ignored.'
                                       .format(self.propertyfile, self.identifier))
                self.propertyfile = None

        if self.propertyfile:
            self.runSet.benchmark.add_required_file(self.propertyfile)
            self.properties = result.properties_of_file(self.propertyfile)
        else:
            self.properties = []

        # Copy columns for having own objects in run
        # (we need this for storing the results in them).
        self.columns = [Column(c.text, c.title, c.number_of_digits) for c in self.runSet.benchmark.columns]

        # here we store the optional result values, e.g. memory usage, energy, host name
        # keys need to be strings, if first character is "@" the value is marked as hidden (e.g., debug info)
        self.values = {}

        # dummy values, for output in case of interrupt
        self.status = ""
        self.cputime = None
        self.walltime = None
        self.category = result.CATEGORY_UNKNOWN


    def cmdline(self):
        assert self.runSet.benchmark.executable is not None, "executor needs to set tool executable"
        return cmdline_for_run(self.runSet.benchmark.tool,
                               self.runSet.benchmark.executable,
                               self.options,
                               self.sourcefiles,
                               self.propertyfile,
                               self.runSet.benchmark.rlimits)


    def set_result(self, values, visible_columns={}):
        """Set the result of this run.
        Use this method instead of manually setting the run attributes and calling after_execution(),
        this method handles all this by itself.
        @param values: a dictionary with result values as returned by RunExecutor.execute_run(),
            may also contain arbitrary additional values
        @param visible_columns: a set of keys of values that should be visible by default
            (i.e., not marked as hidden), apart from those that BenchExec shows by default anyway
        """
        exitcode = values.pop('exitcode', None)
        if exitcode is not None:
            self.values['@exitcode'] = exitcode
            exitcode = util.ProcessExitCode.from_raw(exitcode)
            if exitcode.signal:
                self.values['@exitsignal'] = exitcode.signal
            else:
                self.values['@returnvalue'] = exitcode.value

        for key, value in values.items():
            if key == 'walltime':
                self.walltime = value
            elif key == 'cputime':
                self.cputime = value
            elif key == 'memory':
                self.values['memUsage'] = value
            elif key == 'energy':
                for ekey, evalue in value.items():
                    self.values['energy-'+ekey] = evalue
            elif key in visible_columns:
                self.values[key] = value
            else:
                self.values['@' + key] = value

        self.after_execution(exitcode, termination_reason=values.get('terminationreason'))

    def after_execution(self, exitcode, forceTimeout=False, termination_reason=None):
        """
        @deprecated: use set_result() instead
        """
        # termination reason is not fully precise for timeouts, so we guess "timeouts"
        # if time is too high
        isTimeout = forceTimeout \
                or termination_reason in ['cputime', 'cputime-soft', 'walltime'] \
                or self._is_timeout()

        if isinstance(exitcode, int):
            exitcode = util.ProcessExitCode.from_raw(exitcode)

        # read output
        try:
            with open(self.log_file, 'rt', errors='ignore') as outputFile:
                output = outputFile.readlines()
                # first 6 lines are for logging, rest is output of subprocess, see runexecutor.py for details
                output = output[6:]
        except IOError as e:
            logging.warning("Cannot read log file: %s", e.strerror)
            output = []

        self.status = self._analyse_result(exitcode, output, isTimeout, termination_reason)
        self.category = result.get_result_category(self.identifier, self.status, self.properties)

        for column in self.columns:
            substitutedColumnText = substitute_vars([column.text], self.runSet, self.sourcefiles[0])[0]
            column.value = self.runSet.benchmark.tool.get_value_from_output(output, substitutedColumnText)

    def _analyse_result(self, exitcode, output, isTimeout, termination_reason):
        """Return status according to result and output of tool."""
        status = ""

        # Ask tool info.
        if exitcode is not None:
            logging.debug("My subprocess returned %s.", exitcode)
            status = self.runSet.benchmark.tool.determine_result(
                exitcode.value or 0, exitcode.signal or 0, output, isTimeout)

        # Tools sometimes produce a result even after violating a resource limit.
        # This should not be counted, so we overwrite the result with TIMEOUT/OOM
        # here, if this is the case.
        # However, we don't want to forget more specific results like SEGFAULT,
        # so we do this only if the result is a "normal" one like TRUE/FALSE
        # or an unspecific one like UNKNOWN/ERROR.
        if status in result.RESULT_LIST or status in [result.RESULT_ERROR, result.RESULT_UNKNOWN]:
            tool_status = status
            if isTimeout:
                status = "TIMEOUT"
            elif termination_reason == 'memory':
                status = 'OUT OF MEMORY'
            else:
                # TODO probably this is not necessary anymore
                rlimits = self.runSet.benchmark.rlimits
                guessed_OOM = exitcode is not None \
                        and exitcode.signal == 9 \
                        and MEMLIMIT in rlimits \
                        and 'memUsage' in self.values \
                        and not self.values['memUsage'] is None \
                        and int(self.values['memUsage']) >= (rlimits[MEMLIMIT] * 0.99)
                if guessed_OOM:
                    # Set status to a special marker.
                    # If we see this in the results, we know that we need to do more work to set
                    # termination_reason properly.
                    status = 'PROBABLY OUT OF MEMORY'
            if tool_status not in [status, result.RESULT_ERROR, result.RESULT_UNKNOWN]:
                status = '{} ({})'.format(status, tool_status)

        if status in [result.RESULT_ERROR, result.RESULT_UNKNOWN] and exitcode is not None:
            # provide some more information if possible
            if exitcode.signal == 6:
                status = 'ABORTED'
            elif exitcode.signal == 11:
                status = 'SEGMENTATION FAULT'
            elif exitcode.signal == 15:
                status = 'KILLED'
            elif exitcode.signal:
                status = 'KILLED BY SIGNAL '+str(exitcode.signal)

            elif exitcode.value:
                status = '{} ({})'.format(result.RESULT_ERROR, exitcode.value)

        return status

    def _is_timeout(self):
        ''' try to find out whether the tool terminated because of a timeout '''
        if self.cputime is None:
            return False
        rlimits = self.runSet.benchmark.rlimits
        if SOFTTIMELIMIT in rlimits:
            limit = rlimits[SOFTTIMELIMIT]
        elif TIMELIMIT in rlimits:
            limit = rlimits[TIMELIMIT]
        else:
            limit = float('inf')

        return self.cputime > limit


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
    '''
    This class wrappes the values for the requirements.
    It parses the tags from XML to get those values.
    If no values are found, at least the limits are used as requirements.
    If the user gives a cpu_model in the config, it overrides the previous cpu_model.
    '''
    def __init__(self, tags, rlimits, config):

        self.cpu_model = None
        self.memory   = None
        self.cpu_cores = None

        for requireTag in tags:

            cpu_model = requireTag.get('cpuModel', None)
            if cpu_model:
                if self.cpu_model is None:
                    self.cpu_model = cpu_model
                else:
                    raise Exception('Double specification of required CPU model.')

            cpu_cores = requireTag.get('cpuCores', None)
            if cpu_cores:
                if self.cpu_cores is None:
                    if cpu_cores is not None:
                        self.cpu_cores = int(cpu_cores)
                else:
                    raise Exception('Double specification of required CPU cores.')

            memory = requireTag.get('memory',   None)
            if memory:
                if self.memory is None:
                    if memory is not None:
                        try:
                            self.memory = int(memory) * _BYTE_FACTOR * _BYTE_FACTOR
                            logging.warning(
                                'Value "%s" for memory requirement interpreted as MB for backwards compatibility, '
                                'specify a unit to make this unambiguous.',
                                memory)
                        except ValueError:
                            self.memory = util.parse_memory_value(memory)
                else:
                    raise Exception('Double specification of required memory.')

        # TODO check, if we have enough requirements to reach the limits
        # TODO is this really enough? we need some overhead!
        if self.cpu_cores is None:
            self.cpu_cores = rlimits.get(CORELIMIT, None)

        if self.memory is None:
            self.memory = rlimits.get(MEMLIMIT, None)

        if hasattr(config, 'cpu_model') and config.cpu_model is not None:
            # user-given model -> override value
            self.cpu_model = config.cpu_model

        if self.cpu_cores is not None and self.cpu_cores <= 0:
            raise Exception('Invalid value {} for required CPU cores.'.format(self.cpu_cores))

        if self.memory is not None and self.memory <= 0:
            raise Exception('Invalid value {} for required memory.'.format(self.memory))


    def __str__(self):
        s = ""
        if self.cpu_model:
            s += " CPU='" + self.cpu_model + "'"
        if self.cpu_cores:
            s += " Cores=" + str(self.cpu_cores)
        if self.memory:
            s += " Memory=" + str(self.memory/_BYTE_FACTOR/_BYTE_FACTOR) + " MB"

        return "Requirements:" + (s if s else " None")


