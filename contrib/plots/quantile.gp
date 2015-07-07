# Gnuplot definition for a quantile plot

# set axis labels
set xlabel 'n-th fastest correct result'
set ylabel "CPU time (s)" offset 2

# set value range
set xrange [0:500]
set yrange [1:100]

# use logscale
set logscale y 10

# legend (choose one of two positions)
set key left top Left reverse
#set key bottom right

set output "quantile.pdf"
set terminal pdf

set style data linespoints

# plot with data points from prepared CSV files (more lines can be added here)
plot \
     "config1.results.quantile.csv" using 1:4 title "Configuration 1" with linespoints pointinterval -50, \
     "config2.results.quantile.csv" using 1:4 title "Configuration 2" with linespoints pointinterval -50
