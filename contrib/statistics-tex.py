#!/usr/bin/env python3

# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import sys


def main(args=None):
    sys.exit(
        """This script was replaced by direct LaTeX export from table-generator.
Please use "table-generator --format=statistics-tex" and refer to
https://github.com/sosy-lab/benchexec/edit/main/doc/table-generator.md
for more documentation."""
    )


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit("Script was interrupted by user.")
