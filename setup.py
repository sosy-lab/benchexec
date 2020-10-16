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

# This file is still required for compatibility with pip<19.0
# and for "pip install -e .".

setuptools.setup()
