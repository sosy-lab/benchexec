# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import os

from benchexec import util


class FileWriter(object):
    """
    The class FileWriter is a wrapper for writing content into a file.
    """

    def __init__(self, filename, content):
        """
        The constructor of FileWriter creates the file.
        If the file exist, it will be OVERWRITTEN without a message!
        """

        self.filename = filename
        self.__needsRewrite = False
        self.__content = content

        # Open file with "w" at least once so it will be overwritten.
        util.write_file(content, self.filename)

    def append(self, newContent, keep=True):
        """
        Add content to the represented file.
        If keep is False, the new content will be forgotten during the next call
        to this method.
        """
        content = self.__content + newContent
        if keep:
            self.__content = content

        if self.__needsRewrite:
            """
            Replace the content of the file.
            A temporary file is used to avoid loss of data through an interrupt.
            """
            tmpFilename = self.filename + ".tmp"

            util.write_file(content, tmpFilename)

            os.rename(tmpFilename, self.filename)
        else:
            with open(self.filename, "a") as file:
                file.write(newContent)

        self.__needsRewrite = not keep

    def replace(self, newContent):
        # clear and append
        self.__content = ""
        self.__needsRewrite = True
        self.append(newContent)
