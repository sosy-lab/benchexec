<!--
This file is part of BenchExec, a framework for reliable benchmarking:
https://github.com/sosy-lab/benchexec

SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>

SPDX-License-Identifier: Apache-2.0
-->

# BenchExec: Development Reference

This file contains documentation that is only relevant for developers
and maintainers of BenchExec.

For writing a tool-info module, please refer to the documentation on
[Tool Integration](tool-integration.md).

Development documentation of our React-based project for interactive HTML tables
is in the respective [README](../benchexec/tablegenerator/react-table/README.md).


## Installation for Development

After cloning the [GitHub repository](https://github.com/sosy-lab/benchexec),
BenchExec can be used directly from within the working directory.
Scripts for starting the three programs are available in the `bin` directory.

The alternative (recommended) way is to create a virtual Python environment
and to install BenchExec in development mode within this environment:

    virtualenv -p /usr/bin/python3 path/to/venv
    source path/to/venv/bin/activate
    pip install -e "path/to/benchexec/working/directory[dev]"

This will automatically install all required and `dev` dependencies
and place appropriate start scripts on the PATH.

Some tests of BenchExec require the `lxml` Python module.
To install this, the system packages `libxml2-dev` and `libxslt1-dev` need to be installed.
Alternatively, if you have the package `python3-lxml` installed on your system,
you can skip building the `lxml` module inside the virtual environment
by passing the parameter `--system-site-packages` to `virtualenv`.


## Code Style

We use the automatic code formatter [black](https://github.com/python/black).
Installation is possible for example with `pip3 install black`.
Please format all code using `black .`.

Apart from what is formatted automatically,
we try to follow the official Python style guide [PEP8](https://www.python.org/dev/peps/pep-0008/).


## Tests and CI

To run the test suite of BenchExec, use the following command:

    python3 -m pytest

Specific tests can be selected with `-k TEST_NAME_SUBSTRING`
and debug logs can be captured with `--log-level DEBUG`.

A container with the necessary environment and permissions
for executing the tests can be started with:

    podman run --rm -it \
      --security-opt unmask=/sys/fs/cgroup --cgroups=split \
      --security-opt unmask=/proc/*  --security-opt seccomp=unconfined \
      -v /var/lib/lxcfs:/var/lib/lxcfs:ro --device /dev/fuse \
      -v $(pwd):$(pwd):rw -w $(pwd) \
      registry.gitlab.com/sosy-lab/software/benchexec/test:python-3.12 \
      test/setup_cgroupsv2_in_container.sh bash

We also check our code using the static-analysis tools
[flake8](http://flake8.pycqa.org) and [ruff](https://github.com/astral-sh/ruff/).
If you find a rule that should not be enforced in your opinion,
please raise an issue.

As main CI we use GitLab, which runs all tests and checks,
but only on branches from our repository (not on PRs from forks).
GitHub Actions and AppVeyor also run a subset of checks
(mostly for the JavaScript part of BenchExec) on all PRs.


## Releasing a new Version

 * You need `pip>=10.0` and `twine>=1.11.0` to be installed.

 * Define next version number, e.g., from `1.1-dev` to `1.1`.
   Add an according entry to `CHANGELOG.md` and commit.

 * Check whether any of the DTD files in `doc/` changed since last release.
   If yes, push a copy of the changed DTD with the new version to
   `https://www.sosy-lab.org/benchexec/{benchmark,result,table}-<VERSION>.dtd`,
   and update the version number in all references to this DTD in BenchExec.

 * The remaining steps can also be mostly automated with the script
   [release.sh](https://github.com/sosy-lab/benchexec/blob/main/release.sh)
   (make sure to follow the instructions printed at the end).

 * Update version number in field `__version__` of `benchexec/__init__.py`,
   e.g., from `1.1-dev` to `1.1` and commit.

 * Create a Git tag:

        git tag -s <VERSION>

 * In a clean checkout and in a virtual environment with Python 3 (as described above),
   exececute the following commands to build the source distribution (`sdist`) and
   `wheel` file:

        python3 -m pip install build
        python3 -m build

 * Sign the files and upload them to PyPi inside the build directory:

        twine upload -s dist/*

 * Push commits and tag to GitHub:

        git push --tags

 * On GitHub, create a release from the tag with a description of the changes
   (from `CHANGELOG.md`), and upload all files from `dist/`.

 * Update version number in field `__version__` of `benchexec/__init__.py`,
   e.g., from `1.1` to `1.2-dev` and commit.


### Create a Debian Package

 * Use the tar archive generated above as base, copy it in a fresh directory,
   extract it there, and change into the extracted directory.

 * Copy the folder `debian` from a repository checkout to the current directory.

 * Define a version for the Debian package: Usually, the BenchExec version
   can be taken as it is, but for beta versions (e.g., `1.1-dev`),
   you need to replace the `-` by a `~`. Otherwise the beta package
   will have a higher version number than the package of the final version.

 * Create a `.orig.tar.xz` as needed for Debian packages
   (`<DEB_VERSION>` needs to be the defined package version,
   and `<TAR_ARCHIVE>` is the archive from which the directory was extracted.):

        dh_make -p benchexec_<DEB_VERSION> --createorig -f ../<TAR_ARCHIVE> -i -c apache

 * Set the version of the Debian package to the defined one by adding
   a changelog entry for the new version
   (Description can usually be `New upstream version.`,
   `UNRELEASED` in the first line should be changed to `unstable`.):

        DEBFULLNAME="<YOUR_NAME>" DEBEMAIL="<YOUR_EMAIL>" dch -v <DEB_VERSION>-1

 * For manually distributed packages:
   * Build the package:

          dpkg-buildpackage --build=binary --no-sign

     Note that this step must not be executed on an Ubuntu 21.10 or newer,
     as that would create zst compressed packages that are not installable on Debian.

   * Sign the package with GPG and upload it to GitHub as part of the release.

 * For our [Ubuntu PPA](https://launchpad.net/~sosy-lab/+archive/ubuntu/benchmarking):
   * Build the package:

          dpkg-buildpackage --build=source -sa

     This needs to find a GPG key that is added to your Launchpad account, you can explicitly specify it with `--sign-key=...`.

   * Upload the package with

          dput ppa:sosy-lab/benchmarking ../benchexec_<DEB_VERSION>-1_source.changes

     Launchpad will build the package and publish it after a few minutes. If there are build errors you get an email.

   * Copy the package from the Ubuntu version for which it was built
     to all newer supported Ubuntu versions
     on [this Launchpad page](https://launchpad.net/%7Esosy-lab/+archive/ubuntu/benchmarking/+copy-packages).
     Copying the binary package is enough.

 * Copy the file `debian/changelog` back into the repository and it commit it there,
   to keep track of it.
