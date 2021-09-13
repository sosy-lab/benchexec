from functools import wraps
import logging
from pyroute2 import NetlinkError
from benchexec import BenchExecException
import struct
import os
import sys
import importlib.util
import inspect

# Convert error to make it more readable and if possible clean up.
# args[0] should
def parse_netlink_error(f):
    @wraps(f)
    def handle(*args):
        try:
            return f(args[0])
        except NetlinkError as e:
            if e.code == 17:
                print(
                    "Could not setup veth, veth already exist. Clear any previous veth's"
                )
                raise BenchExecException("Netlink Error")
            elif e.code == 2:
                print(
                    "Could not setup namespace. Namespace is invalid. Clear any previous namespace links in /var/run/netns"
                )
            # Run cleanup
            try:
                args[0].close()
            except AttributeError:
                pass

            else:
                raise NetlinkError(e)

    return handle


def create_tofino_bin(prog_name, ctx_json_path, tofino_bin_path, out_path):
    """
    Creates the bin required to run tofino switches

    Args:
        prog_name (string): Name of the program
        ctx_json_path (string): Path to context.json
        tofino_bin_path (string): Path to tofino.bin
        out_path (string): Path to pin output
    """

    logging.debug(
        f"Building bin file with: program name: {prog_name} context.json: {ctx_json_path} tofino.bin: {tofino_bin_path} outfile: {out_path}"
    )

    with open(ctx_json_path, "rb") as ctx_json_f, open(
        tofino_bin_path, "rb"
    ) as bin_f, open(out_path, "wb") as out_f:
        prog_name_bytes = prog_name.encode()
        out_f.write(struct.pack("<i", len(prog_name_bytes)))
        out_f.write(prog_name_bytes)
        tofino_bin = bin_f.read()
        out_f.write(struct.pack("<i", len(tofino_bin)))
        out_f.write(tofino_bin)
        ctx_json = ctx_json_f.read()
        out_f.write(struct.pack("<i", len(ctx_json)))
        out_f.write(ctx_json)


def find_bin_and_context(p4_build_path, prog_name):
    """
    Walks through given path and looks for a folder containing the program name
    and contains a context.json and tofino.bin

    Args:
        p4_build_path (string): Root path
        prog_name (string): Name of the p4 program

    Returns:
        [(string, string)]: Tuple with path to context.json and tofino.bin. Returns empty strings if nothing
        was found.
    """
    context_path = ""
    tofino_bin_path = ""

    for root, dir, files in os.walk(p4_build_path):
        if "context.json" in files and "tofino.bin" in files:
            path_list = root.split("/")
            if prog_name in path_list:
                context_path = os.path.join(root, "context.json")
                tofino_bin_path = os.path.join(root, "tofino.bin")

                return context_path, tofino_bin_path


def find_test_network_configs(ptf_path):

    # Temp disable logging
    logger = logging.getLogger()
    old_lvl = logger.level
    logger.setLevel(logging.FATAL)

    network_configs = {}

    files = []
    for src, _, filenames in os.walk(ptf_path):
        for filename in filenames:
            if filename.endswith(".py"):
                files.append((src, filename.replace(".py", "")))

    for src, filename in files:
        if not src in sys.path:
            sys.path.append(src)

        spec = importlib.util.spec_from_file_location(
            filename.replace(".py", ""), f"{src}/{filename}.py"
        )
        foo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(foo)

        # foo = importlib.import_module(filename.replace(".py", ""))

        for name, obj in inspect.getmembers(foo):
            if inspect.isclass(obj):
                try:
                    cls = getattr(foo, name)

                    net_conf = cls.get_network_config()

                    if net_conf:
                        network_configs[f"{filename}.{name}"] = net_conf
                        # network_configs.append((f"{filename}.{name}", net_conf))
                except:
                    continue

    logger.setLevel(old_lvl)

    return network_configs


def main():
    # ctx, tof = find_bin_and_context(
    #     "/home/p4/installations/bf-sde-9.5.0", "simple_switch2"
    # )

    # create_tofino_bin(
    #     "simple_switch2", ctx, tof, "/home/p4/installations/p4runtime-shell/out.bin"
    # )

    test_dict = find_test_network_configs(
        "/home/p4/bf_benchexec/benchexec/contrib/p4_files/docker_files/ptf_tester/tests"
    )

    if "test_no_fail.IPV4OneSwitchTest" in test_dict:
        print("test")


if __name__ == "__main__":
    main()
