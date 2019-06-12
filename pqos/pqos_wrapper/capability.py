"""
The module defines PqosCap which can be used to read PQoS capabilities.
"""

import ctypes
from pqos_wrapper.utils import wrapper_handle_error, prepare_cmd_output


class CPqosCapabilityL3(ctypes.Structure):
    "pqos_cap_l3ca structure"
    # pylint: disable=too-few-public-methods

    _fields_ = [
        (u"mem_size", ctypes.c_uint),
        (u"num_classes", ctypes.c_uint),
        (u"num_ways", ctypes.c_uint),
        (u"way_size", ctypes.c_uint),
        (u"way_contention", ctypes.c_uint64),
        (u"cdp", ctypes.c_int),
        (u"cdp_on", ctypes.c_int),
    ]


class CPqosCapabilityL2(ctypes.Structure):
    "pqos_cap_l2ca structure"
    # pylint: disable=too-few-public-methods

    _fields_ = [
        (u"mem_size", ctypes.c_uint),
        (u"num_classes", ctypes.c_uint),
        (u"num_ways", ctypes.c_uint),
        (u"way_size", ctypes.c_uint),
        (u"way_contention", ctypes.c_uint64),
        (u"cdp", ctypes.c_int),
        (u"cdp_on", ctypes.c_int),
    ]


class CPqosCapabilityMBA(ctypes.Structure):
    "pqos_cap_mba structure"
    # pylint: disable=too-few-public-methods

    _fields_ = [
        (u"mem_size", ctypes.c_uint),
        (u"num_classes", ctypes.c_uint),
        (u"throttle_max", ctypes.c_uint),
        (u"throttle_step", ctypes.c_uint),
        (u"is_linear", ctypes.c_int),
        (u"ctrl", ctypes.c_int),
        (u"ctrl_on", ctypes.c_int),
    ]


class CPqosMonitor(ctypes.Structure):
    "pqos_monitor structure"
    # pylint: disable=too-few-public-methods

    PQOS_MON_EVENT_L3_OCCUP = 1
    PQOS_MON_EVENT_LMEM_BW = 2
    PQOS_MON_EVENT_TMEM_BW = 4
    PQOS_MON_EVENT_RMEM_BW = 8
    RESERVED1 = 0x1000
    RESERVED2 = 0x2000
    PQOS_PERF_EVENT_LLC_MISS = 0x4000
    PQOS_PERF_EVENT_IPC = 0x8000

    _fields_ = [
        (u"type", ctypes.c_int),
        (u"max_rmid", ctypes.c_uint),
        (u"scale_factor", ctypes.c_uint32),
    ]


class CPqosCapabilityMonitoring(ctypes.Structure):
    "pqos_cap_mon structure"
    # pylint: disable=too-few-public-methods

    _fields_ = [
        (u"mem_size", ctypes.c_uint),
        (u"max_rmid", ctypes.c_uint),
        (u"l3_size", ctypes.c_uint),
        (u"num_events", ctypes.c_uint),
        (u"events", CPqosMonitor * 0),
    ]


class CPqosCapabilityUnion(ctypes.Union):
    "Union from pqos_capability structure"
    # pylint: disable=too-few-public-methods

    _fields_ = [
        (u"mon", ctypes.POINTER(CPqosCapabilityMonitoring)),
        (u"l3ca", ctypes.POINTER(CPqosCapabilityL3)),
        (u"l2ca", ctypes.POINTER(CPqosCapabilityL2)),
        (u"mba", ctypes.POINTER(CPqosCapabilityMBA)),
        (u"generic_ptr", ctypes.c_void_p),
    ]


class CPqosCapability(ctypes.Structure):
    "pqos_capability structure"
    # pylint: disable=too-few-public-methods

    _fields_ = [(u"type", ctypes.c_int), (u"u", CPqosCapabilityUnion)]


class CPqosCap(ctypes.Structure):
    "pqos_cap structure"
    # pylint: disable=too-few-public-methods

    _fields_ = [
        (u"mem_size", ctypes.c_uint),
        (u"version", ctypes.c_uint),
        (u"num_cap", ctypes.c_uint),
        (u"capabilities", CPqosCapability * 0),
    ]


class PqosCapability(object):
    """
        This class is used to retrieve capabilities from pqos.
    """

    def __init__(self, pqos_lib):
        """
            Initialise capabilities from pqos.

                @pqos_lib: The pqos library instance.
        """
        self.lib = pqos_lib
        self.p_cap = ctypes.POINTER(CPqosCap)()
        ret = self.lib.pqos_cap_get(ctypes.byref(self.p_cap), None)
        wrapper_handle_error(
            "Could not initialise capabilities from pqos", ret, "pqos_cap_get"
        )

    def get_type(self, __type):
        """
            Retrieves the given capability from pqos capabilities object.

                @__type: The name of the capability,
                         Available options: l3ca
        """
        p_cap_item = ctypes.POINTER(CPqosCapability)()
        ret = self.lib.pqos_cap_get_type(
            self.p_cap,
            self.available_capabilities(__type.lower()),
            ctypes.byref(p_cap_item),
        )
        wrapper_handle_error(
            "Failed to retrieve {} capability".format(__type.lower()),
            ret,
            "pqos_cap_get_type",
        )
        cap_item = p_cap_item.contents
        capability = self.get_capability_info(cap_item, __type)
        return prepare_cmd_output(
            "Retrieved {} capability".format(__type.lower()),
            "get_capability_info",
            **capability
        )

    @staticmethod
    def available_capabilities(__type):
        """
            Check if given capability is available in system and return
            its enum code.

                @__type: The name of the capability.
        """
        available_capabilities = {
            "mon" : 0,
            "l3ca": 1,
            "l2ca" : 2,
            "mba" : 3
        }
        if __type not in available_capabilities.keys():
            wrapper_handle_error(
                "Invalid capability requested, available options: {}".format(
                    ", ".join(list(available_capabilities.keys()))
                ),
                2,
                "available_capabilities",
            )
        return available_capabilities[__type]

    @staticmethod
    def get_capability_info(cap_item, __type):
        """
            Get the information of the requested capability from capabilites object

                @cap_item: CPqosCapability object containing capability information.
                @__type: The name of capability requested.
        """
        capability_info = {}
        cap_object = getattr(cap_item.u, __type.lower()).contents
        for field in cap_object._fields_:
            capability_info[field[0]] = getattr(cap_object, field[0])
        return capability_info
