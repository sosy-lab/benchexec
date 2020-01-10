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

from benchexec import __version__


def write_html_table(out, template_values):
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
        out.write(json.dumps(value or template_values[name], sort_keys=True))
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
            title=template_values["title"], version=__version__
        )
    )
    write_tags("style", template_values["app_css"])
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
    write_json_part("head")
    write_json_part("tools")
    write_json_part("rows")
    write_json_part("stats", last=True)
    out.write(
        """};
window.data = data;
</script>

"""
    )
    write_tags("script", template_values["app_js"])
    out.write("</body>\n</html>\n")
