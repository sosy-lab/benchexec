# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import base64
import bz2
import collections
import datetime
import decimal
import io
import os
import shlex
import threading
import time
import sys

# Need to disable pytype for minidom due to https://github.com/google/pytype/issues/1130
from xml.dom import minidom  # pytype: disable=pyi-error
from xml.etree import ElementTree
import zipfile

import benchexec
from benchexec.model import MEMLIMIT, TIMELIMIT, CORELIMIT
from benchexec import filewriter
from benchexec import intel_cpu_energy
from benchexec import result
from benchexec import util

RESULT_XML_PUBLIC_ID = "+//IDN sosy-lab.org//DTD BenchExec result 3.0//EN"
RESULT_XML_SYSTEM_ID = "https://www.sosy-lab.org/benchexec/result-3.0.dtd"

# colors for column status in terminal
COLOR_GREEN = "\033[32;1m{0}\033[m"
COLOR_RED = "\033[31;1m{0}\033[m"
COLOR_ORANGE = "\033[33;1m{0}\033[m"
COLOR_MAGENTA = "\033[35;1m{0}\033[m"
COLOR_DEFAULT = "{0}"
UNDERLINE = "\033[4m{0}\033[0m"

COLOR_DIC = collections.defaultdict(lambda: COLOR_DEFAULT)
TERMINAL_TITLE = ""

if util.should_color_output():
    COLOR_DIC.update(
        {
            result.CATEGORY_CORRECT: COLOR_GREEN,
            result.CATEGORY_WRONG: COLOR_RED,
            result.CATEGORY_UNKNOWN: COLOR_ORANGE,
            result.CATEGORY_ERROR: COLOR_MAGENTA,
            result.CATEGORY_MISSING: COLOR_DEFAULT,
        }
    )
if sys.stdout.isatty():
    _term = os.environ.get("TERM", "")
    if _term.startswith(("xterm", "rxvt")):
        TERMINAL_TITLE = "\033]0;Task {0}\007"
    elif _term.startswith("screen"):
        TERMINAL_TITLE = "\033kTask {0}\033\\"

LEN_OF_STATUS = 25

# the number of digits after the decimal separator for text output of time columns with times
TIME_PRECISION = 2
_BYTE_FACTOR = 1000  # byte in kilobyte


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
        if self.benchmark.rlimits.memory:
            memlimit = str(self.benchmark.rlimits.memory) + "B"
        if self.benchmark.rlimits.cputime:
            timelimit = str(self.benchmark.rlimits.cputime) + "s"
        if self.benchmark.rlimits.cpu_cores:
            corelimit = str(self.benchmark.rlimits.cpu_cores)

        # create folder for file-specific log-files.
        os.makedirs(benchmark.log_folder, exist_ok=True)

        self.store_header_in_xml(version, memlimit, timelimit, corelimit)
        self.write_header_to_log(sysinfo)

        if sysinfo:
            # store systemInfo in XML
            self.store_system_info(
                sysinfo.os,
                sysinfo.cpu_model,
                sysinfo.cpu_number_of_cores,
                sysinfo.cpu_max_frequency,
                sysinfo.memory,
                sysinfo.hostname,
                environment=sysinfo.environment,
                cpu_turboboost=sysinfo.cpu_turboboost,
            )
        self.xml_file_names = []

        if compress_results:
            self.log_zip = zipfile.ZipFile(
                benchmark.log_zip, mode="w", compression=zipfile.ZIP_DEFLATED
            )
            self.log_zip_lock = threading.Lock()
            self.all_created_files.add(benchmark.log_zip)

    def store_system_info(
        self,
        opSystem,
        cpu_model,
        cpu_number_of_cores,
        cpu_max_frequency,
        memory,
        hostname,
        runSet=None,
        environment={},
        cpu_turboboost=None,
    ):
        for systemInfo in self.xml_header.findall("systeminfo"):
            if systemInfo.attrib["hostname"] == hostname:
                return

        osElem = ElementTree.Element("os", name=opSystem)
        cpuElem = ElementTree.Element(
            "cpu",
            model=cpu_model,
            cores=cpu_number_of_cores,
            frequency=str(cpu_max_frequency) + "Hz",
        )
        if cpu_turboboost is not None:
            cpuElem.set("turboboostActive", str(cpu_turboboost).lower())
        ramElem = ElementTree.Element("ram", size=str(memory) + "B")
        systemInfo = ElementTree.Element("systeminfo", hostname=hostname)
        systemInfo.append(osElem)
        systemInfo.append(cpuElem)
        systemInfo.append(ramElem)
        env = ElementTree.SubElement(systemInfo, "environment")
        for var, value in sorted(environment.items()):
            elem = ElementTree.SubElement(env, "var", name=var)
            if util.is_legal_for_xml(value):
                elem.text = value
            else:
                elem.text = base64.standard_b64encode(value.encode()).decode()
                elem.attrib["encoding"] = "base64"

        self.xml_header.append(systemInfo)
        if runSet:
            # insert before <run> tags to conform with DTD
            i = None
            for i, elem in enumerate(runSet.xml):  # noqa: B007
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
        self.xml_header.set("error", msg or "unknown error")
        if runSet:
            runSet.xml.set("error", msg or "unknown error")

    def store_header_in_xml(self, version, memlimit, timelimit, corelimit):
        # store benchmarkInfo in XML
        self.xml_header = ElementTree.Element(
            "result",
            benchmarkname=self.benchmark.name,
            date=self.benchmark.start_time.strftime("%Y-%m-%d %H:%M:%S %Z"),
            starttime=self.benchmark.start_time.isoformat(),
            tool=self.benchmark.tool_name,
            version=version,
            toolmodule=self.benchmark.tool_module,
            generator="BenchExec " + benchexec.__version__,
        )
        if self.benchmark.display_name:
            self.xml_header.set("displayName", self.benchmark.display_name)

        if memlimit is not None:
            self.xml_header.set(MEMLIMIT, memlimit)
        if timelimit is not None:
            self.xml_header.set(TIMELIMIT, timelimit)
        if corelimit is not None:
            self.xml_header.set(CORELIMIT, corelimit)

        if self.benchmark.description:
            description_tag = ElementTree.Element("description")
            description_tag.text = self.benchmark.description
            self.xml_header.append(description_tag)

        # store columnTitles in XML, this are the default columns, that are shown in a default html-table from table-generator
        columntitlesElem = ElementTree.Element("columns")
        columntitlesElem.append(ElementTree.Element("column", title="status"))
        columntitlesElem.append(ElementTree.Element("column", title="cputime"))
        columntitlesElem.append(ElementTree.Element("column", title="walltime"))
        for column in self.benchmark.columns:
            columnElem = ElementTree.Element("column", title=column.title)
            columntitlesElem.append(columnElem)
        self.xml_header.append(columntitlesElem)

    def write_header_to_log(self, sysinfo):
        """
        This method writes information about benchmark and system into txt_file.
        """
        runSetName = None
        run_sets = [
            runSet for runSet in self.benchmark.run_sets if runSet.should_be_executed()
        ]
        if len(run_sets) == 1:
            # in case there is only a single run set to to execute, we can use its name
            runSetName = run_sets[0].name

        columnWidth = 25
        simpleLine = "-" * 60 + "\n\n"

        def format_line(key, value):
            if value is None:
                return ""
            return ((key + ":").ljust(columnWidth) + str(value)).strip() + "\n"

        def format_byte(key, value):
            if value is None:
                return ""
            return format_line(key, str(value / _BYTE_FACTOR / _BYTE_FACTOR) + " MB")

        def format_time(key, value):
            if value is None:
                return ""
            return format_line(key, str(value) + " s")

        header = (
            "   BENCHMARK INFORMATION\n"
            + (
                (self.benchmark.display_name + "\n")
                if self.benchmark.display_name
                else ""
            )
            + format_line("benchmark definition", self.benchmark.benchmark_file)
            + format_line("name", self.benchmark.name)
            + format_line("run sets", ", ".join(run_set.name for run_set in run_sets))
            + format_line(
                "date", self.benchmark.start_time.strftime("%a, %Y-%m-%d %H:%M:%S %Z")
            )
            + format_line(
                "tool", self.benchmark.tool_name + " " + self.benchmark.tool_version
            )
            + format_line("tool executable", self.benchmark.executable)
            + format_line("options", shlex.join(self.benchmark.options))
            + format_line(
                "property file", util.text_or_none(self.benchmark.propertytag)
            )
        )
        if self.benchmark.num_of_threads > 1:
            header += format_line("parallel runs", self.benchmark.num_of_threads)

        header += (
            "resource limits:\n"
            + format_byte("- memory", self.benchmark.rlimits.memory)
            + format_time("- time", self.benchmark.rlimits.cputime)
            + format_line("- cpu cores", self.benchmark.rlimits.cpu_cores)
        )

        header += (
            "hardware requirements:\n"
            + format_line("- cpu model", self.benchmark.requirements.cpu_model)
            + format_line("- cpu cores", self.benchmark.requirements.cpu_cores)
            + format_byte("- memory", self.benchmark.requirements.memory)
            + simpleLine
        )

        if sysinfo:
            header += (
                "   SYSTEM INFORMATION\n"
                + format_line("host", sysinfo.hostname)
                + format_line("os", sysinfo.os)
                + format_line("cpu", sysinfo.cpu_model)
                + format_line("- cores", sysinfo.cpu_number_of_cores)
                + format_line(
                    "- max frequency",
                    str(sysinfo.cpu_max_frequency / 1000 / 1000) + " MHz",
                )
                + format_line("- turbo boost enabled", sysinfo.cpu_turboboost)
                + format_byte("ram", sysinfo.memory)
                + simpleLine
            )

        self.description = header

        # write to file
        txt_file_name = self.get_filename(runSetName, "txt")
        self.txt_file = filewriter.FileWriter(txt_file_name, self.description)
        self.all_created_files.add(txt_file_name)

    def output_before_run_set(self, runSet, start_time=None):
        """
        The method output_before_run_set() calculates the length of the
        first column for the output in terminal and stores information
        about the runSet in XML.
        @param runSet: current run set
        """
        xml_file_name = self.get_filename(runSet.name, "xml")

        identifier_names = [run.identifier for run in runSet.runs]

        # common prefix of file names
        runSet.common_prefix = util.common_base_dir(identifier_names)
        if runSet.common_prefix:
            runSet.common_prefix += os.path.sep

        # length of the first column in terminal
        runSet.max_length_of_filename = (
            max(len(file) for file in identifier_names) if identifier_names else 20
        )
        runSet.max_length_of_filename = max(
            20, runSet.max_length_of_filename - len(runSet.common_prefix)
        )

        # write run set name to terminal
        numberOfFiles = len(runSet.runs)
        numberOfFilesStr = (
            "     (1 file)" if numberOfFiles == 1 else f"     ({numberOfFiles} files)"
        )
        util.printOut(
            "\nexecuting run set"
            + (" '" + runSet.name + "'" if runSet.name else "")
            + numberOfFilesStr
            + TERMINAL_TITLE.format(runSet.full_name)
        )

        # write information about the run set into txt_file
        self.writeRunSetInfoToLog(runSet)

        # prepare information for text output
        for run in runSet.runs:
            run.resultline = self.format_sourcefile_name(run.identifier, runSet)

            if run.sourcefiles:
                adjusted_identifier = util.relative_path(run.identifier, xml_file_name)
            else:
                # If no source files exist the task doesn't point to any file that could be downloaded.
                # In this case, the name doesn't have to be adjusted because it's no path.
                adjusted_identifier = run.identifier

            # prepare XML structure for each run and runSet
            run.xml = ElementTree.Element("run", name=adjusted_identifier)
            if run.sourcefiles:
                adjusted_sourcefiles = (
                    util.relative_path(s, xml_file_name) for s in run.sourcefiles
                )
                run.xml.set("files", "[" + ", ".join(adjusted_sourcefiles) + "]")
            if run.specific_options:
                run.xml.set("options", " ".join(run.specific_options))
            if run.properties:
                all_properties = (prop.name for prop in run.properties)
                run.xml.set("properties", " ".join(sorted(all_properties)))
            if len(run.properties) == 1:
                prop = run.properties[0]
                run.xml.set(
                    "propertyFile", util.relative_path(prop.filename, xml_file_name)
                )
                expected_result = str(run.expected_results.get(prop.filename, ""))
                if expected_result:
                    run.xml.set("expectedVerdict", expected_result)

        block_name = runSet.blocks[0].name if len(runSet.blocks) == 1 else None
        runSet.xml = self.runs_to_xml(runSet, runSet.runs, block_name)
        if start_time:
            runSet.xml.set("starttime", start_time.isoformat())
        elif not self.benchmark.config.start_time:
            runSet.xml.set("starttime", util.read_local_time().isoformat())

        # write (empty) results to XML
        runSet.xml_file_name = xml_file_name
        self._write_rough_result_xml_to_file(runSet.xml, runSet.xml_file_name)
        runSet.xml_file_last_modified_time = time.monotonic()
        self.all_created_files.add(runSet.xml_file_name)
        self.xml_file_names.append(runSet.xml_file_name)

    def output_for_skipping_run_set(self, runSet, reason=None):
        """
        This function writes a simple message to terminal and logfile,
        when a run set is skipped.
        There is no message about skipping a run set in the xml-file.
        """

        # print to terminal
        util.printOut(
            "\nSkipping run set"
            + (" '" + runSet.name + "'" if runSet.name else "")
            + (" " + reason if reason else "")
        )

        # write into txt_file
        runSetInfo = "\n\n"
        if runSet.name:
            runSetInfo += runSet.name + "\n"
        runSetInfo += (
            f"Run set {runSet.index} of {len(self.benchmark.run_sets)}: "
            f"skipped {reason or ''}".rstrip()
        )
        runSetInfo += "\n"
        self.txt_file.append(runSetInfo)

    def writeRunSetInfoToLog(self, runSet):
        """
        This method writes the information about a run set into the txt_file.
        """

        runSetInfo = "\n\n"
        if runSet.name:
            runSetInfo += runSet.name + "\n"
        runSetInfo += (
            f"Run set {runSet.index} of {len(self.benchmark.run_sets)} "
            f"with options '{' '.join(runSet.options)}' and "
            f"propertyfile '{util.text_or_none(runSet.propertytag)}'\n\n"
        )

        titleLine = self.create_output_line(
            runSet,
            "inputfile",
            "status",
            "cpu time",
            "wall time",
            "host",
            self.benchmark.columns,
            True,
        )

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
            progressIndicator = f" ({runSet.started_runs}/{len(runSet.runs)})"
            terminalTitle = TERMINAL_TITLE.format(runSet.full_name + progressIndicator)
            if self.benchmark.num_of_threads == 1:
                util.printOut(
                    terminalTitle
                    + timeStr
                    + self.format_sourcefile_name(run.identifier, runSet),
                    "",
                )
            else:
                util.printOut(
                    terminalTitle
                    + timeStr
                    + "starting   "
                    + self.format_sourcefile_name(run.identifier, runSet)
                )
        finally:
            OutputHandler.print_lock.release()

    def output_after_run(self, run):
        """
        The method output_after_run() prints filename, result, time and status
        of a run to terminal and stores all data in XML
        """

        # format times, type is changed from float to string!
        cputime_str = util.format_number(run.values.get("cputime"), TIME_PRECISION)
        walltime_str = util.format_number(run.values.get("walltime"), TIME_PRECISION)

        # format numbers, number_of_digits is optional, so it can be None
        for column in run.columns:
            if column.number_of_digits is not None:
                # if the number ends with "s" or another letter, remove it
                if (not column.value.isdigit()) and column.value[-2:-1].isdigit():
                    column.value = column.value[:-1]

                try:
                    floatValue = float(column.value)
                    column.value = util.format_number(
                        floatValue, column.number_of_digits
                    )
                except ValueError:  # if value is no float, don't format it
                    pass

        # store information in run
        run.resultline = self.create_output_line(
            run.runSet,
            run.identifier,
            run.status,
            cputime_str,
            walltime_str,
            run.values.get("host"),
            run.columns,
        )
        self.add_values_to_run_xml(run)

        # output in terminal/console
        statusStr = COLOR_DIC[run.category].format(run.status.ljust(LEN_OF_STATUS))

        try:
            OutputHandler.print_lock.acquire()

            valueStr = statusStr + cputime_str.rjust(8) + walltime_str.rjust(8)
            if self.benchmark.num_of_threads == 1:
                util.printOut(valueStr)
            else:
                timeStr = time.strftime("%H:%M:%S", time.localtime()) + " " * 14
                util.printOut(
                    timeStr
                    + self.format_sourcefile_name(run.identifier, run.runSet)
                    + valueStr
                )

            # write result in txt_file and XML
            self.txt_file.append(run.resultline + "\n", keep=False)
            self.statistics.add_result(run)

            # we don't want to write this file to often, it can slow down the whole script,
            # so we wait at least 10 seconds between two write-actions
            currentTime = time.monotonic()
            if currentTime - run.runSet.xml_file_last_modified_time > 60:
                self._write_rough_result_xml_to_file(
                    run.runSet.xml, run.runSet.xml_file_name
                )
                run.runSet.xml_file_last_modified_time = time.monotonic()

        finally:
            OutputHandler.print_lock.release()

        if self.compress_results:
            log_file_path = os.path.relpath(
                run.log_file, os.path.join(self.benchmark.log_folder, os.pardir)
            )
            with self.log_zip_lock:
                self.log_zip.write(run.log_file, log_file_path)
            os.remove(run.log_file)
        else:
            self.all_created_files.add(run.log_file)

        if os.path.isdir(run.result_files_folder):
            self.all_created_files.add(run.result_files_folder)

    def output_after_run_set(
        self, runSet, cputime=None, walltime=None, energy={}, cache={}, end_time=None
    ):
        """
        The method output_after_run_set() stores the times of a run set in XML.
        @params cputime, walltime: accumulated times of the run set
        """

        self.add_values_to_run_set_xml(runSet, cputime, walltime, energy, cache)

        if end_time:
            runSet.xml.set("endtime", end_time.isoformat())
        elif not self.benchmark.config.start_time:
            runSet.xml.set("endtime", util.read_local_time().isoformat())

        # Write results to files. This overwrites the intermediate files written
        # from output_after_run with the proper results.
        self._write_pretty_result_xml_to_file(runSet.xml, runSet.xml_file_name)

        if len(runSet.blocks) > 1:
            for block in runSet.blocks:
                blockFileName = self.get_filename(runSet.name, block.name + ".xml")
                block_xml = self.runs_to_xml(runSet, block.runs, block.name)
                block_xml.set("starttime", runSet.xml.get("starttime"))
                if runSet.xml.get("endtime"):
                    block_xml.set("endtime", runSet.xml.get("endtime"))
                self._write_pretty_result_xml_to_file(block_xml, blockFileName)

        self.txt_file.append(self.run_set_to_text(runSet, cputime, walltime, energy))

    def run_set_to_text(self, runSet, cputime=0, walltime=0, energy={}):
        lines = []

        # store values of each run
        for run in runSet.runs:
            lines.append(run.resultline)

        lines.append(runSet.simpleLine)

        # write endline into txt_file
        endline = f"Run set {runSet.index}"

        # format time, type is changed from float to string!
        cputime_str = (
            "None" if cputime is None else util.format_number(cputime, TIME_PRECISION)
        )
        walltime_str = (
            "None" if walltime is None else util.format_number(walltime, TIME_PRECISION)
        )
        lines.append(
            self.create_output_line(
                runSet, endline, "done", cputime_str, walltime_str, "-", []
            )
        )

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
            runsElem.set(
                "name",
                ((runSet.real_name + ".") if runSet.real_name else "") + blockname,
            )
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
        self.add_column_to_xml(runElem, "status", run.status)
        self.add_column_to_xml(runElem, "@category", run.category)  # hidden
        self.add_column_to_xml(runElem, "", run.values)

        for column in run.columns:
            self.add_column_to_xml(runElem, column.title, column.value)

        # Sort child elements by hidden and title attributes
        runElem[:] = sorted(
            runElem, key=lambda elem: (elem.get("hidden", ""), elem.get("title"))
        )

    def add_values_to_run_set_xml(self, runSet, cputime, walltime, energy, cache):
        """
        This function adds the result values to the XML representation of a runSet.
        """
        self.add_column_to_xml(runSet.xml, "cputime", cputime)
        self.add_column_to_xml(runSet.xml, "walltime", walltime)
        energy = intel_cpu_energy.format_energy_results(energy)
        for energy_key, energy_value in energy.items():
            self.add_column_to_xml(runSet.xml, energy_key, energy_value)
        for cache_key, cache_value in cache.items():
            self.add_column_to_xml(runSet.xml, cache_key, cache_value)

    def add_column_to_xml(self, xml, title, value, prefix="", value_suffix=""):
        if value is None:
            return

        if isinstance(value, dict):
            for key, item_value in value.items():
                if prefix:
                    common_prefix = prefix + "_" + title
                else:
                    common_prefix = title
                self.add_column_to_xml(xml, key, item_value, prefix=common_prefix)
            return

        if hasattr(value, "__getitem__") and not isinstance(value, (str, bytes)):
            value = ",".join(map(str, value))  # pytype: disable=wrong-arg-types
        elif isinstance(value, datetime.datetime):
            value = value.isoformat()
        elif isinstance(value, decimal.Decimal):
            value = util.print_decimal(value)

        if prefix:
            title = prefix + "_" + title
        if title[0] == "@":
            hidden = True
            title = title[1:]
        else:
            hidden = False

        if not value_suffix and not isinstance(value, (str, bytes)):
            if title.startswith("cputime") or title.startswith("walltime"):
                value_suffix = "s"
            elif title.startswith("cpuenergy"):
                value_suffix = "J"
            elif title.startswith("blkio-") or title.startswith("memory"):
                value_suffix = "B"
            elif title.startswith("llc"):
                if not title.startswith("llc_misses"):
                    value_suffix = "B"
            elif title.startswith("mbm"):
                value_suffix = "B/s"
            elif title.startswith("pressure-") and title.endswith("-some"):
                value_suffix = "s"

        value = f"{value}{value_suffix}"

        element = ElementTree.Element("column", title=title, value=value)
        if hidden:
            element.set("hidden", "true")
        xml.append(element)

    def create_output_line(
        self,
        runSet,
        sourcefile,
        status,
        cputime_delta,
        walltime_delta,
        host,
        columns,
        isFirstLine=False,
    ):
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

        outputLine = (
            self.format_sourcefile_name(sourcefile, runSet)
            + status.ljust(LEN_OF_STATUS)
            + cputime_delta.rjust(lengthOfTime)
            + walltime_delta.rjust(lengthOfTime)
            + str(host).rjust(lengthOfTime)
        )

        for column in columns:
            columnLength = max(minLengthOfColumns, len(column.title)) + 2

            if isFirstLine:
                value = column.title
            else:
                value = column.value

            outputLine = outputLine + str(value).rjust(columnLength)

        return outputLine

    def output_after_benchmark(self, isStoppedByInterrupt):
        stats = str(self.statistics)
        util.printOut(stats)
        self.txt_file.append(stats)

        if self.xml_file_names:

            def _find_file_relative(name):
                """
                Find a file with the given name in the same directory as this script.
                Returns a path relative to the current directory, or None.
                """
                main_dir = os.path.dirname(sys.argv[0])
                search_dirs = [
                    main_dir,
                    os.path.join(main_dir, os.path.pardir, "bin"),
                    os.path.join(os.path.dirname(__file__), os.path.pardir),
                ]
                path = util.find_executable2(name, search_dirs)

                if not path:
                    return None

                if os.path.dirname(path) in util.get_path():
                    # in PATH, just use command name
                    return os.path.basename(path)

                path = os.path.relpath(path)
                if path == name:
                    path = "./" + path  # for easier copy and paste into a shell
                return path

            tableGeneratorPath = _find_file_relative(
                "table-generator.py"
            ) or _find_file_relative("table-generator")
            if tableGeneratorPath:
                xml_file_names = (
                    [file + ".bz2" for file in self.xml_file_names]
                    if self.compress_results
                    else self.xml_file_names
                )
                cmdline = [tableGeneratorPath] + xml_file_names
                util.printOut(
                    "In order to get HTML and CSV tables, run\n" + shlex.join(cmdline)
                )

        if isStoppedByInterrupt:
            util.printOut(
                "\nScript was interrupted by user, some runs may not be done.\n"
            )

    def close(self):
        """Do all necessary cleanup."""
        self.txt_file.close()

        if self.compress_results:
            with self.log_zip_lock:
                zip_is_empty = not self.log_zip.namelist()
                self.log_zip.close()

                if zip_is_empty:
                    # remove useless ZIP file, e.g., because all runs were skipped
                    os.remove(self.benchmark.log_zip)
                    self.all_created_files.remove(self.benchmark.log_zip)

        # remove useless log folder if it is empty,
        # e.g., because all logs were written to the ZIP file
        try:
            os.rmdir(self.benchmark.log_folder)
        except OSError:
            pass

    def get_filename(self, runSetName, fileExtension):
        """
        This function returns the name of the file for a run set
        with an extension ("txt", "xml").
        """

        fileName = self.benchmark.output_base_name + ".results."

        if runSetName:
            fileName += runSetName + "."

        return fileName + fileExtension

    def format_sourcefile_name(self, fileName, runSet):
        """
        Formats the file name of a program for printing on console.
        """
        if fileName.startswith(runSet.common_prefix):
            fileName = fileName[len(runSet.common_prefix) :]
        return fileName.ljust(runSet.max_length_of_filename + 4)

    def _write_rough_result_xml_to_file(self, xml, filename):
        """Write a rough string version of the XML (for temporary files)."""
        # Write content to temp file first
        error = xml.get("error", None)
        xml.set("error", "incomplete")  # Mark result file as incomplete
        temp_filename = filename + ".tmp"
        with open(temp_filename, "wb") as file:
            ElementTree.ElementTree(xml).write(
                file, encoding="utf-8", xml_declaration=True
            )
        os.replace(temp_filename, filename)
        if error is not None:
            xml.set("error", error)
        else:
            del xml.attrib["error"]

    def _write_pretty_result_xml_to_file(self, xml, filename):
        """Writes a nicely formatted XML file with DOCTYPE, and compressed if necessary."""
        if self.compress_results:
            actual_filename = filename + ".bz2"
            open_func = bz2.BZ2File
        else:
            # write content to temp file first to prevent losing data
            # in existing file if writing fails
            actual_filename = filename + ".tmp"
            open_func = open

        with io.TextIOWrapper(
            open_func(actual_filename, "wb"), encoding="utf-8"
        ) as file:
            rough_string = ElementTree.tostring(xml, encoding="unicode")
            reparsed = minidom.parseString(rough_string)
            doctype = minidom.DOMImplementation().createDocumentType(
                "result", RESULT_XML_PUBLIC_ID, RESULT_XML_SYSTEM_ID
            )
            reparsed.insertBefore(doctype, reparsed.documentElement)
            reparsed.writexml(
                file, indent="", addindent="  ", newl="\n", encoding="utf-8"
            )

        if self.compress_results:
            # try to delete uncompressed file (would have been overwritten in no-compress-mode)
            try:
                os.remove(filename)
            except OSError:
                pass
            self.all_created_files.discard(filename)
            self.all_created_files.add(actual_filename)
        else:
            os.replace(actual_filename, filename)
            self.all_created_files.add(filename)

        return filename


class Statistics(object):
    def __init__(self):
        self.dic = collections.defaultdict(int)
        self.counter = 0
        self.score = 0
        self.max_score = None

    def add_result(self, run):
        self.counter += 1
        self.dic[run.category] += 1
        self.dic[(run.category, result.get_result_classification(run.status))] += 1
        for prop in run.properties:
            self.score += prop.compute_score(run.category, run.status) or 0
            max_score = prop.max_score(run.expected_results.get(prop.filename))
            if max_score is not None:
                self.max_score = max_score + (self.max_score or 0)

    def __str__(self):
        correct = self.dic[result.CATEGORY_CORRECT]
        correct_true = self.dic[(result.CATEGORY_CORRECT, result.RESULT_CLASS_TRUE)]
        correct_false = correct - correct_true
        incorrect = self.dic[result.CATEGORY_WRONG]
        incorrect_true = self.dic[(result.CATEGORY_WRONG, result.RESULT_CLASS_TRUE)]
        incorrect_false = incorrect - incorrect_true

        width = 6
        output = [
            "",
            "Statistics:" + str(self.counter).rjust(width + 9) + " Files",
            "  correct:          " + str(correct).rjust(width),
            "    correct true:   " + str(correct_true).rjust(width),
            "    correct false:  " + str(correct_false).rjust(width),
            "  incorrect:        " + str(incorrect).rjust(width),
            "    incorrect true: " + str(incorrect_true).rjust(width),
            "    incorrect false:" + str(incorrect_false).rjust(width),
            "  unknown:          "
            + str(
                self.dic[result.CATEGORY_UNKNOWN] + self.dic[result.CATEGORY_ERROR]
            ).rjust(width),
        ]
        if self.max_score is not None:
            output.append(
                "  Score:            "
                + str(self.score).rjust(width)
                + " (max: "
                + str(self.max_score)
                + ")"
            )
        output.append("")
        return "\n".join(output)
