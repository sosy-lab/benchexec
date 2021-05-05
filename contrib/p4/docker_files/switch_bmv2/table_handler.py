# SPDX-FileCopyrightText: 2020-2021 CASTOR Software Research Centre
# <https://www.castor.kth.se/>
# SPDX-FileCopyrightText: 2020-2021 Johan Paulsson

# SPDX-License-Identifier: Apache-2.0

import os
import json
import subprocess
import argparse

PATH_TO_TABLE_JSON = "/app/ip_table.json"
PATH_TO_CLI = "/usr/local/behavioral-model/tools/runtime_CLI.py"

# Parser
parser = argparse.ArgumentParser()
parser.add_argument("table_file")

args = parser.parse_args()


def main():
    with open(args.table_file) as json_file:
        data = json.load(json_file)

        final_command = PATH_TO_CLI

        with open("/app/table_input.txt", "w") as fstdin:
            for table_entry in data["table_entries"]:
                CLI_command = (
                    "table_add"
                    " " + str(table_entry["table_name"]) + ""
                    " " + str(table_entry["action_name"]) + ""
                    " "
                    + str(table_entry["match"][0])
                    + "/"
                    + str(table_entry["match"][1])
                    + ""
                    " => "
                    + str(table_entry["action_params"]["dstAddr"])
                    + " "
                    + str(table_entry["action_params"]["port"])
                )

                fstdin.write(CLI_command + "\n")
                final_command += "; " + CLI_command

        with open("/app/table_command_output.txt", "w") as fout:
            with open("/app/table_input.txt", "r") as pyargs:
                subprocess.run(PATH_TO_CLI, stdin=pyargs, stdout=fout, shell=True)


if __name__ == "__main__":
    main()
