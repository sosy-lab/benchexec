# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

# The following code is intended for use in pytest sessions and ensures consistent rounding behavior during tests.
# It sets the rounding mode to ROUND_HALF_UP for both the DefaultContext and the local context at the start of the session.
# This helps maintain reproducibility in test results by avoiding discrepancies in rounding behavior across different environments or configurations.
# The use of pytest_sessionstart hook from `conftest.py` ensures that this setup is applied globally at the beginning of each test session.

import decimal

original_default_rounding = decimal.DefaultContext.rounding
original_local_rounding = decimal.getcontext().rounding


def pytest_sessionstart(session):
    decimal.DefaultContext.rounding = decimal.ROUND_HALF_UP
    decimal.getcontext().rounding = decimal.ROUND_HALF_UP
