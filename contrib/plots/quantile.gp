# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

# Gnuplot definition for a quantile plot

# set axis labels
set xlabel 'n-th fastest correct result'
set ylabel "CPU time (s)" offset 2

# set value range
set xrange [0:1200]
set yrange [0.1:1000]

# use logscale
set logscale y 10

# legend (choose one of two positions)
set key left top Left reverse
#set key bottom right

set output "quantile.gp.pdf"
set terminal pdf

set style data linespoints

# plot with data points from prepared CSV files (more lines can be added here)
plot \
     "example-tool1.quantile.csv" using 1:5 title "Tool 1" with linespoints pointinterval -500, \
     "example-tool2.quantile.csv" using 1:5 title "Tool 2" with linespoints pointinterval -500
