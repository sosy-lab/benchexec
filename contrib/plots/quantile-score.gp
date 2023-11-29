# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

# Gnuplot definition for a score-based quantile plot

# set axis labels
set xlabel 'Accumulated score'
set ylabel "CPU time (s)" offset 2

# set value range
set xrange [-200:2000]
set yrange [0.1:1000]

# use logscale
set logscale y 10

# legend (choose one of two positions)
set key left top Left reverse
#set key bottom right

set output "quantile-score.gp.pdf"
set terminal pdf

set style data linespoints

# plot with data points from prepared CSV files (more lines can be added here)
plot \
     "example-tool1.quantile-score.csv" using 1:5 title "Tool 1" with linespoints pointinterval -500, \
     "example-tool2.quantile-score.csv" using 1:5 title "Tool 2" with linespoints pointinterval -500
