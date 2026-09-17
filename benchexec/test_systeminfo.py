# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2026 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

from decimal import Decimal

from benchexec.systeminfo import _read_cpu_info, _read_memory_info


def test_cpu_info():
    cpu_info = _read_cpu_info()
    for key, _ in cpu_info:
        assert key
        assert key.strip() == key

    cpu_dict = dict(cpu_info)
    assert cpu_dict["processor"]
    assert Decimal(cpu_dict["cpu MHz"])


def test_memory():
    memory_info = _read_memory_info()
    for key, value in memory_info.items():
        assert key
        assert value
        assert key.strip() == key

    assert int(memory_info["MemTotal"].removesuffix(" kB"))
