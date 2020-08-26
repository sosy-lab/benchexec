# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0


class FileWriter(object):
    """
    The class FileWriter is a wrapper for writing content into a file.
    """

    def __init__(self, filename, content):
        """
        The constructor of FileWriter creates the file.
        If the file exist, it will be OVERWRITTEN without a message!
        """

        self._file = open(filename, "w")
        self._pos = None
        self.append(content)

    def append(self, newContent, keep=True):
        """
        Add content to the represented file.
        If keep is False, the new content will be removed again during the next call
        to this method where keep=True.
        """
        assert self._file
        if keep:
            self._truncate()
        elif self._pos is None:
            self._pos = self._file.tell()  # keep marker for where we need to truncate

        self._file.write(newContent)
        self._file.flush()

    def _truncate(self):
        """Remove any temporary content that was added with append(keep=False)"""
        if self._pos is not None:
            self._file.seek(self._pos)
            self._file.truncate()
            self._pos = None

    def close(self):
        """Close file and prevent any further additions"""
        if self._file:
            self._truncate()
            self._file.close()
            self._file = None
