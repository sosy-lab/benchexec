#!/bin/bash

set -e

VERSION="$(grep __version__ benchexec/__init__.py | sed -e "s/^.*'\(.*\)'.*$/\1/")"
if [ $(expr match "$VERSION" ".*dev") -gt 0 ]; then
  echo "Cannot relase development version, please update benchexec/__init__.py."
  exit 1
fi
if ! grep -q "BenchExec $VERSION" CHANGELOG.md; then
  echo "Cannot relase version without changelog, please update CHANGELOG.md"
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

read -p "Do you want to release version '$VERSION'? (y/n) " -n 1 -r
echo
if ! [[ $REPLY =~ ^[Yy]$ ]]; then
  exit 0
fi

DIR="$(pwd)"
DIST_DIR="$DIR/dist-$VERSION"
rm -r "$DIST_DIR" 2>/dev/null || true
mkdir "$DIST_DIR"

TEMP3="$(mktemp -d)"
virtualenv -p /usr/bin/python3 --system-site-packages "$TEMP3"
. "$TEMP3/bin/activate"
git clone "file://$DIR" "$TEMP3/benchexec"
pushd "$TEMP3/benchexec"
pip install -e "."
python setup.py nosetests
python setup.py sdist bdist_egg bdist_wheel
popd
deactivate
cp "$TEMP3/benchexec/dist/"* "$DIST_DIR"
rm -rf "$TEMP3"

TEMP2="$(mktemp -d)"
virtualenv -p /usr/bin/python2 --system-site-packages "$TEMP2"
. "$TEMP2/bin/activate"
git clone "file://$DIR" "$TEMP2/benchexec"
pushd "$TEMP2/benchexec"
pip install -e "."
python setup.py test
python setup.py bdist_egg
popd
deactivate
cp "$TEMP2/benchexec/dist/"* "$DIST_DIR"
rm -rf "$TEMP2"

TAR="BenchExec-$VERSION.tar.gz"

TEMP_DEB="$(mktemp -d)"
cp "$DIST_DIR/$TAR" "$TEMP_DEB"
pushd "$TEMP_DEB"
tar xf "$TAR"
cp -r "$DIR/debian" "$TEMP_DEB/BenchExec-$VERSION"
cd "BenchExec-$VERSION"

dh_make -p "benchexec_$VERSION" --createorig -f "../$TAR" -i -c apache || true

echo
echo "In the following editor, please enter 'New upstream version.' in the empty changelog entry."
echo "Press ENTER to continue."
read
dch -v "$VERSION-1"

EDITOR=/bin/true dch -r --no-force-save-on-release
dpkg-buildpackage -us -uc
popd
cp "$TEMP_DEB/BenchExec-$VERSION/debian/changelog" "debian/changelog"
cp "$TEMP_DEB/benchexec_$VERSION-1_all.deb" "$DIST_DIR"
rm -rf "$TEMP_DEB"

for f in "$DIST_DIR/"*; do
  gpg --detach-sign -a "$f"
done
git tag -s "$VERSION" -m "Relase $VERSION"
git push --tags
twine upload "$DIST_DIR/BenchExec"*

echo
echo "Please create a release on GitHub and add content from CHANGELOG.md and files from $DIST_DIR/:"
echo "https://github.com/sosy-lab/benchexec/releases"
echo
echo "Please increment version in benchexec/__init__.py to next development version."
echo
echo "Please commit the changed file debian/changelog."
