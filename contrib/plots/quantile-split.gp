# Gnuplot definition for a quantile plot, with linear scale below 1s

# set value range
set xrange [0:500]

# legend (choose one of two positions)
set key left top Left reverse
#set key bottom right

set output "quantile-split.pdf"
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
     "config1.results.quantile.csv" using 1:4 title "Configuration 1", \
     "config2.results.quantile.csv" using 1:4 title "Configuration 2"

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
     "config1.results.quantile.csv" using 1:4 title "Configuration 1", \
     "config2.results.quantile.csv" using 1:4 title "Configuration 2"
