# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import decimal

# Store the original rounding values
original_default_rounding = decimal.DefaultContext.rounding
original_local_rounding = decimal.getcontext().rounding


def pytest_sessionstart(session):
    # Set both DefaultContext and local context rounding to ROUND_HALF_UP at the beginning of the test session
    decimal.DefaultContext.rounding = decimal.ROUND_HALF_UP
    decimal.getcontext().rounding = decimal.ROUND_HALF_UP
