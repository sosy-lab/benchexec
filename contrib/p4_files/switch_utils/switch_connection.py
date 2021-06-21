import logging
import sys
import time
import grpc
import struct
import socket
from functools import wraps
from p4.v1 import p4runtime_pb2, p4runtime_pb2_grpc
from p4.config.v1 import p4info_pb2
from .p4info_helper import P4InfoHelper

from p4.tmp import p4config_pb2

import google.protobuf.text_format
from google.rpc import status_pb2, code_pb2
import queue
import threading

# Taken from p4runtime-sh github
class P4RuntimeException(Exception):
    def __init__(self, grpc_error):
        super().__init__()
        self.grpc_error = grpc_error

    def __str__(self):
        message = "P4Runtime RPC error ({}): {}".format(
            self.grpc_error.code().name, self.grpc_error.details()
        )
        return message


def parse_p4runtime_error(f):
    @wraps(f)
    def handle(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except grpc.RpcError as e:
            raise P4RuntimeException(e) from None

    return handle


class SwitchConnection(object):
    """
    Defines a gRPC connection to a switch.
    """

    def __init__(self, grpc_address, device_id, election_id) -> None:
        self.grpc_addr = grpc_address
        self.device_id = device_id
        self.election_id = election_id

        self.connected = False

        try:
            self.channel = grpc.insecure_channel(self.grpc_addr)
        except:
            logging.critical("Failed to connect to P4Runtime server")
            sys.exit(1)

        self.stub = p4runtime_pb2_grpc.P4RuntimeStub(self.channel)
        # self.setup_stream()

    def setup_stream(self):
        self.stream_out_q = queue.Queue()
        self.stream_in_q = queue.Queue()
        self.error_q = queue.Queue()

        def stream_req_iterator():
            while True:
                p = self.stream_out_q.get()
                if p is None:
                    break
                yield p

        def stream_recv_wrapper(stream):
            def stream_recv():
                try:
                    for p in stream:
                        self.stream_in_q.put(p)
                except grpc.RpcError as e:
                    self.error_q.put(e)

            stream_recv()

        self.stream = self.stub.StreamChannel(stream_req_iterator())
        self.stream_recv_thread = threading.Thread(
            target=stream_recv_wrapper, args=(self.stream,)
        )
        self.stream_recv_thread.start()

        self.handshake()

    def wait_for_setup(self, timeout=60):
        start = time.time()
        while True:
            time_passed = time.time() - start

            if time_passed > timeout or self.connected:
                break

            self.setup_stream()

    def handshake(self):
        req = p4runtime_pb2.StreamMessageRequest()
        arbitration = req.arbitration
        arbitration.device_id = self.device_id
        arbitration.election_id.high = self.election_id[1]
        arbitration.election_id.low = self.election_id[0]

        self.stream_out_q.put(req)
        rep = self.get_stream_packet("arbitration", timeout=2)

        if rep is not None:
            self.connected = rep.arbitration.status.code == code_pb2.OK

        return rep

    def get_stream_packet(self, type_, timeout=1):
        start = time.time()
        try:
            while True:
                remaining = timeout - (time.time() - start)
                if remaining < 0:
                    break
                msg = self.stream_in_q.get(timeout=remaining)
                if msg is None:
                    return None
                if not msg.HasField(type_):
                    continue
                return msg
        except queue.Empty:  # timeout expired
            pass
        return None

    def write_table_entry(self, table_entry):
        request = p4runtime_pb2.WriteRequest()
        request.device_id = self.device_id
        request.election_id.low = self.election_id[0]
        request.election_id.high = self.election_id[1]
        update = request.updates.add()

        if table_entry.is_default_action:
            update.type = p4runtime_pb2.Update.MODIFY
        else:
            update.type = p4runtime_pb2.Update.INSERT
        update.entity.table_entry.CopyFrom(table_entry)

        self.stub.Write(request)

    def read_table_entries(self, table_id=None):
        request = p4runtime_pb2.ReadRequest()
        request.device_id = self.device_id
        entity = request.entities.add()
        table_entry = entity.table_entry
        if table_id is not None:
            table_entry.table_id = table_id
        else:
            table_entry.table_id = 0

        for response in self.stub.Read(request):
            yield response

    def SetForwardingPipelineConfig(self, bin_path, cxt_json_path, prog_name):
        def build_tofino_config(prog_name, bin_path, cxt_json_path):
            device_config = p4config_pb2.P4DeviceConfig()
            with open(bin_path, "rb") as bin_f:
                with open(cxt_json_path, "r") as cxt_json_f:
                    device_config.device_data = "".encode()
                    device_config.device_data += struct.pack("<i", len(prog_name))
                    device_config.device_data += prog_name.encode()
                    tofino_bin = bin_f.read()
                    device_config.device_data += struct.pack("<i", len(tofino_bin))
                    device_config.device_data += tofino_bin
                    cxt_json = cxt_json_f.read()
                    device_config.device_data += struct.pack("<i", len(cxt_json))
                    device_config.device_data += cxt_json.encode()
            return device_config

        req = p4runtime_pb2.SetForwardingPipelineConfigRequest()
        # …
        config = req.config
        # …
        # device_config = build_tofino_config(prog_name, bin_path, cxt_json_path)
        # config.p4_device_config = device_config.SerializeToString()

        req.device_id = self.device_id
        req.election_id.low = self.election_id[0]
        req.election_id.high = self.election_id[1]

        with open(bin_path, "rb") as bin_f:
            with open(cxt_json_path, "r") as cxt_json_f:
                config.p4_device_config = "".encode()
                config.p4_device_config += struct.pack("<i", len(prog_name))
                config.p4_device_config += prog_name.encode()
                tofino_bin = bin_f.read()
                config.p4_device_config += struct.pack("<i", len(tofino_bin))
                config.p4_device_config += tofino_bin
                cxt_json = cxt_json_f.read()
                config.p4_device_config += struct.pack("<i", len(cxt_json))
                config.p4_device_config += cxt_json.encode()

        req.action = p4runtime_pb2.SetForwardingPipelineConfigRequest.VERIFY_AND_COMMIT

        self.stub.SetForwardingPipelineConfig(req)

    def SetForwadingPipelineConfig2(self, p4info_path, bin_path):
        request = p4runtime_pb2.SetForwardingPipelineConfigRequest()
        request.election_id.low = self.election_id[0]
        request.election_id.high = self.election_id[1]
        request.device_id = self.device_id

        request.action = (
            p4runtime_pb2.SetForwardingPipelineConfigRequest.VERIFY_AND_COMMIT
        )

        self.p4info = p4info_pb2.P4Info()

        with open(p4info_path, "r") as p4info_file:
            google.protobuf.text_format.Merge(p4info_file.read(), self.p4info)

        request.config.p4info.CopyFrom(self.p4info)

        with open(bin_path, "rb") as bin_file:
            request.config.p4_device_config = bin_file.read()

        msg = self.stub.SetForwardingPipelineConfig(request)

        return msg

    def GetForwardingPipelineConfig(self):
        req = p4runtime_pb2.GetForwardingPipelineConfigRequest()
        test = self.stub.GetForwardingPipelineConfig(req)

        return test.config.p4info

    def shutdown(self):
        if self.stream_out_q:
            self.stream_out_q.put(None)
            self.stream_recv_thread.join()
        self.channel.close()


def main():

    P4_INFO_FILEPATH = "/home/p4/installations/bf-sde-9.5.0/build/p4-build/tofino/simple_switch/tofino/p4info2.pb.txt"
    INFO_PATH = (
        "/home/p4/installations/bf-sde-9.5.0/install/share/tofinopd/simple_switch"
    )

    BIN_PATH = f"{INFO_PATH}/pipe/tofino.bin"
    CONTEXT_PATH = f"{INFO_PATH}/pipe/context.json"
    PROG_NAME = "simple_switch"

    COMBINED_BIN_PATH = "/home/p4/P4_Runtime/out.bin"

    # Test P4Info
    p4_info_helper = P4InfoHelper(P4_INFO_FILEPATH)

    id = p4_info_helper.get_id("tables", "Ingress.ipv4_lpm")

    table_entry = p4_info_helper.build_table_entry(
        table_name="Ingress.ipv4_lpm",
        match_fields={"hdr.ipv4.dst_addr": ("192.0.0.2", 32)},
        action_name="Ingress.ipv4_forward",
        action_params={"egress_port": 10},
    )

    print("Done")

    connection = SwitchConnection("127.0.0.1:50051", 0, (0, 1))
    connection.wait_for_setup()

    connection.SetForwadingPipelineConfig2(P4_INFO_FILEPATH, COMBINED_BIN_PATH)

    test = connection.read_table_entries(id)

    for i in test:
        print(i)

    connection.write_table_entry(table_entry)

    test = connection.read_table_entries(id)

    for i in test:
        print(i)

    # connection.bindPipelineConfig()
    # print(connection.get_bfrt_info())


if __name__ == "__main__":
    main()
