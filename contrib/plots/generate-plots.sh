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

# Generate quantile plots of CPU times
for i in *.results.xml ; do
	./quantile-generator.py --correct-only $i > ${i%.xml}.quantile.csv
done
gnuplot quantile.gp
gnuplot quantile-split.gp

# Generate score-based quantile plot of CPU times
for i in *.results.xml ; do
	./quantile-generator.py --score-based $i > ${i%.xml}.quantile-score.csv
done
gnuplot quantile-score.gp
