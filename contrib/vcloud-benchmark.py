#!/usr/bin/env python3

# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import os
import subprocess
import sys
import tempfile
import urllib.request

from vcloud import vcloudutil
from vcloud.vcloudbenchmarkbase import VcloudBenchmarkBase

sys.dont_write_bytecode = True  # prevent creation of .pyc files
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import benchexec.benchexec  # noqa: E402
import benchexec.model  # noqa: E402
import benchexec.tools  # noqa: E402
from benchexec import BenchExecException, __version__  # noqa: E402

_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "vcloud"))
IVY_JAR_NAME = "ivy-2.5.0.jar"
IVY_PATH = os.path.join(_ROOT_DIR, "lib", IVY_JAR_NAME)
IVY_DOWNLOAD_URL = "https://www.sosy-lab.org/ivy/org.apache.ivy/ivy/" + IVY_JAR_NAME


def download_required_jars(config):
    # download ivy if needed
    if not os.path.isfile(IVY_PATH):
        # let the process exit if an exception occurs.
        urllib.request.urlretrieve(IVY_DOWNLOAD_URL, IVY_PATH)

    # prepare command
    cmd = ["java", "-jar", "lib/" + IVY_JAR_NAME]
    cmd += ["-settings", "lib/ivysettings.xml"]
    cmd += ["-dependency", "org.sosy_lab", "vcloud", "0.+"]
    cmd += ["-confs", "runtime", "-mode", "dynamic", "-refresh"]
    if not config.debug:
        # In normal mode, -warn is good (no output by default, only if sth. is wrong).
        # In debug mode, the default Ivy output seems fine (-verbose and -debug would
        # be too verbose).
        cmd += ["-warn"]
    cmd += ["-retrieve", "lib/vcloud-jars/[artifact](-[classifier]).[ext]"]
    cmd += ["-overwriteMode", "different"]

    # Provide temporary directory
    temp_dir = None
    if config.noIvyCache:
        temp_dir = tempfile.TemporaryDirectory(prefix="vcloud-ivy-cache-")
        cmd += ["-cache", temp_dir.name]
    try:
        # install vcloud jar and dependencies
        return_code = subprocess.run(
            cmd,
            cwd=_ROOT_DIR,
            shell=vcloudutil.is_windows(),
        ).returncode
        if return_code != 0:
            sys.exit(
                "Retrieving the VerifierCloud client with Ivy failed. "
                "Please have a look at the Ivy output above. "
                "Note that Internet access may be necessary."
            )
    finally:
        if temp_dir:
            temp_dir.cleanup()


def load_tool_info_in_container(tool_name, config):
    """
    Load the tool-info class inside a Podman container.
    @param tool_name: The name of the tool-info module.
    Either a full Python package name or a name within the benchexec.tools package.
    @return: A tuple of the full name of the used tool-info module and an instance of the tool-info class.
    """
    tool_module = tool_name if "." in tool_name else f"benchexec.tools.{tool_name}"

    try:
        from vcloud.podman_containerized_tool import PodmanContainerizedTool

        tool = PodmanContainerizedTool(tool_module, config, config.containerImage)

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
    return tool_module, tool


class VcloudBenchmark(VcloudBenchmarkBase):
    """
    An extension of BenchExec
    that executes the benchmarks in the VerifierCloud.
    """

    def add_vcloud_args(self, vcloud_args):
        vcloud_args.add_argument(
            "--no-ivy-cache",
            dest="noIvyCache",
            action="store_true",
            help="Prevents ivy from caching the downloaded jar files. This prevents clashes due to concurrent access to the cache.",
        )
        # add arguments from the base class.
        super().add_vcloud_args(vcloud_args)

    def get_param_name(self, pname):
        return "--v" + pname

    def load_executor(self):
        download_required_jars(self.config)

        import vcloud.benchmarkclient_executor as executor

        executor.set_vcloud_jar_path(
            os.path.join(_ROOT_DIR, "lib", "vcloud-jars", "vcloud.jar")
        )

        logging.debug(
            "This is vcloud-benchmark.py (based on benchexec %s) "
            "using the VerifierCloud internal API.",
            __version__,
        )

        if self.config.containerImage:
            if not self.config.tool_directory:
                raise BenchExecException(
                    "Using a container image is currently only supported "
                    "if the tool directory is explicitly provided. Please set it "
                    "using the --tool-directory option."
                )

            # Monkey-patch BenchExec to load tool-info module in Podman container.
            benchexec.model.load_tool_info = load_tool_info_in_container

        return executor


if __name__ == "__main__":
    benchexec.benchexec.main(VcloudBenchmark())
