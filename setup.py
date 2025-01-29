#!/usr/bin/env python3

# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import setuptools
import warnings

warnings.filterwarnings("default", module=r"^benchexec\..*")

# This file is required for compatibility with
# - pip<19.0 (older than our minium Python version, so irrelevant)
# - editable mode (pip install -e .) with pip<21.3 (not important)
# - building Debian packages without build dependency pybuild-plugin-pyproject
# As the last one is not available on Ubuntu 20.04, we need to keep setup.py
# for now, but should consider updating the Debian package build and removing setup.py
# once we drop support for Ubuntu 20.04.

setuptools.setup()
