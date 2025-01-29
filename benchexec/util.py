# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

"""
This module contains some useful functions for Strings, XML or Lists.
"""

import argparse
import collections
import datetime
import errno
import fnmatch
import glob
import logging
import os
import re
import shutil
import signal as _signal
import stat
import subprocess
import sys
from ctypes.util import find_library
import ctypes
from xml.etree import ElementTree


_BYTE_FACTOR = 1000  # byte in kilobyte
_FREQUENCY_FACTOR = 1000  # Hz in kHz

TIMESTAMP_FILENAME_FORMAT = "%Y-%m-%d_%H-%M-%S"
"""Our standard timestamp format for file names (without colons etc.)"""


def printOut(value, end="\n"):
    """
    This function prints the given String immediately and flushes the output.
    """
    sys.stdout.write(value)
    sys.stdout.write(end)
    sys.stdout.flush()


def is_comment(line):
    return not line or line.startswith("#") or line.startswith("//")


def flatten(iterable, exclude=[]):
    return [value for sublist in iterable for value in sublist if value not in exclude]


def get_list_from_xml(elem, tag="option", attributes=["name"]):
    """
    This function searches for all "option"-tags and returns a list with all attributes and texts.
    """
    return flatten(
        (
            [option.get(attr) for attr in attributes] + [option.text]
            for option in elem.findall(tag)
        ),
        exclude=[None],
    )


def get_single_child_from_xml(elem, tag):
    """
    Get a single child tag from an XML element.
    Similar to "elem.find(tag)", but warns if there are multiple child tags with the given name.
    """
    children = elem.findall(tag)
    if not children:
        return None
    if len(children) > 1:
        logging.warning(
            'Tag "%s" has more than one child tags with name "%s" in input file, '
            "ignoring all but the first.",
            elem.tag,
            tag,
        )
    return children[0]


def text_or_none(elem):
    """
    Retrieve the text content of an XML tag, or None if the element itself is None
    """
    return elem.text if elem is not None else None


def copy_of_xml_element(elem):
    """
    This method returns a shallow copy of a XML-Element.
    This method is for compatibility with Python 2.6 or earlier..
    In Python 2.7 you can use  'copyElem = elem.copy()'  instead.
    """

    copyElem = ElementTree.Element(elem.tag, elem.attrib)
    for child in elem:
        copyElem.append(child)
    return copyElem


_ILLEGAL_XML_CHARS = re.compile(r"[^\x09\x0A\x0D\x20-\xD7FF\xE000-\xFFFD]")


def is_legal_for_xml(string):
    """Check whether the given string can be written to XML documents."""
    return not re.search(_ILLEGAL_XML_CHARS, string)


def decode_to_string(toDecode):
    """
    Decode a byte string to a string, return input unchanged if it is already a string.
    This method should usually not be used because it should be clear if calling
    decode() is necessary, and because it hardcodes the UTF-8 encoding.
    """
    try:
        return toDecode.decode("utf-8")
    except AttributeError:  # bytesToDecode was of type string before
        return toDecode


def format_number(number, number_of_digits):
    """
    The function format_number() return a string-representation of a number
    with a number of digits after the decimal separator.
    If the number has more digits, it is rounded.
    If the number has less digits, zeros are added.

    @param number: the number to format
    @param digits: the number of digits
    """
    if number is None:
        return ""
    return f"{number:.{number_of_digits}f}"


class InputValueError(ValueError, argparse.ArgumentTypeError):
    """
    Exception for invalid values passed as input.
    Inherits from both ValueError and ArgumentTypeError in order to be useful
    for both inputs to called methods (should raise ValueError)
    and for inputs from user (in type handlers for argparse.add_argument).
    """

    pass


def parse_int_list(s):
    """
    Parse a comma-separated list of strings.
    The list may additionally contain ranges such as "1-5",
    which will be expanded into "1,2,3,4,5".
    """
    result = []
    for item in s.split(","):
        item = item.strip().split("-")
        if len(item) == 1:
            result.append(int(item[0]))
        elif len(item) == 2:
            start, end = item
            result.extend(range(int(start), int(end) + 1))
        else:
            raise InputValueError(f"invalid range: '{s}'")
    return result


def split_number_and_unit(s):
    """Parse a string that consists of a integer number and an optional unit.
    @param s a non-empty string that starts with an int and is followed by some letters
    @return a triple of the number (as int) and the unit
    """
    if not s:
        raise InputValueError("empty value")
    s = s.strip()
    pos = len(s)
    while pos and not s[pos - 1].isdigit():
        pos -= 1
    number = int(s[:pos])
    unit = s[pos:].strip()
    return number, unit


def parse_memory_value(s):
    """Parse a string that contains a number of bytes, optionally with a unit like MB.
    @return the number of bytes encoded by the string
    """
    number, unit = split_number_and_unit(s)
    if not unit or unit == "B":
        return number
    elif unit == "kB":
        return number * _BYTE_FACTOR
    elif unit == "MB":
        return number * _BYTE_FACTOR * _BYTE_FACTOR
    elif unit == "GB":
        return number * _BYTE_FACTOR * _BYTE_FACTOR * _BYTE_FACTOR
    elif unit == "TB":
        return number * _BYTE_FACTOR * _BYTE_FACTOR * _BYTE_FACTOR * _BYTE_FACTOR
    else:
        raise InputValueError(
            f"unknown unit: {unit} (allowed are B, kB, MB, GB, and TB)"
        )


def parse_timespan_value(s):
    """Parse a string that contains a time span, optionally with a unit like s.
    @return the number of seconds encoded by the string
    """
    number, unit = split_number_and_unit(s)
    if not unit or unit == "s":
        return number
    elif unit == "min":
        return number * 60
    elif unit == "h":
        return number * 60 * 60
    elif unit == "d":
        return number * 24 * 60 * 60
    else:
        raise InputValueError(f"unknown unit: {unit} (allowed are s, min, h, and d)")


def parse_frequency_value(s):
    """Parse a string that contains a frequency, optionally with a unit like Hz.
    @return the number of frequency encoded by the string
    """
    number, unit = split_number_and_unit(s)
    if not unit or unit == "Hz":
        return number
    elif unit == "kHz":
        return number * _FREQUENCY_FACTOR
    elif unit == "MHz":
        return number * _FREQUENCY_FACTOR * _FREQUENCY_FACTOR
    elif unit == "GHz":
        return number * _FREQUENCY_FACTOR * _FREQUENCY_FACTOR * _FREQUENCY_FACTOR
    else:
        raise InputValueError(
            f"unknown unit: {unit} (allowed are Hz, kHz, MHz, and GHz)"
        )


def non_empty_str(s):
    """Utility for requiring a non-empty string value as command-line parameter."""
    s = str(s)
    if not s:
        raise InputValueError("empty string not allowed")
    return s


def print_decimal(d):
    """
    Print a Decimal instance in non-scientific (i.e., decimal) notation with full
    precision, i.e., all digits are printed exactly as stored in the Decimal instance.
    Note that str(d) always falls back to scientific notation for very small values.
    """

    if d.is_nan():
        return "NaN"
    elif d.is_infinite():
        return "Inf" if d > 0 else "-Inf"
    assert d.is_finite()

    sign, digits, exp = d.as_tuple()
    # sign is 1 if negative
    # digits is exactly the sequence of significant digits in the decimal representation
    # exp tells us whether we need to shift digits (pos: left shift; neg: right shift).
    # left shift can only add zeros, right shift adds decimal separator

    sign = "-" if sign == 1 else ""
    digits = list(map(str, digits))

    if exp >= 0:
        if digits == ["0"]:
            # special case: return "0" instead of "0000" for "0e4"
            return sign + "0"
        return sign + "".join(digits) + ("0" * exp)

    # Split digits into parts before and after decimal separator.
    # If -exp > len(digits) the result needs to start with "0.", so we force a 0.
    integral_part = digits[:exp] or ["0"]
    decimal_part = digits[exp:]
    assert decimal_part

    return (
        sign
        + "".join(integral_part)
        + "."
        + ("0" * (-exp - len(decimal_part)))  # additional zeros if necessary
        + "".join(decimal_part)
    )


def expand_filename_pattern(pattern, base_dir):
    """
    Expand a file name pattern containing wildcards, environment variables etc.

    @param pattern: The pattern string to expand.
    @param base_dir: The directory where relative paths are based on.
    @return: A list of file names (possibly empty).
    """
    # 'join' ignores base_dir, if expandedPattern is absolute.
    # 'normpath' replaces 'A/foo/../B' with 'A/B', for pretty printing only
    pattern = os.path.normpath(os.path.join(base_dir, pattern))

    # expand tilde and variables
    pattern = os.path.expandvars(os.path.expanduser(pattern))

    # expand wildcards
    fileList = glob.glob(pattern)

    return fileList


def get_files(paths):
    changed = False
    result = []
    for path in paths:
        if os.path.isfile(path):
            result.append(path)
        elif os.path.isdir(path):
            changed = True
            for currentPath, dirs, files in os.walk(path):
                # ignore hidden files, on Linux they start with '.',
                # inplace replacement of 'dirs', because it is used later in os.walk
                files = [f for f in files if not f.startswith(".")]
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                result.extend(os.path.join(currentPath, f) for f in files)
    return result if changed else paths


def substitute_vars(template, replacements):
    """Replace certain keys with respective values in a string.
    @param template: the string in which replacements should be made
    @param replacements: a dict or a list of pairs of keys and values
    """
    result = template
    for key, value in replacements:
        result = result.replace("${" + key + "}", value)
    if "${" in result:
        logging.warning("A variable was not replaced in '%s'.", result)
    return result


def find_executable(program, fallback=None, exitOnError=True, use_current_dir=True):
    """Deprecated, prefer find_executable2"""
    dirs = get_path()
    if use_current_dir:
        dirs.append(os.path.curdir)

    found_non_executable = []  # for nicer error message
    for dir_ in dirs:
        name = os.path.join(dir_, program)
        if os.path.isfile(name):
            if os.access(name, os.X_OK):
                # file exists and is executable
                return name
            found_non_executable.append(name)

    if fallback is not None and os.path.isfile(fallback):
        if os.access(fallback, os.X_OK):
            return fallback
        found_non_executable.append(name)

    if exitOnError:
        if found_non_executable:
            sys.exit(  # noqa: R503 always raises
                f"Could not find '{program}' executable, "
                f"but found file '{found_non_executable[0]}' that is not executable."
            )
        else:
            sys.exit(  # noqa: R503 always raises
                f"Could not find '{program}' executable."
            )
    else:
        return fallback


def find_executable2(name, dirs=None, required_mode=os.X_OK):
    """
    Search for an executable file either in PATH or in given directories.

    @param name: The name of the executable to search
    @param dirs: The directories where to search (PATH will be used by default)
    @param required_mode: A valid mode parameter for os.access as filter criterion
    @return None or the path to the executable
    """
    if dirs is None:
        dirs = get_path()

    for candidate_dir in dirs:
        candidate = os.path.join(candidate_dir, name)
        if os.path.isfile(candidate) and os.access(candidate, required_mode):
            return candidate

    return None


def get_path():
    """Get list of directories in PATH environment variable."""
    return os.environ["PATH"].split(os.path.pathsep)


def common_base_dir(paths):
    # os.path.commonprefix returns the common prefix, not the common directory
    return os.path.dirname(os.path.commonprefix(paths))


def relative_path(destination, start):
    return os.path.relpath(destination, os.path.dirname(start))


def path_is_below(path, target_path):
    """
    Check whether path is below target_path.
    Works for bytes and strings, but both arguments need to have same type.
    """
    # compare with trailing slashes for cases like /foo and /foobar
    empty_path = path[:0]  # empty string, but works for bytes and strings
    path = os.path.join(path, empty_path)
    target_path = os.path.join(target_path, empty_path)
    return path.startswith(target_path)


def log_rmtree_error(func, arg, exc_info):
    """Suited as onerror handler for (sh)util.rmtree() that logs a warning."""
    logging.warning("Failure during '%s(%s)': %s", func.__name__, arg, exc_info[1])


def rmtree(path, ignore_errors=False, onerror=None):
    """Same as shutil.rmtree, but supports directories without write or execute permissions."""
    if ignore_errors:

        def onerror(*args):
            pass

    elif onerror is None:

        def onerror(*args):
            raise

    for root, dirs, _unused_files in os.walk(path):
        for directory in dirs:
            try:
                abs_directory = os.path.join(root, directory)
                os.chmod(abs_directory, stat.S_IRWXU)
            except OSError as e:
                onerror(os.chmod, abs_directory, e)
    shutil.rmtree(path, ignore_errors=ignore_errors, onerror=onerror)


def copy_all_lines_from_to(inputFile, outputFile):
    """Copy all lines from an input file object to an output file object."""
    currentLine = inputFile.readline()
    while currentLine:
        outputFile.write(currentLine)
        currentLine = inputFile.readline()


def write_file(content, *path, force=False):
    """
    Simply write some content to a file, overriding the file if necessary.
    If force is set this will attempt to ignore missing write permissions.
    """
    filename = os.path.join(*path)
    try:
        with open(filename, "w") as file:
            return file.write(content)
    except OSError:
        if force:
            os.chmod(filename, stat.S_IRUSR | stat.S_IWUSR)
            write_file(content, filename)
        else:
            raise


def shrink_text_file(filename, max_size, removal_marker=None):
    """Shrink a text file to approximately maxSize bytes
    by removing lines from the middle of the file.
    """
    file_size = os.path.getsize(filename)
    assert file_size > max_size

    # We partition the file into 3 parts:
    # A) start: maxSize/2 bytes we want to keep
    # B) middle: part we want to remove
    # C) end: maxSize/2 bytes we want to keep

    # Trick taken from StackOverflow:
    # https://stackoverflow.com/questions/2329417/fastest-way-to-delete-a-line-from-large-file-in-python
    # We open the file twice at the same time, once for reading (input_file) and once for writing (output_file).
    # We position output_file at the beginning of part B
    # and input_file at the beginning of part C.
    # Then we copy the content of C into B, overwriting what is there.
    # Afterwards we truncate the file after A+C.

    with open(filename, "r+b") as output_file:
        with open(filename, "rb") as input_file:
            # Position outputFile between A and B
            output_file.seek(max_size // 2)
            output_file.readline()  # jump to end of current line so that we truncate at line boundaries
            if output_file.tell() == file_size:
                # readline jumped to end of file because of a long line
                return

            if removal_marker:
                output_file.write(removal_marker.encode())

            # Position inputFile between B and C
            # jump to beginning of second part we want to keep from end of file
            input_file.seek(-max_size // 2, os.SEEK_END)
            input_file.readline()  # jump to end of current line so that we truncate at line boundaries

            # Copy C over B
            copy_all_lines_from_to(input_file, output_file)

            output_file.truncate()


def read_file(*path):
    """
    Read the full content of a file.
    """
    with open(os.path.join(*path)) as f:
        return f.read().strip()


def try_read_file(*path):
    """Read the full content of a file if possible, return None otherwise."""
    try:
        return read_file(*path).strip()
    except OSError:
        return None


def read_key_value_pairs_from_file(*path):
    """
    Read key value pairs from a file (each pair on a separate line).
    Key and value are separated by ' ' as often used by the kernel.
    @return a generator of tuples
    """
    with open(os.path.join(*path)) as f:
        for line in f:
            yield line.split(" ", 1)  # maxsplit=1


def is_url(path_or_url):
    return "://" in path_or_url or path_or_url.startswith("file:")


class ProcessExitCode(collections.namedtuple("ProcessExitCode", "raw value signal")):
    """Tuple for storing the exit status indication given by a os.wait() call.
    Only value or signal are present, not both
    (a process cannot return a value when it is killed by a signal).
    """

    @classmethod
    def from_raw(cls, exitcode):
        if not (0 <= exitcode < 2**16):
            raise ValueError(f"invalid exitcode {exitcode}")
        # calculation is: exitcode == (returnvalue * 256) + exitsignal
        # highest bit of exitsignal shows only whether a core file was produced, we clear it
        exitsignal = exitcode & 0x7F
        returnvalue = exitcode >> 8
        if exitsignal == 0:
            # signal 0 does not exist, this means there was no signal that killed the process
            exitsignal = None
        else:
            assert (
                returnvalue == 0
            ), f"returnvalue {returnvalue}, although exitsignal is {exitsignal}"
            returnvalue = None
        return cls(exitcode, returnvalue, exitsignal)

    @classmethod
    def create(cls, value=None, signal=None):
        """
        Create an instance of either a return value or an exit signal.
        The other parameter must be None.
        """
        if value is None and signal is None:
            raise ValueError("Need return value or exit signal for ProcessExitCode")
        if value is not None and signal is not None:
            raise ValueError("Cannot create ProcessExitCode with both value and signal")
        if value is not None and not (0 <= value <= 255):
            raise ValueError(f"Invalid value {value} for return value")
        if signal is not None and not (1 <= signal <= 127):
            raise ValueError(f"Invalid value {value} for exit signal")

        exitcode = ((value or 0) * 256) + (signal or 0)
        return cls(exitcode, value, signal)

    def __str__(self):
        return (
            f"exit signal {self.signal}"
            if self.signal
            else f"return value {self.value}"
        )

    def __bool__(self):
        return bool(self.signal or self.value)

    def __nonzero__(self):
        return self.__bool__()


def kill_process(pid, sig=None):
    """Try to send signal to given process."""
    if sig is None:
        # set default lazily, otherwise importing fails on Windows
        sig = _signal.SIGKILL
    try:
        os.kill(pid, sig)
    except OSError as e:
        if e.errno == errno.ESRCH:
            # process itself returned and exited before killing
            logging.debug(
                "Failure %s while killing process %s with signal %s: %s",
                e.errno,
                pid,
                sig,
                e.strerror,
            )
        else:
            logging.warning(
                "Failure %s while killing process %s with signal %s: %s",
                e.errno,
                pid,
                sig,
                e.strerror,
            )


def try_set_signal_handler(signal_name, handler):
    """
    Set signal handler like signal.signal(), but only if signal name exists on this
    platform. Signal name must be a string starting with "SIG".
    """
    sig = getattr(_signal, signal_name, None)
    if sig:
        _signal.signal(sig, handler)


def dummy_fn(*args, **kwargs):
    """Dummy function that accepts all parameters but does nothing."""
    pass


def add_files_to_git_repository(base_dir, files, description):
    """
    Add and commit all files given in a list into a git repository in the
    base_dir directory. Nothing is done if the git repository has
    local changes.

    @param files: the files to commit
    @param description: the commit message
    """
    if not os.path.isdir(base_dir):
        printOut("Output path is not a directory, cannot add files to git repository.")
        return

    # find out root directory of repository
    gitRoot = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=base_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    if gitRoot.returncode != 0:
        printOut(
            "Cannot commit results to repository: git rev-parse failed, perhaps output path is not a git directory?"
        )
        return
    gitRootDir = gitRoot.stdout.splitlines()[0]

    # check whether repository is clean
    gitStatus = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=gitRootDir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    if gitStatus.returncode != 0:
        printOut("Git status failed! Output was:\n" + gitStatus.stderr)
        return

    if gitStatus.stdout:
        printOut("Git repository has local changes, not commiting results.")
        return

    # add files to staging area
    files = [os.path.realpath(file) for file in files]
    # Use --force to add all files in result-files directory even if .gitignore excludes them
    gitAdd = subprocess.run(["git", "add", "--force", "--"] + files, cwd=gitRootDir)
    if gitAdd.returncode != 0:
        printOut("Git add failed, will not commit results!")
        return

    # commit files
    printOut("Committing results files to git repository in " + gitRootDir)
    gitCommit = subprocess.run(
        ["git", "commit", "--file=-", "--quiet"],
        input=description,
        cwd=gitRootDir,
        universal_newlines=True,
    )
    if gitCommit.returncode != 0:
        printOut("Git commit failed!")
        return


def wildcard_match(word, wildcard):
    return word and fnmatch.fnmatch(word, wildcard)


def read_local_time():
    """Get "aware" datetime.datetime instance with local time (including time zone)."""
    return datetime.datetime.now().astimezone()


def should_color_output():
    """Determine whether we want colored output to stdout."""
    # cf. https://no-color.org/
    return sys.stdout.isatty() and "NO_COLOR" not in os.environ


def setup_logging(fmt="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO):
    """Setup the logging framework with a basic configuration"""
    if should_color_output():
        try:
            import coloredlogs

            coloredlogs.install(fmt=fmt, level=level)
            return
        except ImportError:
            pass

    logging.basicConfig(format=fmt, level=level)


def _debug_current_process(sig, current_frame):
    """Interrupt running process, and provide a python prompt for interactive debugging.
    This code is based on http://stackoverflow.com/a/133384/396730
    """
    # Import modules only if necessary, readline is for shell history support.
    import code, traceback, readline, threading  # noqa: E401, F401 @UnresolvedImport @UnusedImport

    d = {"_frame": current_frame}  # Allow access to frame object.
    d.update(current_frame.f_globals)  # Unless shadowed by global
    d.update(current_frame.f_locals)

    i = code.InteractiveConsole(d)
    message = "Signal received : entering python shell.\n"

    threads = {thread.ident: thread for thread in threading.enumerate()}
    current_thread = threading.current_thread()
    for thread_id, frame in sys._current_frames().items():
        if current_thread.ident != thread_id:
            message += f"\nTraceback of thread {threads[thread_id]}:\n"
            message += "".join(traceback.format_stack(frame))
    message += f"\nTraceback of current thread {current_thread}:\n"
    message += "".join(traceback.format_stack(current_frame))
    i.interact(message)


def activate_debug_shell_on_signal():
    """Install a signal handler for USR1 that dumps stack traces
    and gives an interactive debugging shell. Does nothing on Windows.
    """
    try_set_signal_handler("SIGUSR1", _debug_current_process)


def get_capability(filename):
    """
    Get names of capabilities and the corresponding capability set for given filename.

        @filename: The complete path to the file
    """
    res = {"capabilities": [], "set": [], "error": False}
    try:
        libcap_path = find_library("cap")
        libcap = ctypes.cdll.LoadLibrary(libcap_path)
    except OSError:
        res["error"] = True
        logging.warning("Unable to find capabilities for %s", filename)
        return res
    cap_t = libcap.cap_get_file(ctypes.create_string_buffer(filename.encode()))
    libcap.cap_to_text.restype = ctypes.c_char_p
    cap_object = libcap.cap_to_text(cap_t, None)
    libcap.cap_free(cap_t)
    if cap_object is not None:
        cap_string = cap_object.decode()
        res["capabilities"] = (cap_string.split("+")[0])[2:].split(",")
        res["set"] = list(cap_string.split("+")[1])
    return res


def check_msr():
    """
    Checks if the msr driver is loaded and if the user executing
    benchexec has the read and write permissions for msr.
    """
    res = {"loaded": False, "write": False, "read": False}
    loaded_modules = subprocess.check_output(
        ["lsmod"], universal_newlines=True
    ).splitlines()

    if any("msr" in module for module in loaded_modules):
        res["loaded"] = True
    if res["loaded"]:
        cpu_dirs = os.listdir("/dev/cpu")
        cpu_dirs.remove("microcode")
        if all(os.access(f"/dev/cpu/{cpu}/msr", os.R_OK) for cpu in cpu_dirs):
            res["read"] = True
        if all(os.access(f"/dev/cpu/{cpu}/msr", os.W_OK) for cpu in cpu_dirs):
            res["write"] = True
    return res


def is_child_process_of_us(pid: int) -> bool:
    """
    Return if the given PID is a (transitive) child process of the current process.
    Also returns true if the given PID is ours.
    """
    if pid == os.getpid():
        return True

    ppid = None
    try:
        with open(f"/proc/{pid}/status") as status_file:
            for line in status_file:
                if line.startswith("PPid:"):
                    ppid = int(line.split(":", maxsplit=1)[1].strip())
                    break
    except FileNotFoundError:
        pass  # Process terminated in the meantime.

    if ppid:
        return is_child_process_of_us(ppid)
    else:
        return False
