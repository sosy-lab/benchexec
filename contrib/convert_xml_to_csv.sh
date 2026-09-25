#!/bin/bash

# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2025-2026 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

# This file is meant as an example for how to convert
# a result XML file (.xml.bz2) produced by BenchExec to a simple CSV file.

DELIMITER=$'\t'

XML_FILE="${1:-}"
if [[ "$XML_FILE" == "" ]]; then
  echo "Usage: $0 XML_FILE"
  exit
fi

# Replace file ending by '.table.csv' as table-generator would do.
CSV_FILE=${XML_FILE/.xml.bz2/.xml.table.csv}

# Print the header into the new CSV_FILE (overwrites old file if present).
echo "task	property	expected	status	category	cputime (s)	walltime (s)	memory (B)" \
  > "$CSV_FILE"

# Read relevant data from the XML file and append it to the CSV_FILE.
bzcat "$XML_FILE" \
  | xmlstarlet format --dropdtd \
  | xmlstarlet select --text --template --match "/result/run" \
          --value-of "@name" --output "$DELIMITER" \
          --value-of "@properties" --output "$DELIMITER" \
          --value-of "@expectedVerdict" --output "$DELIMITER" \
          --value-of "column[@title='status']/@value" --output "$DELIMITER" \
          --value-of "column[@title='category']/@value" --output "$DELIMITER" \
          --value-of "column[@title='cputime']/@value" --output "$DELIMITER" \
          --value-of "column[@title='walltime']/@value" --output "$DELIMITER" \
          --value-of "column[@title='memory']/@value" --output "$DELIMITER" \
          --nl >> "$CSV_FILE"

# Print progress dot.
# echo -n "."

