# Gnuplot definition for a scatter plot where color indicates frequency of data points

# set axis labels
set xlabel 'Configuration 1'
set ylabel 'Configuration 2' offset 2
set cblabel 'Number of results'

# set value range
set xrange [1:100]
set yrange [1:100]
set cbrange[1:100]

# use logscale
set logscale

set nokey
set size square

set palette defined (0 'green', 0.25 'orange', 0.5 'red', 0.75 'dark-red', 1 'black')

set output "scatter-counted.pdf"
set terminal pdf size 11.5cm,10cm

# plot with 3 diagonal lines and data points from columns 4 and 8 in table
plot \
     x*10 linecolor rgb "dark-gray", \
     x/10 linecolor rgb "dark-gray", \
     x linecolor rgb "dark-gray", \
     "scatter.counted.csv" using 2:3:1 with points pointtype 2 palette title "Count"
