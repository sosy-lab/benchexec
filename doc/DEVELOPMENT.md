# BenchExec: Development Reference

This file contains documentation that is only relevant for developers
and maintainers of BenchExec.

For writing a tool-info module, please refer to the documentation on
[Tool Integration](tool-integration.md).


## Installation for Development

After cloning the [GitHub repository](https://github.com/sosy-lab/benchexec),
BenchExec can be used directly from within the working directory.
Scripts for starting the three programs are available in the `bin` directory.
For `table-generator`, the [Python package Tempita](https://pypi.python.org/pypi/Tempita)
needs to be installed on the system.

The alternative (recommended) way is to create a virtual Python environment
and to install BenchExec in development mode within this environment:

    virtualenv -p /usr/bin/python3 path/to/venv
    source path/to/venv/bin/activate
    pip install -e path/to/benchexec/working/directory

This will automatically install all dependencies
and place appropriate start scripts on the PATH.

Some tests of BenchExec require the `lxml` Python module.
To install this, the system packages `libxml2-dev` and `libxslt1-dev` need to be installed.
Alternatively, if you have the package `python3-lxml` installed on your system,
you can skip building the `lxml` module inside the virtual environment
by passing the parameter `--system-site-packages` to `virtualenv`.


## Releasing a new Version

 * Make sure to install `pandoc`, otherwise the documentation cannot be
   converted to the correct format that PyPI needs.
   You also need `twine`.

 * Define next version number, e.g., from `1.1-dev` to `1.1`.
   Add an according entry to `CHANGELOG.md` and commit.

 * Check whether any of the DTD files in `doc/` changed since last release.
   If yes, push a copy of the changed DTD with the new version to
   `http://www.sosy-lab.org/benchexec/{benchmark,result,table}-<VERSION>.dtd`,
   and update the version number in all references to this DTD in BenchExec.

 * The remaining steps can also be automated with the script
   [release.sh](https://github.com/sosy-lab/benchexec/blob/master/release.sh).

 * Update version number in field `__version__` of `benchexec/__init__.py`,
   e.g., from `1.1-dev` to `1.1` and commit.

 * Create a Git tag:

        git tag -s <VERSION>

 * In a clean checkout and in a virtual environment with Python 3 (as described above),
   create the release archives:

        python3 setup.py sdist bdist_egg bdist_wheel

 * In a clean checkout and in a virtual environment with Python **2**,
   create the release archive with only runexec for Python 2:

        python2 setup.py bdist_egg

 * Copy the `dist/*.egg` file created with Python 2 into the `dist` directory
   of the Python 3 build.

 * Sign the files and upload them to PyPi inside the Python 3 build directory:

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

 * Build the package:

        dpkg-buildpackage -us -uc

 * Sign the package with GPG and upload it to GitHub as part of the release.

 * Copy the file `debian/changelog` back into the repository and it commit it there,
   to keep track of it.
