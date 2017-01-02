#!/usr/bin/env python3
'''
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.

Copyright (C) 2007-2015  Dirk Beyer
All rights reserved.

Licensed under the Apache License, Version 2.0 (the 'License');
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an 'AS IS' BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''

import os
import re
import setuptools
import sys
import warnings
warnings.filterwarnings('default', module="^benchexec\..*")

# Links for documentation on how to build and use Python packages:
# http://python-packaging-user-guide.readthedocs.org/en/latest/
# http://gehrcke.de/2014/02/distributing-a-python-command-line-application/
# http://www.jeffknupp.com/blog/2013/08/16/open-sourcing-a-python-project-the-right-way/
# https://pythonhosted.org/setuptools/setuptools.html
# https://docs.python.org/3/distutils/index.html

# determine version (more robust than importing benchexec)
# c.f. http://gehrcke.de/2014/02/distributing-a-python-command-line-application/
with open('benchexec/__init__.py') as f:
    version = re.search('^__version__\s*=\s*\'(.*)\'', f.read(), re.M).group(1)

# Get the long description from the relevant file
readme = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'README.md')
try:
    import pypandoc
    long_description = pypandoc.convert(readme, 'rst', format='markdown_github-hard_line_breaks')
except (IOError, ImportError):
    with open(readme, 'rb') as f:
        long_description = f.read().decode('utf-8')

PY2 = sys.version_info[0] == 2

setuptools.setup(
    name = 'BenchExec',
    version = version,
    author = 'Dirk Beyer',
    description = ('A Framework for Reliable Benchmarking and Resource Measurement.'),
    long_description = long_description,
    url = 'https://github.com/sosy-lab/benchexec/',
    license = 'Apache 2.0 License',
    keywords = 'benchmarking resource measurement',
    classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: System :: Benchmark',
        ],
    platforms = ['Linux'],

    packages = ['benchexec'] +
        (['benchexec.tablegenerator', 'benchexec.tools'] if not PY2 else []),
    package_data = {'benchexec.tablegenerator': ['template.*']} if not PY2 else {},
    entry_points = {
        "console_scripts": [
            'runexec = benchexec.runexecutor:main',
            'containerexec = benchexec.containerexecutor:main',
            ] + ([
            'benchexec = benchexec.benchexec:main',
            'table-generator = benchexec.tablegenerator:main',
            ] if not PY2 else []),
        },
    install_requires = ['tempita==0.5.2'],
    setup_requires=['nose>=1.0'] + ['lxml'] if not PY2 else [],
    test_suite = 'nose.collector' if not PY2 else 'benchexec.test_python2.Python2Tests',
    zip_safe = True,
)
