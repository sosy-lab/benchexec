# BenchExec Contrib
## Generating Plots from BenchExec Data
This directory contains helper files for producing plots
from data produced with BenchExec.

### Plot Types
There are helper files for two different types of plots here:
quantile plots (also known as cactus plots) and scatter plots.
Quantile plots allow an arbitrary amount of data columns to be compared,
and sort each of the columns individually by its value.
Scatter plots allow only two columns to be compared,
but show the relation between the two values for each individual data point.
An alternative to regular quantile plots are score-based quantile plots,
where the x-axis does not show the number of results,
but the accumulated score achieved with these results.
Such plots are for example used by the
[International Competition on Software Verification](http://sv-comp.sosy-lab.org/2015/results/).

In general, when plotting resource usage it is recommended to show only
data points for correct results, and omit data points for wrong results and crashes.
Otherwise, a wrong answer or crash after for example 10s would look "better"
in the plot than a correct answer after 100s.
This can be done by generating appropriate CSV files with the parameter `--correct-only`
for `table-generator`.
Note that for scatter plots this means that only data points are shown for tasks
for which both runs gave a correct answer. 

### Plots with Gnuplot
The files `*.gp` contain plot definitions for [Gnuplot](http://www.gnuplot.info).
The file [quantile.gp](quantile.gp) defines a quantile plot,
[quantile-score.gp](quantile-score.gp) defines a score-based quantile plot,
and [quantile-split.gp](quantile-split.gp) defines a quantile plot
with a linear scale for the y-range [0,1] and a logarithmic scale beyond.
The file [scatter.gp](scatter.gp) defines a scatter plot,
and [scatter-counted.gp](scatter-counted.gp) defines a scatter plot
where the color of each data point indicates the number of its occurrences
(best for discrete data).

For using these Gnuplot files, appropriate CSV files need to be generated,
which can be done with `table-generator` for scatter plots
and with the script `quantile-generator` in this directory for quantile plots.
The script [generate-plots.sh](generate-plots.sh) shows the necessary commands.
For scatter plots, an XML file with a table definition needs to be written
that contains the two data columns that should be shown in the plot,
as in [scatter.xml](scatter.xml).  