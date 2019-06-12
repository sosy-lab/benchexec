"""
    The main module to parse command line arguments and call specific pqos_wrapper API.
"""
import sys
import ctypes
import json
from pqos_wrapper.utils import argument_parser, wrapper_handle_error, prepare_cmd_output
from ctypes.util import find_library


class CPqosConfig(ctypes.Structure):
    """
        pqos_config structure
    """

    # pylint: disable=too-few-public-methods

    PQOS_INTER_MSR = 0
    PQOS_INTER_OS = 1

    LOG_VER_VERBOSE = 1
    LOG_VER_SILENT = -1

    LOG_CALLBACK = ctypes.CFUNCTYPE(
        None, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_char_p
    )

    _fields_ = [
        (u"fd_log", ctypes.c_int),
        (u"callback_log", LOG_CALLBACK),
        (u"context_log", ctypes.c_void_p),
        (u"verbose", ctypes.c_int),
        (u"interface", ctypes.c_int),
    ]

    def __init__(
        self,
        interface,
        fd_log=0,
        callback_log=LOG_CALLBACK(0),
        verbose=LOG_VER_SILENT,
        context_log=None,
    ):
        super(CPqosConfig, self).__init__(
            fd_log, callback_log, context_log, verbose, interface
        )


class PqosWrapper(object):
    """
        The Wrapper class to parse arguments and call pqos API 
    """

    return_code = 0

    def __init__(self, argv):
        """
            Parse cli arguments and finds PQoS library to construct a new object.
                
                @argv: the command line arguments passed to the CLI
        """
        self.config = argument_parser(argv[1:])
        libpqos_path = find_library(u"pqos")
        if not libpqos_path:
            wrapper_handle_error("pqos library initialisation error", 1, "find_library")
        self.lib = ctypes.cdll.LoadLibrary(libpqos_path)

    @classmethod
    def main(cls):
        """
            The entry point for the CLI.
        """
        __instance = cls(sys.argv)
        __instance.execute_cli()
        return __instance.return_code

    def execute_cli(self):
        """
            The pipeline for executing pqos API and print dictionary output
            based on the given arguments of the CLI
        """
        return_dict = {}
        return_dict["load_pqos"] = self.load_pqos(self.config["interface"])
        print(json.dumps(return_dict, indent=4))

    def load_pqos(self, interface):
        """
            Initializes PQoS library
            
            @interface: an interface to be used by PQoS library, 
                        Available options: MSR, OS
        """
        cfg_interface = (
            CPqosConfig.PQOS_INTER_MSR
            if interface.upper() == u"MSR"
            else CPqosConfig.PQOS_INTER_OS
        )
        config = CPqosConfig(cfg_interface)
        ret = self.lib.pqos_init(ctypes.byref(config))
        wrapper_handle_error(
            "{} interface initialisation error".format(interface), ret, "pqos_init"
        )
        return prepare_cmd_output(
            "{} interface intialised".format(interface), "pqos_init"
        )
