#!/bin/sh

# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

# Generate CSV for a scatter plot of CPU times.
table-generator --correct-only -f csv -x scatter.xml

# Generate CSV for a scatter plot where color indicates frequency of data points
# (not useful with the example data in this directory).
cut -f 3,7 < scatter.table.csv \
	| sort -n \
	| uniq -c \
	> scatter.counted.csv

# Generate CSV for a quantile plot of CPU times.
for i in *.results.xml.bz2 ; do
	./quantile-generator.py --correct-only $i > ${i%.results.xml.bz2}.quantile.csv
done

# Generate CSV for a score-based quantile plot of CPU times.
for i in *.results.xml.bz2 ; do
	./quantile-generator.py --score-based $i > ${i%.results.xml.bz2}.quantile-score.csv
done


# Commands for generating plots with Gnuplot:
gnuplot scatter.gp
gnuplot scatter-counted.gp
gnuplot quantile.gp
gnuplot quantile-split.gp
gnuplot quantile-score.gp

# Commands for generating plots with LaTeX (not necessary if included in other LaTeX file):
pdflatex scatter.tex
pdflatex scatter-counted.tex
pdflatex quantile.tex
pdflatex quantile-score.tex

# Special command for generating plots as PNG files (just for recreating the demo files)
# for f in *.tex; do
#   pdflatex -shell-escape "\PassOptionsToClass{convert}{standalone}\input{$f}"
# done
