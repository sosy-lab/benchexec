# Gnuplot definition for a scatter plot

# set axis labels
set xlabel 'Configuration 1'
set ylabel 'Configuration 2' offset 2

# set value range
set xrange [1:100]
set yrange [1:100]

# use logscale
set logscale

set nokey
set size square

set output "scatter.pdf"
set terminal pdf size 10cm,10cm

# plot with 3 diagonal lines and data points from columns 4 and 8 in table
plot \
     x*10 linecolor rgb "dark-gray", \
     x/10 linecolor rgb "dark-gray", \
     x linecolor rgb "dark-gray", \
     "scatter.table.csv" using 3:7 with points pointtype 1
