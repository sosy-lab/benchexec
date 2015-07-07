#!/bin/sh

# Generate a scatter plot of CPU times
table-generator --correct-only -x scatter.xml
gnuplot scatter.gp

# Generate a scatter plot where color indicates frequency of data points
cut -f 3,7 < scatter.table.csv \
	| sort -n \
	| uniq -c \
	> scatter.counted.csv
gnuplot scatter-counted.gp

# Generate quantile plots of CPU times by creating sorted CSV files
for i in *.results.xml ; do
	table-generator --correct-only $i
	# Extract CPU time, prune irrelevant lines, and sort
	cut -f 3 < ${i%.xml}.csv \
		| sed -e '/^.[a-zA-Z]/ d' -e '/^$/ d' \
		| sort -g \
		> ${i%.xml}.quantile.csv
done
gnuplot quantile.gp
gnuplot quantile-split.gp
