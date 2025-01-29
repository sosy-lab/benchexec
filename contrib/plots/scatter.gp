# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

# Gnuplot definition for a scatter plot

# set axis labels
set xlabel 'CPU Time for Tool 1 (s)'
set ylabel 'CPU Time for Tool 2 (s)' offset 2

# set value range
set xrange [0.1:1000]
set yrange [0.1:1000]

# use logscale
set logscale

set nokey
set size square

set output "scatter.gp.pdf"
set terminal pdf size 10cm,10cm

# plot with 3 diagonal lines and data points from columns 4 and 8 in table
plot \
     x*10 linecolor rgb "dark-gray", \
     x/10 linecolor rgb "dark-gray", \
     x linecolor rgb "dark-gray", \
     "scatter.table.csv" using 4:8 with points pointtype 1
