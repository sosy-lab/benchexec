#!/usr/bin/env python3

# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import os
import sys
import tempfile
import urllib.request
import subprocess

sys.dont_write_bytecode = True  # prevent creation of .pyc files
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vcloud.vcloudbenchmarkbase import VcloudBenchmarkBase  # noqa E402
from vcloud import vcloudutil  # noqa E402
from benchexec import __version__  # noqa E402
import benchexec.benchexec  # noqa E402
import benchexec.tools  # noqa E402

_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "vcloud"))
IVY_JAR_NAME = "ivy-2.5.0.jar"
IVY_PATH = os.path.join(_ROOT_DIR, "lib", IVY_JAR_NAME)
IVY_DOWNLOAD_URL = "https://www.sosy-lab.org/ivy/org.apache.ivy/ivy/" + IVY_JAR_NAME


def download_required_jars(config):
    # download ivy if needed
    if not os.path.isfile(IVY_PATH):
        # let the process exit if an exception occurs.
        urllib.request.urlretrieve(IVY_DOWNLOAD_URL, IVY_PATH)  # noqa S310

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
            shell=vcloudutil.is_windows(),  # noqa: S602
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


class VcloudBenchmark(VcloudBenchmarkBase):
    """
    Benchmark class that defines the load_executor function.
    """

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

        return executor


if __name__ == "__main__":
    benchexec.benchexec.main(VcloudBenchmark())
