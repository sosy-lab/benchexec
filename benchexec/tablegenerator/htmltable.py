# BenchExec is a framework for reliable benchmarking.
# This file is part of BenchExec.
#
# Copyright (C) 2007-2019  Dirk Beyer
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import os

from benchexec import __version__
from benchexec.tablegenerator import util

_REACT_FILES = [
    os.path.join(os.path.dirname(__file__), "react-table", "build", path)
    for path in ["vendors.min.", "bundle.min."]
]


def write_html_table(
    out,
    options,
    title,
    head,
    run_sets,
    rows,
    stats,
    relevant_id_columns,
    output_path,
    **kwargs,
):
    app_css = [util.read_bundled_file(path + "css") for path in _REACT_FILES]
    app_js = [util.read_bundled_file(path + "js") for path in _REACT_FILES]
    columns = [run_set.columns for run_set in run_sets]
    stats = util.prepare_stats_for_js(stats, columns)
    tools = util.prepare_run_sets_for_js(run_sets)
    href_base = os.path.dirname(options.xmltablefile) if options.xmltablefile else None
    rows_js = util.prepare_rows_for_js(
        rows, output_path, href_base, relevant_id_columns
    )

    def write_tags(tag_name, contents):
        for content in contents:
            out.write("<")
            out.write(tag_name)
            out.write(">\n")
            out.write(content)
            out.write("\n</")
            out.write(tag_name)
            out.write(">\n")

    def write_json_part(name, value=None, last=False):
        out.write('  "')
        out.write(name)
        out.write('": ')
        out.write(json.dumps(value, sort_keys=True))
        if not last:
            out.write(",")
        out.write("\n")

    out.write(
        """<!DOCTYPE html>
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<meta name="generator" content="BenchExec table-generator {version}">
<title>{title} &ndash; BenchExec results</title>

""".format(
            title=title, version=__version__
        )
    )
    write_tags("style", app_css)
    out.write(
        """</head>
<body>

<div id="root"></div>
<noscript>
  This is an interactive table for viewing results produced by
  <a href="https://github.com/sosy-lab/benchexec" target="_blank" rel="noopener noreferrer">BenchExec</a>.
  Please enable JavaScript to use it.
</noscript>

<script>
const data = {
"""
    )
    write_json_part("version", __version__)
    write_json_part("head", head)
    write_json_part("tools", tools)
    write_json_part("rows", rows_js)
    write_json_part("stats", stats, last=True)
    out.write(
        """};
window.data = data;
</script>

"""
    )
    write_tags("script", app_js)
    out.write("</body>\n</html>\n")
