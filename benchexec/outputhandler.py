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

import bz2
import collections
import io
import os
import threading
import time
import sys
from xml.dom import minidom
from xml.etree import ElementTree as ET
import zipfile

import benchexec
from benchexec.model import MEMLIMIT, TIMELIMIT, SOFTTIMELIMIT, CORELIMIT
from benchexec import filewriter
from benchexec import result
from benchexec import util

RESULT_XML_PUBLIC_ID = '+//IDN sosy-lab.org//DTD BenchExec result 1.9//EN'
RESULT_XML_SYSTEM_ID = 'http://www.sosy-lab.org/benchexec/result-1.9.dtd'

# colors for column status in terminal
USE_COLORS = True
COLOR_GREEN   = "\033[32;1m{0}\033[m"
COLOR_RED     = "\033[31;1m{0}\033[m"
COLOR_ORANGE  = "\033[33;1m{0}\033[m"
COLOR_MAGENTA = "\033[35;1m{0}\033[m"
COLOR_DEFAULT = "{0}"
UNDERLINE     = "\033[4m{0}\033[0m"

COLOR_DIC = {result.CATEGORY_CORRECT: COLOR_GREEN,
             result.CATEGORY_WRONG:   COLOR_RED,
             result.CATEGORY_UNKNOWN: COLOR_ORANGE,
             result.CATEGORY_ERROR:   COLOR_MAGENTA,
             result.CATEGORY_MISSING: COLOR_DEFAULT,
             None: COLOR_DEFAULT}

LEN_OF_STATUS = 22

TERMINAL_TITLE=''
_term = os.environ.get('TERM', '')
if _term.startswith(('xterm', 'rxvt')):
    TERMINAL_TITLE = "\033]0;Task {0}\007"
elif _term.startswith('screen'):
    TERMINAL_TITLE = "\033kTask {0}\033\\"

# the number of digits after the decimal separator for text output of time columns with times
TIME_PRECISION = 2
_BYTE_FACTOR = 1000 # byte in kilobyte


class OutputHandler(object):
    """
    The class OutputHandler manages all outputs to the terminal and to files.
    """

    print_lock = threading.Lock()

    def __init__(self, benchmark, sysinfo, compress_results):
        """
        The constructor of OutputHandler collects information about the benchmark and the computer.
        """

        self.compress_results = compress_results
        self.all_created_files = set()
        self.benchmark = benchmark
        self.statistics = Statistics()

        version = self.benchmark.tool_version

        memlimit = None
        timelimit = None
        corelimit = None
        if MEMLIMIT in self.benchmark.rlimits:
            memlimit = self.benchmark.rlimits[MEMLIMIT]
        if SOFTTIMELIMIT in self.benchmark.rlimits:
            timelimit = str(self.benchmark.rlimits[SOFTTIMELIMIT]) + "s"
        elif TIMELIMIT in self.benchmark.rlimits:
            timelimit = str(self.benchmark.rlimits[TIMELIMIT]) + "s"
        if CORELIMIT in self.benchmark.rlimits:
            corelimit = str(self.benchmark.rlimits[CORELIMIT])

        # create folder for file-specific log-files.
        os.makedirs(benchmark.log_folder, exist_ok=True)

        self.store_header_in_xml(version, memlimit, timelimit, corelimit)
        self.write_header_to_log(version, memlimit, timelimit, corelimit, sysinfo)

        if sysinfo:
            # store systemInfo in XML
            self.store_system_info(sysinfo.os, sysinfo.cpu_model,
                                 sysinfo.cpu_number_of_cores, sysinfo.cpu_max_frequency,
                                 sysinfo.memory, sysinfo.hostname,
                                 environment=sysinfo.environment,
                                 cpu_turboboost=sysinfo.cpu_turboboost)
        self.xml_file_names = []

        if compress_results:
            self.log_zip = zipfile.ZipFile(benchmark.log_zip, mode="w",
                                           compression=zipfile.ZIP_DEFLATED)
            self.all_created_files.add(benchmark.log_zip)


    def store_system_info(self, opSystem, cpu_model, cpu_number_of_cores, cpu_max_frequency, memory, hostname,
                          runSet=None, environment={},
                          cpu_turboboost=None):
        for systemInfo in self.xml_header.findall("systeminfo"):
                    if systemInfo.attrib["hostname"] == hostname:
                        return

        osElem = ET.Element("os", {"name":opSystem})
        cpuElem = ET.Element("cpu", {"model":cpu_model, "cores":cpu_number_of_cores, "frequency":str(cpu_max_frequency)})
        if cpu_turboboost is not None:
            cpuElem.set("turboboostActive", str(cpu_turboboost).lower())
        ramElem = ET.Element("ram", {"size":str(memory)})
        systemInfo = ET.Element("systeminfo", {"hostname":hostname})
        systemInfo.append(osElem)
        systemInfo.append(cpuElem)
        systemInfo.append(ramElem)
        env = ET.SubElement(systemInfo, "environment")
        for var, value in sorted(environment.items()):
            ET.SubElement(env, "var", name=var).text = value

        self.xml_header.append(systemInfo)
        if runSet:
            # insert before <run> tags to conform with DTD
            i = None
            for i, elem in enumerate(runSet.xml):
                if elem.tag == "run":
                    break
            if i is None:
                runSet.xml.append(systemInfo)
            else:
                runSet.xml.insert(i, systemInfo)

    def set_error(self, msg, runSet=None):
        """
        Mark the benchmark as erroneous, e.g., because the benchmarking tool crashed.
        The message is intended as explanation for the user.
        """
        self.xml_header.set('error', msg if msg else 'unknown error')
        if runSet:
            runSet.xml.set('error', msg if msg else 'unknown error')


    def store_header_in_xml(self, version, memlimit, timelimit, corelimit):

        # store benchmarkInfo in XML
        self.xml_header = ET.Element("result",
                    {"benchmarkname": self.benchmark.name,
                     "date":  time.strftime("%Y-%m-%d %H:%M:%S %Z", self.benchmark.start_time),
                     "tool": self.benchmark.tool_name, "version": version,
                     "toolmodule": self.benchmark.tool_module,
                     "generator": "BenchExec " + benchexec.__version__
                     })

        if memlimit is not None:
            self.xml_header.set(MEMLIMIT, str(memlimit))
        if timelimit is not None:
            self.xml_header.set(TIMELIMIT, timelimit)
        if corelimit is not None:
            self.xml_header.set(CORELIMIT, corelimit)

        # store columnTitles in XML, this are the default columns, that are shown in a default html-table from table-generator
        columntitlesElem = ET.Element("columns")
        columntitlesElem.append(ET.Element("column", {"title": "status"}))
        columntitlesElem.append(ET.Element("column", {"title": "cputime"}))
        columntitlesElem.append(ET.Element("column", {"title": "walltime"}))
        for column in self.benchmark.columns:
            columnElem = ET.Element("column", {"title": column.title})
            columntitlesElem.append(columnElem)
        self.xml_header.append(columntitlesElem)

        # Build dummy entries for output, later replaced by the results,
        # The dummy XML elements are shared over all runs.
        self.xml_dummy_elements = [ET.Element("column", {"title": "status", "value": ""}),
                      ET.Element("column", {"title": "cputime", "value": ""}),
                      ET.Element("column", {"title": "walltime", "value": ""})]
        for column in self.benchmark.columns:
            self.xml_dummy_elements.append(ET.Element("column",
                        {"title": column.title, "value": ""}))


    def write_header_to_log(self, version, memlimit, timelimit, corelimit, sysinfo):
        """
        This method writes information about benchmark and system into txt_file.
        """

        columnWidth = 20
        simpleLine = "-" * (60) + "\n\n"

        header = "   BENCHMARK INFORMATION\n"\
                + "benchmark:".ljust(columnWidth) + self.benchmark.name + "\n"\
                + "date:".ljust(columnWidth) +  time.strftime("%a, %Y-%m-%d %H:%M:%S %Z", self.benchmark.start_time) + "\n"\
                + "tool:".ljust(columnWidth) + self.benchmark.tool_name\
                + " " + version + "\n"

        if memlimit:
            header += "memlimit:".ljust(columnWidth) + str(memlimit/_BYTE_FACTOR/_BYTE_FACTOR) + " MB\n"
        if timelimit:
            header += "timelimit:".ljust(columnWidth) + timelimit + "\n"
        if corelimit:
            header += "CPU cores used:".ljust(columnWidth) + corelimit + "\n"
        header += simpleLine

        if sysinfo:
            header += "   SYSTEM INFORMATION\n"\
                    + "host:".ljust(columnWidth) + sysinfo.hostname + "\n"\
                    + "os:".ljust(columnWidth) + sysinfo.os + "\n"\
                    + "cpu:".ljust(columnWidth) + sysinfo.cpu_model + "\n"\
                    + "- cores:".ljust(columnWidth) + sysinfo.cpu_number_of_cores + "\n"\
                    + "- max frequency:".ljust(columnWidth) + str(sysinfo.cpu_max_frequency/1000/1000) + " MHz\n"\
                    + "ram:".ljust(columnWidth) + str(sysinfo.memory/_BYTE_FACTOR/_BYTE_FACTOR) + " MB\n"\
                    + simpleLine

        self.description = header

        runSetName = None
        run_sets = [runSet for runSet in self.benchmark.run_sets if runSet.should_be_executed()]
        if len(run_sets) == 1:
            # in case there is only a single run set to to execute, we can use its name
            runSetName = run_sets[0].name

        # write to file
        txt_file_name = self.get_filename(runSetName, "txt")
        self.txt_file = filewriter.FileWriter(txt_file_name, self.description)
        self.all_created_files.add(txt_file_name)


    def output_before_run_set(self, runSet):
        """
        The method output_before_run_set() calculates the length of the
        first column for the output in terminal and stores information
        about the runSet in XML.
        @param runSet: current run set
        """
        sourcefiles = [run.identifier for run in runSet.runs]

        # common prefix of file names
        runSet.common_prefix = util.common_base_dir(sourcefiles) + os.path.sep

        # length of the first column in terminal
        runSet.max_length_of_filename = max(len(file) for file in sourcefiles) if sourcefiles else 20
        runSet.max_length_of_filename = max(20, runSet.max_length_of_filename - len(runSet.common_prefix))

        # write run set name to terminal
        numberOfFiles = len(runSet.runs)
        numberOfFilesStr = ("     (1 file)" if numberOfFiles == 1
                        else "     ({0} files)".format(numberOfFiles))
        util.printOut("\nexecuting run set"
            + (" '" + runSet.name + "'" if runSet.name else "")
            + numberOfFilesStr
            + (TERMINAL_TITLE.format(runSet.full_name) if USE_COLORS and sys.stdout.isatty() else ""))

        # write information about the run set into txt_file
        self.writeRunSetInfoToLog(runSet)

        # prepare information for text output
        for run in runSet.runs:
            run.resultline = self.format_sourcefile_name(run.identifier, runSet)

        # prepare XML structure for each run and runSet
            run.xml = ET.Element("run",
                                 {"name": run.identifier, "files": "[" + ", ".join(run.sourcefiles) + "]"})
            if run.specific_options:
                run.xml.set("options", " ".join(run.specific_options))
            if run.properties:
                run.xml.set("properties", " ".join(sorted(run.properties)))
            run.xml.extend(self.xml_dummy_elements)

        runSet.xml = self.runs_to_xml(runSet, runSet.runs)

        # write (empty) results to txt_file and XML
        self.txt_file.append(self.run_set_to_text(runSet), False)
        runSet.xml_file_name = self.get_filename(runSet.name, "xml")
        self._write_rough_result_xml_to_file(runSet.xml, runSet.xml_file_name)
        runSet.xml_file_last_modified_time = util.read_monotonic_time()
        self.all_created_files.add(runSet.xml_file_name)
        self.xml_file_names.append(runSet.xml_file_name)


    def output_for_skipping_run_set(self, runSet, reason=None):
        '''
        This function writes a simple message to terminal and logfile,
        when a run set is skipped.
        There is no message about skipping a run set in the xml-file.
        '''

        # print to terminal
        util.printOut("\nSkipping run set" +
               (" '" + runSet.name + "'" if runSet.name else "") +
               (" " + reason if reason else "")
              )

        # write into txt_file
        runSetInfo = "\n\n"
        if runSet.name:
            runSetInfo += runSet.name + "\n"
        runSetInfo += "Run set {0} of {1}: skipped {2}\n".format(
                runSet.index, len(self.benchmark.run_sets), reason or "")
        self.txt_file.append(runSetInfo)


    def writeRunSetInfoToLog(self, runSet):
        """
        This method writes the information about a run set into the txt_file.
        """

        runSetInfo = "\n\n"
        if runSet.name:
            runSetInfo += runSet.name + "\n"
        runSetInfo += "Run set {0} of {1} with options '{2}' and propertyfile '{3}'\n\n".format(
                runSet.index, len(self.benchmark.run_sets),
                " ".join(runSet.options),
                runSet.propertyfile)

        titleLine = self.create_output_line(runSet, "inputfile", "status", "cpu time",
                            "wall time", "host", self.benchmark.columns, True)

        runSet.simpleLine = "-" * (len(titleLine))

        runSetInfo += titleLine + "\n" + runSet.simpleLine + "\n"

        # write into txt_file
        self.txt_file.append(runSetInfo)


    def output_before_run(self, run):
        """
        The method output_before_run() prints the name of a file to terminal.
        It returns the name of the logfile.
        @param run: a Run object
        """
        # output in terminal
        runSet = run.runSet
        try:
            OutputHandler.print_lock.acquire()

            try:
                runSet.started_runs += 1
            except AttributeError:
                runSet.started_runs = 1

            timeStr = time.strftime("%H:%M:%S", time.localtime()) + "   "
            progressIndicator = " ({0}/{1})".format(runSet.started_runs, len(runSet.runs))
            terminalTitle = TERMINAL_TITLE.format(runSet.full_name + progressIndicator) if USE_COLORS and sys.stdout.isatty() else ""
            if self.benchmark.num_of_threads == 1:
                util.printOut(terminalTitle + timeStr + self.format_sourcefile_name(run.identifier, runSet), '')
            else:
                util.printOut(terminalTitle + timeStr + "starting   " + self.format_sourcefile_name(run.identifier, runSet))
        finally:
            OutputHandler.print_lock.release()


    def output_after_run(self, run):
        """
        The method output_after_run() prints filename, result, time and status
        of a run to terminal and stores all data in XML
        """

        # format times, type is changed from float to string!
        cputime_str = util.format_number(run.cputime, TIME_PRECISION)
        walltime_str = util.format_number(run.walltime, TIME_PRECISION)

        # format numbers, number_of_digits is optional, so it can be None
        for column in run.columns:
            if column.number_of_digits is not None:

                # if the number ends with "s" or another letter, remove it
                if (not column.value.isdigit()) and column.value[-2:-1].isdigit():
                    column.value = column.value[:-1]

                try:
                    floatValue = float(column.value)
                    column.value = util.format_number(floatValue, column.number_of_digits)
                except ValueError: # if value is no float, don't format it
                    pass

        # store information in run
        run.resultline = self.create_output_line(run.runSet, run.identifier, run.status,
                cputime_str, walltime_str, run.values.get('host'),
                run.columns)
        self.add_values_to_run_xml(run)

        # output in terminal/console
        if USE_COLORS and sys.stdout.isatty(): # is terminal, not file
            statusStr = COLOR_DIC[run.category].format(run.status.ljust(LEN_OF_STATUS))
        else:
            statusStr = run.status.ljust(LEN_OF_STATUS)

        try:
            OutputHandler.print_lock.acquire()

            valueStr = statusStr + cputime_str.rjust(8) + walltime_str.rjust(8)
            if self.benchmark.num_of_threads == 1:
                util.printOut(valueStr)
            else:
                timeStr = time.strftime("%H:%M:%S", time.localtime()) + " "*14
                util.printOut(timeStr + self.format_sourcefile_name(run.identifier, run.runSet) + valueStr)

            # write result in txt_file and XML
            self.txt_file.append(self.run_set_to_text(run.runSet), False)
            self.statistics.add_result(run)

            # we don't want to write this file to often, it can slow down the whole script,
            # so we wait at least 10 seconds between two write-actions
            currentTime = util.read_monotonic_time()
            if currentTime - run.runSet.xml_file_last_modified_time > 60:
                self._write_rough_result_xml_to_file(run.runSet.xml, run.runSet.xml_file_name)
                run.runSet.xml_file_last_modified_time = util.read_monotonic_time()

        finally:
            OutputHandler.print_lock.release()

        if self.compress_results:
            self.log_zip.write(run.log_file, os.path.relpath(run.log_file, os.path.join(self.benchmark.log_folder, os.pardir)))
            os.remove(run.log_file)
        else:
            self.all_created_files.add(run.log_file)


    def output_after_run_set(self, runSet, cputime=None, walltime=None, energy={}):
        """
        The method output_after_run_set() stores the times of a run set in XML.
        @params cputime, walltime: accumulated times of the run set
        """

        self.add_values_to_run_set_xml(runSet, cputime, walltime, energy)

        # write results to files
        self._write_pretty_result_xml_to_file(runSet.xml, runSet.xml_file_name)

        if len(runSet.blocks) > 1:
            for block in runSet.blocks:
                blockFileName = self.get_filename(runSet.name, block.name + ".xml")
                self._write_pretty_result_xml_to_file(
                    self.runs_to_xml(runSet, block.runs, block.name),
                    blockFileName)

        self.txt_file.append(self.run_set_to_text(runSet, True, cputime, walltime, energy))


    def run_set_to_text(self, runSet, finished=False, cputime=0, walltime=0, energy={}):
        lines = []

        # store values of each run
        for run in runSet.runs:
            lines.append(run.resultline)

        lines.append(runSet.simpleLine)

        # write endline into txt_file
        if finished:
            endline = ("Run set {0}".format(runSet.index))

            # format time, type is changed from float to string!
            cputime_str  = "None" if cputime  is None else util.format_number(cputime, TIME_PRECISION)
            walltime_str = "None" if walltime is None else util.format_number(walltime, TIME_PRECISION)
            lines.append(self.create_output_line(runSet, endline, "done", cputime_str,
                             walltime_str, "-", []))

        return "\n".join(lines) + "\n"

    def runs_to_xml(self, runSet, runs, blockname=None):
        """
        This function creates the XML structure for a list of runs
        """
        # copy benchmarkinfo, limits, columntitles, systeminfo from xml_header
        runsElem = util.copy_of_xml_element(self.xml_header)
        runsElem.set("options", " ".join(runSet.options))
        if blockname is not None:
            runsElem.set("block", blockname)
            runsElem.set("name", ((runSet.real_name + ".") if runSet.real_name else "") + blockname)
        elif runSet.real_name:
            runsElem.set("name", runSet.real_name)

        # collect XMLelements from all runs
        for run in runs:
            runsElem.append(run.xml)

        return runsElem


    def add_values_to_run_xml(self, run):
        """
        This function adds the result values to the XML representation of a run.
        """
        runElem = run.xml
        for elem in list(runElem):
            runElem.remove(elem)
        self.add_column_to_xml(runElem, 'status',    run.status)
        self.add_column_to_xml(runElem, 'cputime', run.cputime)
        self.add_column_to_xml(runElem, 'walltime', run.walltime)
        self.add_column_to_xml(runElem, '@category', run.category) # hidden
        self.add_column_to_xml(runElem, '',          run.values)

        for column in run.columns:
            self.add_column_to_xml(runElem, column.title, column.value)

    def add_values_to_run_set_xml(self, runSet, cputime, walltime, energy):
        """
        This function adds the result values to the XML representation of a runSet.
        """
        self.add_column_to_xml(runSet.xml, 'cputime', cputime)
        self.add_column_to_xml(runSet.xml, 'walltime', walltime)
        self.add_column_to_xml(runSet.xml, 'energy', energy)


    def add_column_to_xml(self, xml, title, value, prefix="", value_suffix=""):
        if value is None:
            return

        if isinstance(value, dict):
            for key, value in value.items():
                if prefix:
                    common_prefix = prefix + '_' + title
                else:
                    common_prefix = title
                self.add_column_to_xml(xml, key, value, prefix=common_prefix)
            return

        if hasattr(value, '__getitem__') and not isinstance(value, (str, bytes)):
            value = ','.join(map(str, value))

        if prefix:
            title = prefix + '_' + title
        if title[0] == '@':
            hidden = True
            title = title[1:]
        else:
            hidden = False

        if title.startswith('cputime') or title.startswith('walltime'):
            if not value_suffix and not isinstance(value, (str, bytes)):
                value_suffix = 's'

        value = "{}{}".format(value, value_suffix)

        if hidden:
            attributes = {"title": title, "value": value, "hidden": "true"}
        else:
            attributes = {"title": title, "value": value}
        xml.append(ET.Element("column", attributes))


    def create_output_line(self, runSet, sourcefile, status, cputime_delta, walltime_delta, host, columns, isFirstLine=False):
        """
        @param sourcefile: title of a sourcefile
        @param status: status of programm
        @param cputime_delta: time from running the programm
        @param walltime_delta: time from running the programm
        @param columns: list of columns with a title or a value
        @param isFirstLine: boolean for different output of headline and other lines
        @return: a line for the outputFile
        """

        lengthOfTime = 12
        minLengthOfColumns = 8

        outputLine = self.format_sourcefile_name(sourcefile, runSet) + \
                     status.ljust(LEN_OF_STATUS) + \
                     cputime_delta.rjust(lengthOfTime) + \
                     walltime_delta.rjust(lengthOfTime) + \
                     str(host).rjust(lengthOfTime)

        for column in columns:
            columnLength = max(minLengthOfColumns, len(column.title)) + 2

            if isFirstLine:
                value = column.title
            else:
                value = column.value

            outputLine = outputLine + str(value).rjust(columnLength)

        return outputLine


    def output_after_benchmark(self, isStoppedByInterrupt):
        self.statistics.print_to_terminal()

        if self.xml_file_names:

            def _find_file_relative(name):
                """
                Find a file with the given name in the same directory as this script.
                Returns a path relative to the current directory, or None.
                """
                path = os.path.join(os.path.dirname(sys.argv[0]), name)
                if not os.path.isfile(path):
                    path = os.path.join(os.path.dirname(__file__), os.path.pardir, name)
                    if not os.path.isfile(path):
                        return None

                if os.path.dirname(path) in os.environ['PATH'].split(os.pathsep):
                    # in PATH, just use command name
                    return os.path.basename(path)

                path = os.path.relpath(path)
                if path == name:
                    path = './' + path # for easier copy and paste into a shell
                return path

            tableGeneratorPath = _find_file_relative('table-generator.py') \
                              or _find_file_relative('table-generator')
            if tableGeneratorPath:
                xml_file_names = [file+".bz2" for file in self.xml_file_names] if self.compress_results else self.xml_file_names
                util.printOut("In order to get HTML and CSV tables, run\n{0} '{1}'"
                              .format(tableGeneratorPath, "' '".join(xml_file_names)))

        if isStoppedByInterrupt:
            util.printOut("\nScript was interrupted by user, some runs may not be done.\n")


    def close(self):
        """Do all necessary cleanup."""
        if self.compress_results:
            self.log_zip.close()


    def get_filename(self, runSetName, fileExtension):
        '''
        This function returns the name of the file for a run set
        with an extension ("txt", "xml").
        '''

        fileName = self.benchmark.output_base_name + ".results."

        if runSetName:
            fileName += runSetName + "."

        return fileName + fileExtension


    def format_sourcefile_name(self, fileName, runSet):
        '''
        Formats the file name of a program for printing on console.
        '''
        if fileName.startswith(runSet.common_prefix):
            fileName = fileName[len(runSet.common_prefix):]
        return fileName.ljust(runSet.max_length_of_filename + 4)


    def _write_rough_result_xml_to_file(self, xml, filename):
        """Write a rough string version of the XML (for temporary files)."""
        # Write content to temp file first
        error = xml.get('error', None)
        xml.set('error', 'incomplete') # Mark result file as incomplete
        temp_filename = filename + ".tmp"
        with open(temp_filename, 'wb') as file:
            ET.ElementTree(xml).write(file, encoding='utf-8', xml_declaration=True)
        os.rename(temp_filename, filename)
        if error is not None:
            xml.set('error', error)
        else:
            del xml.attrib['error']

    def _write_pretty_result_xml_to_file(self, xml, filename):
        """Writes a nicely formatted XML file with DOCTYPE, and compressed if necessary."""
        if self.compress_results:
            actual_filename = filename + ".bz2"
            # Use BZ2File directly or our hack for Python 3.2
            open_func = bz2.BZ2File if hasattr(bz2.BZ2File, 'writable') else util.BZ2FileHack
        else:
            # write content to temp file first to prevent loosing data
            # in existing file if writing fails
            actual_filename = filename + ".tmp"
            open_func = open

        with io.TextIOWrapper(open_func(actual_filename, 'wb'), encoding='utf-8') as file:
            rough_string = ET.tostring(xml, encoding='unicode')
            reparsed = minidom.parseString(rough_string)
            doctype = minidom.DOMImplementation().createDocumentType(
                    'result', RESULT_XML_PUBLIC_ID, RESULT_XML_SYSTEM_ID)
            reparsed.insertBefore(doctype, reparsed.documentElement)
            reparsed.writexml(file, indent="", addindent="  ", newl="\n", encoding="utf-8")

        if self.compress_results:
            # try to delete uncompressed file (would have been overwritten in no-compress-mode)
            try:
                os.remove(filename)
            except OSError:
                pass
            self.all_created_files.discard(filename)
            self.all_created_files.add(actual_filename)
        else:
            os.rename(actual_filename, filename)
            self.all_created_files.add(filename)

        return filename


class Statistics(object):

    def __init__(self):
        self.dic = collections.defaultdict(int)
        self.counter = 0
        self.score = 0
        self.max_score = 0

    def add_result(self, run):
        self.counter += 1
        self.dic[run.category] += 1
        self.dic[(run.category, result.get_result_classification(run.status))] += 1
        self.score += result.score_for_task(run.identifier, run.properties, run.category, run.status)
        #if run.properties:
        self.max_score += result.score_for_task(run.identifier, run.properties, result.CATEGORY_CORRECT, None)

    def print_to_terminal(self):
        correct = self.dic[result.CATEGORY_CORRECT]
        correct_true = self.dic[(result.CATEGORY_CORRECT, result.RESULT_CLASS_TRUE)]
        correct_false = correct - correct_true
        incorrect = self.dic[result.CATEGORY_WRONG]
        incorrect_true = self.dic[(result.CATEGORY_WRONG, result.RESULT_CLASS_TRUE)]
        incorrect_false = incorrect - incorrect_true

        width = 6
        output = ['',
                 'Statistics:' + str(self.counter).rjust(width + 9) + ' Files',
                 '  correct:          ' + str(correct).rjust(width),
                 '    correct true:   ' + str(correct_true).rjust(width),
                 '    correct false:  ' + str(correct_false).rjust(width),
                 '  incorrect:        ' + str(incorrect).rjust(width),
                 '    incorrect true: ' + str(incorrect_true).rjust(width),
                 '    incorrect false:' + str(incorrect_false).rjust(width),
                 '  unknown:          ' + str(self.dic[result.CATEGORY_UNKNOWN] + self.dic[result.CATEGORY_ERROR]).rjust(width),
                 ]
        if self.max_score:
            output.append(
                 '  Score:            ' + str(self.score).rjust(width) + ' (max: ' + str(self.max_score) + ')'
                 )
        util.printOut('\n'.join(output)+'\n')
