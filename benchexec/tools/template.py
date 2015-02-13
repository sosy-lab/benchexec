import benchexec.util as util

class BaseTool(object):
    """
    This class serves both as a template for tool adaptor implementations,
    and as an abstract super class for them.
    For writing a new tool adaptor, inherit from this class and override
    the necessary methods (usually only executable(), name(), and determine_result(),
    maybe version() and cmdline(), too).
    The classes for each specific tool need to be named "Tool"
    and be located in a module named "benchmark.tools.<tool>",
    where "<tool>" is the string specified by the user in the benchmark definition.
    """

    def executable(self):
        """
        Find the path to the executable file that will get executed.
        This method always needs to be overridden,
        and most implementations will look similar to this one.
        """
        return util.find_executable('tool')


    def version(self, executable):
        """
        Determine a version string for this tool, if available.
        """
        return ''


    def name(self):
        """
        Return the name of the tool, formatted for humans.
        """
        return 'UNKOWN'


    def cmdline(self, executable, options, sourcefiles, propertyfile=None, rlimits={}):
        """
        Compose the command line to execute from the name of the executable,
        the user-specified options, and the sourcefile to analyze.
        This method can get overridden, if, for example, some options should
        be enabled or if the order of arguments must be changed.

        @param executable: the path to the executable of the tool, the result of executable()
        @param options: a list of options, in the same order as given in the XML-file.
        @param sourcefiles: a list of sourcefiles, that should be analysed with the tool in one run.
                            In most cases we we have only _one_ sourcefile.
        @param propertyfile: contains a specification for the verifier.
        @param rlimits: This dictionary contains resource-limits for a run,
                        for example: time-limit, soft-time-limit, hard-time-limit, memory-limit, cpu-core-limit.
                        All entries in rlimits are optional, so check for existence before usage!
        """
        return [executable] + options + sourcefiles


    def determine_result(self, returncode, returnsignal, output, isTimeout):
        """
        Parse the output of the tool and extract the verification result.
        This method always needs to be overridden.
        """
        return 'UNKNOWN'


    def add_column_values(self, output, columns):
        """
        OPTIONAL, override this to add statistics data from the output of the tool
        to the tables if requested by the user.
        If a value is not found, it should be set to '-'.
        """
        pass


    def program_files(self, executable):
        """
        OPTIONAL, this method is only necessary for situations when the benchmark environment
        needs to know all files belonging to a tool
        (to transport them to a cloud service, for example).
        Returns a list of files or directories that are necessary to run the tool.
        """
        return []


    def working_directory(self, executable):
        """
        OPTIONAL, this method is only necessary for situations
        when the tool needs a separate working directory.
        """
        return "."


    def environment(self, executable):
        """
        OPTIONAL, this method is only necessary for tools
        that needs special environment variable.
        Returns a map, that contains identifiers for several submaps.
        All keys and values have to be Strings!
        
        Currently we support 2 identifiers:
        
        "newEnv": Before the execution, the values are assigned to the real environment-identifiers.
                  This will override existing values.
        "additionalEnv": Before the execution, the values are appended to the real environment-identifiers.
                  The seperator for the appending must be given in this method,
                  so that the operation "realValue + additionalValue" is a valid value.
                  For example in the PATH-variable the additionalValue starts with a ":".
        """
        return {}
