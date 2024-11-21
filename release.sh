#!/bin/bash

# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

set -e

if [ -z "$1" ]; then
  echo "Please specify to-be-released version as parameter."
  exit 1
fi

OLD_VERSION="$(grep __version__ benchexec/__init__.py | sed -e 's/^.*"\(.*\)".*$/\1/')"
VERSION="$1"
if [ $(expr match "$VERSION" ".*dev") -gt 0 ]; then
  echo "Cannot release development version."
  exit 1
fi
if [ "$VERSION" = "$OLD_VERSION" ]; then
  echo "Version already exists."
  exit 1
fi
if ! grep -q "^#* *BenchExec $VERSION" CHANGELOG.md; then
  echo "Cannot release version without changelog, please update CHANGELOG.md"
  exit 1
fi
if [ ! -z "$(git status -uno -s)" ]; then
  echo "Cannot release with local changes, please stash them."
  exit 1
fi

git remote update origin
if [ ! -z "$(git rev-list HEAD..origin/main)" ]; then
  echo "Local branch is not up-to-date, please rebase."
  exit 1
fi

if [ -z "$DEBFULLNAME" ]; then
  echo "Please define environment variable DEBFULLNAME with your name you want to use for the Debian package."
  exit 1
fi
if [ -z "$DEBEMAIL" ]; then
  echo "Please define environment variable DEBEMAIL with your name you want to use for the Debian package."
  exit 1
fi
if [ -z "$DEBKEY" ]; then
  echo "Please define environment variable DEBKEY with your key ID you want to use for signing the Debian package."
  exit 1
fi
if ! which twine > /dev/null; then
  echo 'Please install twine>=1.11.0, e.g. with "pipx install twine" or "pip3 install --user twine".'
  exit 1
fi

# Prepare files with new version number
sed -e "s/^__version__ = .*/__version__ = \"$VERSION\"/" -i benchexec/__init__.py
dch -v "$VERSION-1" "New upstream version."
dch -r ""

git commit debian/changelog benchexec/__init__.py -m"Release $VERSION"


# Other preparations
DIR="$(pwd)"
DIST_DIR="$DIR/dist-$VERSION"
rm -r "$DIST_DIR" 2>/dev/null || true
mkdir "$DIST_DIR"

# This makes at least wheels reproducible: https://reproducible-builds.org/docs/source-date-epoch/
export SOURCE_DATE_EPOCH="$(dpkg-parsechangelog -STimestamp)"


# Test and build wheel in a fresh directory and environment
TEMP3="$(mktemp -d)"
python3 -m venv "$TEMP3"
. "$TEMP3/bin/activate"
git clone "file://$DIR" "$TEMP3/benchexec"
pushd "$TEMP3/benchexec"
pip install build
pip install -e ".[dev]"
python -m pytest
python -m build
popd
deactivate
cp "$TEMP3/benchexec/dist/"* "$DIST_DIR"
rm -rf "$TEMP3"


# Build Debian package
TAR="BenchExec-$VERSION.tar.gz"

TEMP_DEB="$(mktemp -d)"
cp "$DIST_DIR/$TAR" "$TEMP_DEB"
pushd "$TEMP_DEB"
tar xf "$TAR"
cp -r "$DIR/debian" "$TEMP_DEB/BenchExec-$VERSION"
cd "BenchExec-$VERSION"

dh_make -p "benchexec_$VERSION" --createorig -f "../$TAR" -i -c apache || true

dpkg-buildpackage --build=source -sa "--sign-key=$DEBKEY"
podman run --security-opt unmask=/sys/fs/cgroup --cgroups=split \
  --security-opt unmask=/proc/* --security-opt seccomp=unconfined --device /dev/fuse \
  --rm -w "$(pwd)" -v "$TEMP_DEB:$TEMP_DEB:rw" --rm ubuntu:20.04 \
  "$TEMP_DEB/BenchExec-$VERSION/test/setup_cgroupsv2_in_container.sh" bash -c '
  apt-get update
  apt-get install -y --no-install-recommends dpkg-dev
  TZ=UTC DEBIAN_FRONTEND=noninteractive apt-get install -y $(dpkg-checkbuilddeps 2>&1 | grep -o "Unmet build dependencies:.*" | cut -d: -f2- | sed "s/([^)]*)//g")
  dpkg-buildpackage --build=binary --no-sign
'
popd
cp "$TEMP_DEB/benchexec_$VERSION"{.orig.tar.gz,-1_all.deb,-1.dsc,-1.debian.tar.xz,-1_source.buildinfo,-1_source.changes} "$DIST_DIR"
rm -rf "$TEMP_DEB"

for f in "$DIST_DIR/BenchExec-$VERSION"*.{whl,tar.gz} "$DIST_DIR/benchexec_$VERSION"*.deb; do
  gpg --detach-sign -a -u "$DEBKEY" "$f"
done
git tag -s "$VERSION" -m "Release $VERSION"


# Upload and finish
read -p "Everything finished, do you want to release version '$VERSION' publically? (y/n) " -n 1 -r
echo
if ! [[ $REPLY =~ ^[Yy]$ ]]; then
  exit 0
fi

git push --tags
twine upload "$DIST_DIR/BenchExec"*
dput ppa:sosy-lab/benchmarking "$DIST_DIR/benchexec_$VERSION-1_source.changes"

REPLY=
while [[ $REPLY = "" ]]; do
  read -p "Please enter next version number:  " -r
done
sed -e "s/^__version__ = .*/__version__ = \"$REPLY\"/" -i benchexec/__init__.py
git commit benchexec/__init__.py -m"Prepare version number for next development cycle."


echo
echo "Please create a release on GitHub and add content from CHANGELOG.md and the following files:"
ls -1 "$DIST_DIR/BenchExec-$VERSION"*.{whl,whl.asc,tar.gz,tar.gz.asc} "$DIST_DIR/benchexec_$VERSION"*.{deb,deb.asc}
echo "=> https://github.com/sosy-lab/benchexec/releases/new?tag=$VERSION&title=Release%20$VERSION"
echo "Please also copy the binary PPA packages to all newer supported Ubuntu versions after they have been built by going to https://launchpad.net/%7Esosy-lab/+archive/ubuntu/benchmarking/+copy-packages"
