#!/usr/bin/env python3

# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import os
import re
import setuptools
import warnings

warnings.filterwarnings("default", module=r"^benchexec\..*")

# Links for documentation on how to build and use Python packages:
# http://python-packaging-user-guide.readthedocs.org/en/latest/
# http://gehrcke.de/2014/02/distributing-a-python-command-line-application/
# http://www.jeffknupp.com/blog/2013/08/16/open-sourcing-a-python-project-the-right-way/
# https://pythonhosted.org/setuptools/setuptools.html
# https://docs.python.org/3/distutils/index.html

# determine version (more robust than importing benchexec)
# c.f. http://gehrcke.de/2014/02/distributing-a-python-command-line-application/
with open("benchexec/__init__.py") as f:
    version = re.search(r'^__version__\s*=\s*"(.*)"', f.read(), re.M).group(1)

# Get the long description from the relevant file
readme = os.path.join(os.path.abspath(os.path.dirname(__file__)), "README.md")
with open(readme, "rb") as f:
    long_description = f.read().decode("utf-8")

setuptools.setup(
    name="BenchExec",
    version=version,
    author="Dirk Beyer",
    description=("A Framework for Reliable Benchmarking and Resource Measurement."),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/sosy-lab/benchexec/",
    license="Apache-2.0 AND BSD-3-Clause AND CC-BY-4.0 AND MIT AND ISC AND LicenseRef-BSD-3-Clause-CMU",
    keywords="benchmarking resource measurement",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "License :: OSI Approved :: BSD License",
        "License :: OSI Approved :: ISC License (ISCL)",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: System :: Benchmark",
    ],
    platforms=["Linux"],
    packages=["benchexec", "benchexec.tablegenerator", "benchexec.tools"],
    package_data={
        "benchexec.tablegenerator": [
            "react-table/build/*.min.js",
            "react-table/build/*.min.css",
        ]
    },
    entry_points={
        "console_scripts": [
            "runexec = benchexec.runexecutor:main",
            "containerexec = benchexec.containerexecutor:main",
            "benchexec = benchexec.benchexec:main",
            "table-generator = benchexec.tablegenerator:main",
        ]
    },
    install_requires=["PyYAML>=3.12"],
    setup_requires=["nose>=1.0", "lxml", "PyYAML>=3.12"],
    test_suite="nose.collector",
    zip_safe=True,
)
