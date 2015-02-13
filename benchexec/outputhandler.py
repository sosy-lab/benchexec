"""
CPAchecker is a tool for configurable software verification.
This file is part of CPAchecker.

Copyright (C) 2007-2014  Dirk Beyer
All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.


CPAchecker web page:
  http://cpachecker.sosy-lab.org
"""

# prepare for Python 3
from __future__ import absolute_import, division, print_function, unicode_literals

import threading
import time
import sys
import os
import xml.etree.ElementTree as ET

from .model import MEMLIMIT, TIMELIMIT, SOFTTIMELIMIT, CORELIMIT
from . import filewriter
from . import result
from . import util as util

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
    TERMINAL_TITLE = "\033]0;Benchmark {0}\007"
elif _term.startswith('screen'):
    TERMINAL_TITLE = "\033kBenchmark {0}\033\\"

# the number of digits after the decimal separator for text output of time columns with times
TIME_PRECISION = 2


class OutputHandler:
    """
    The class OutputHandler manages all outputs to the terminal and to files.
    """

    print_lock = threading.Lock()

    def __init__(self, benchmark, sysinfo):
        """
        The constructor of OutputHandler collects information about the benchmark and the computer.
        """

        self.all_created_files = []
        self.benchmark = benchmark
        self.statistics = Statistics()
        self.runSet = None

        version = self.benchmark.tool_version

        memlimit = None
        timelimit = None
        corelimit = None
        if MEMLIMIT in self.benchmark.rlimits:
            memlimit = str(self.benchmark.rlimits[MEMLIMIT]) + " MB"
        if SOFTTIMELIMIT in self.benchmark.rlimits:
            timelimit = str(self.benchmark.rlimits[SOFTTIMELIMIT]) + " s"
        elif TIMELIMIT in self.benchmark.rlimits:
            timelimit = str(self.benchmark.rlimits[TIMELIMIT]) + " s"
        if CORELIMIT in self.benchmark.rlimits:
            corelimit = str(self.benchmark.rlimits[CORELIMIT])

        # create folder for file-specific log-files.
        os.makedirs(benchmark.log_folder)

        self.store_header_in_xml(version, memlimit, timelimit, corelimit)
        self.write_header_to_log(version, memlimit, timelimit, corelimit, sysinfo)

        if sysinfo:
            # store systemInfo in XML
            self.store_system_info(sysinfo.os, sysinfo.cpu_model,
                                 sysinfo.cpu_number_of_cores, sysinfo.cpu_max_frequency,
                                 sysinfo.memory, sysinfo.hostname)
        self.xml_file_names = []


    def store_system_info(self, opSystem, cpu_model, cpu_number_of_cores, cpu_max_frequency, memory, hostname):
        for systemInfo in self.xml_header.findall("systeminfo"):
                    if systemInfo.attrib["hostname"] == hostname:
                        return

        osElem = ET.Element("os", {"name":opSystem})
        cpuElem = ET.Element("cpu", {"model":cpu_model, "cores":cpu_number_of_cores, "frequency":cpu_max_frequency})
        ramElem = ET.Element("ram", {"size":memory})
        systemInfo = ET.Element("systeminfo", {"hostname":hostname})
        systemInfo.append(osElem)
        systemInfo.append(cpuElem)
        systemInfo.append(ramElem)
            
        self.xml_header.append(systemInfo)
        if self.runSet and self.runSet.xml:
            self.runSet.xml.append(systemInfo)


    def set_error(self, msg):
        """
        Mark the benchmark as erroneous, e.g., because the benchmarking tool crashed.
        The message is intended as explanation for the user.
        """
        self.xml_header.set('error', msg if msg else 'unknown error')
        if self.runSet:
            self.runSet.xml.set('error', msg if msg else 'unknown error')


    def store_header_in_xml(self, version, memlimit, timelimit, corelimit):

        # store benchmarkInfo in XML
        self.xml_header = ET.Element("result",
                    {"benchmarkname": self.benchmark.name,
                     "date":  time.strftime("%y-%m-%d %H:%M", self.benchmark.start_time),
                     "tool": self.benchmark.tool_name, "version": version})

        self.xml_header.set(MEMLIMIT, memlimit if memlimit else '-')
        self.xml_header.set(TIMELIMIT, timelimit if timelimit else '-')
        self.xml_header.set(CORELIMIT, corelimit if corelimit else '-')

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
            header += "memlimit:".ljust(columnWidth) + memlimit + "\n"
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
                    + "- max frequency:".ljust(columnWidth) + sysinfo.cpu_max_frequency + "\n"\
                    + "ram:".ljust(columnWidth) + sysinfo.memory + "\n"\
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
        self.all_created_files.append(txt_file_name)


    def output_before_run_set(self, runSet):
        """
        The method output_before_run_set() calculates the length of the
        first column for the output in terminal and stores information
        about the runSet in XML.
        @param runSet: current run set
        """

        self.runSet = runSet

        sourcefiles = [run.identifier for run in runSet.runs]

        # common prefix of file names
        self.common_prefix = util.common_base_dir(sourcefiles) + os.path.sep

        # length of the first column in terminal
        self.max_length_of_filename = max(len(file) for file in sourcefiles) if sourcefiles else 20
        self.max_length_of_filename = max(20, self.max_length_of_filename - len(self.common_prefix))

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
            run.resultline = self.format_sourcefile_name(run.identifier)

        # prepare XML structure for each run and runSet
            run.xml = ET.Element("sourcefile", 
                                 {"name": run.identifier, "files": "[" + ", ".join(run.sourcefiles) + "]"})
            if run.specific_options:
                run.xml.set("options", " ".join(run.specific_options))
            run.xml.extend(self.xml_dummy_elements)

        runSet.xml = self.runs_to_xml(runSet, runSet.runs)

        # write (empty) results to txt_file and XML
        self.txt_file.append(self.run_set_to_text(runSet), False)
        xml_file_name = self.get_filename(runSet.name, "xml")
        self.xml_file = filewriter.FileWriter(xml_file_name,
                       util.xml_to_string(runSet.xml))
        self.xml_file.lastModifiedTime = time.time()
        self.all_created_files.append(xml_file_name)
        self.xml_file_names.append(xml_file_name)


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
                " ".join(runSet.property_files))

        titleLine = self.create_output_line("sourcefile", "status", "cpu time",
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
        try:
            OutputHandler.print_lock.acquire()

            timeStr = time.strftime("%H:%M:%S", time.localtime()) + "   "
            progressIndicator = " ({0}/{1})".format(self.runSet.runs.index(run), len(self.runSet.runs))
            terminalTitle = TERMINAL_TITLE.format(self.runSet.full_name + progressIndicator) if USE_COLORS and sys.stdout.isatty() else ""
            if self.benchmark.num_of_threads == 1:
                util.printOut(terminalTitle + timeStr + self.format_sourcefile_name(run.identifier), '')
            else:
                util.printOut(terminalTitle + timeStr + "starting   " + self.format_sourcefile_name(run.identifier))
        finally:
            OutputHandler.print_lock.release()

        # get name of file-specific log-file
        self.all_created_files.append(run.log_file)


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
        run.resultline = self.create_output_line(run.identifier, run.status,
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
                util.printOut(timeStr + self.format_sourcefile_name(run.identifier) + valueStr)

            # write result in txt_file and XML
            self.txt_file.append(self.run_set_to_text(run.runSet), False)
            self.statistics.add_result(run.category, run.status)

            # we don't want to write this file to often, it can slow down the whole script,
            # so we wait at least 10 seconds between two write-actions
            currentTime = time.time()
            if currentTime - self.xml_file.lastModifiedTime > 10:
                self.xml_file.replace(util.xml_to_string(run.runSet.xml))
                self.xml_file.lastModifiedTime = currentTime

        finally:
            OutputHandler.print_lock.release()


    def output_after_run_set(self, runSet, cputime=None, walltime=None, energy={}):
        """
        The method output_after_run_set() stores the times of a run set in XML.
        @params cputime, walltime: accumulated times of the run set
        """
        
        self.add_values_to_run_set_xml(runSet, cputime, walltime, energy)

        # write results to files
        self.xml_file.replace(util.xml_to_string(runSet.xml))

        if len(runSet.blocks) > 1:
            for block in runSet.blocks:
                blockFileName = self.get_filename(runSet.name, block.name + ".xml")
                util.write_file(
                    util.xml_to_string(self.runs_to_xml(runSet, block.runs, block.name)),
                    blockFileName
                )
                self.all_created_files.append(blockFileName)

        self.txt_file.append(self.run_set_to_text(runSet, True, cputime, walltime, energy))


    def run_set_to_text(self, runSet, finished=False, cputime=0, walltime=0, energy={}):
        lines = []

        # store values of each run
        for run in runSet.runs: lines.append(run.resultline)

        lines.append(runSet.simpleLine)

        # write endline into txt_file
        if finished:
            endline = ("Run set {0}".format(runSet.index))

            # format time, type is changed from float to string!
            cputime_str  = "None" if cputime  is None else util.format_number(cputime, TIME_PRECISION)
            walltime_str = "None" if walltime is None else util.format_number(walltime, TIME_PRECISION)
            lines.append(self.create_output_line(endline, "done", cputime_str,
                             walltime_str, "-", []))

        return "\n".join(lines) + "\n"

    def runs_to_xml(self, runSet, runs, blockname=None):
        """
        This function creates the XML structure for a list of runs
        """
        # copy benchmarkinfo, limits, columntitles, systeminfo from xml_header
        runsElem = util.copy_of_xml_element(self.xml_header)
        runsElem.set("options", " ".join(runSet.options))
        runsElem.set("propertyfiles", " ".join(runSet.property_files))
        if blockname is not None:
            runsElem.set("block", blockname)
            runsElem.set("name", ((runSet.real_name + ".") if runSet.real_name else "") + blockname)
        elif runSet.real_name:
            runsElem.set("name", runSet.real_name)

        # collect XMLelements from all runs
        for run in runs: runsElem.append(run.xml)

        return runsElem


    def add_values_to_run_xml(self, run):
        """
        This function adds the result values to the XML representation of a run.
        """
        runElem = run.xml
        for elem in list(runElem):
            runElem.remove(elem)
        self.add_column_to_xml(runElem, 'status',    run.status)
        if run.cputime is not None:
            self.add_column_to_xml(runElem, 'cputime',   str(run.cputime) + 's')
        if run.walltime is not None:
            self.add_column_to_xml(runElem, 'walltime',  str(run.walltime) + 's')
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


    def add_column_to_xml(self, xml, title, value, prefix=""):
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

        # default case: add columns
        if prefix:
            if prefix.startswith('@'):
                attributes = {"title": prefix[1:] + '_' + title, "value": str(value), "hidden": "true"}
            else:
                attributes = {"title": prefix + '_' + title, "value": str(value)}
        else:
            if title.startswith('@'):
                attributes = {"title": title[1:], "value": str(value), "hidden": "true"}
            else:
                attributes = {"title": title, "value": str(value)}
        xml.append(ET.Element("column", attributes))


    def create_output_line(self, sourcefile, status, cputime_delta, walltime_delta, host, columns, isFirstLine=False):
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
        lengthOfEnergy = 18
        minLengthOfColumns = 8

        outputLine = self.format_sourcefile_name(sourcefile) + \
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
            tableGeneratorName = 'table-generator.py'
            tableGeneratorPath = os.path.relpath(os.path.join(os.path.dirname(__file__), os.path.pardir, tableGeneratorName))
            if tableGeneratorPath == tableGeneratorName:
                tableGeneratorPath = './' + tableGeneratorName
            util.printOut("In order to get HTML and CSV tables, run\n{0} '{1}'"
                          .format(tableGeneratorPath, "' '".join(self.xml_file_names)))

        if isStoppedByInterrupt:
            util.printOut("\nScript was interrupted by user, some runs may not be done.\n")


    def get_filename(self, runSetName, fileExtension):
        '''
        This function returns the name of the file for a run set
        with an extension ("txt", "xml").
        '''

        fileName = self.benchmark.output_base_name + ".results."

        if runSetName:
            fileName += runSetName + "."

        return fileName + fileExtension


    def format_sourcefile_name(self, fileName):
        '''
        Formats the file name of a program for printing on console.
        '''
        fileName = fileName.replace(self.common_prefix, '', 1)
        return fileName.ljust(self.max_length_of_filename + 4)


class Statistics:

    def __init__(self):
        self.dic = dict((category,0) for category in COLOR_DIC)
        self.dic[(result.CATEGORY_WRONG, result.STATUS_TRUE_PROP)] = 0
        self.counter = 0

    def add_result(self, category, status):
        self.counter += 1
        assert category in self.dic
        if category == result.CATEGORY_WRONG and status == result.STATUS_TRUE_PROP:
            self.dic[(result.CATEGORY_WRONG, result.STATUS_TRUE_PROP)] += 1
        self.dic[category] += 1


    def print_to_terminal(self):
        util.printOut('\n'.join(['\nStatistics:' + str(self.counter).rjust(13) + ' Files',
                 '    correct:        ' + str(self.dic[result.CATEGORY_CORRECT]).rjust(4),
                 '    unknown:        ' + str(self.dic[result.CATEGORY_UNKNOWN] + self.dic[result.CATEGORY_ERROR]).rjust(4),
                 '    false positives:' + str(self.dic[result.CATEGORY_WRONG] - self.dic[(result.CATEGORY_WRONG, result.STATUS_TRUE_PROP)]).rjust(4) + \
                 '        (result is false, file is true or has a different false-property)',
                 '    false negatives:' + str(self.dic[(result.CATEGORY_WRONG, result.STATUS_TRUE_PROP)]).rjust(4) + \
                 '        (result is true, file is false)',
                 '']))
