# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

# Gnuplot definition for a quantile plot, with linear scale below 1s

# set value range
set xrange [0:1200]

# legend (choose one of two positions)
set key left top Left reverse
#set key bottom right

set output "quantile-split.gp.pdf"
set terminal pdf

set style data lines

# Use two separate plots for y-ranges [0,1] and [1,100]
set multiplot layout 2,1

# configure upper plot and y-axis
set yrange [1:100]
set ylabel "CPU time (s)" offset 2
set logscale y 10

set size 1,0.76
set origin 0,0.24
set bmargin 0
set lmargin 6
unset xtics

# plot with data points from prepared CSV files (more lines can be added here)
plot \
     "example-tool1.quantile.csv" using 1:5 title "Tool 1", \
     "example-tool2.quantile.csv" using 1:5 title "Tool 2"

# configure lower plot and x-axis
set yrange [0:1]
set xlabel 'n-th fastest correct result'

set size 1,0.24
set origin 0,0
set bmargin 3
set tmargin 0
set xtics nomirror
unset key
unset ytics
unset ylabel
unset logscale

# same plot definition as above
plot \
     "example-tool1.quantile.csv" using 1:5 title "Tool 1", \
     "example-tool2.quantile.csv" using 1:5 title "Tool 2"
