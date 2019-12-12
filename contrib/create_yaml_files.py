#!/usr/bin/env python3

import glob
import os
import re
import argparse
from typing import Tuple

CHANGE_FILE_NAME = True
"""Whether to shorten file names by removing the verdicts, if possible without collisions."""
AVOID_COLLISIONS_ACROSS_DIRECTORIES = True
"""Whether to avoid same file names in different directories."""

NAME_TO_PROP_AND_SUBPROP = {
    "unreach-call": ("unreach-call.prp", None),
    "cover-error": ("coverage-error-call.prp", None),
    "unreach-label": ("ALL.prp", None),
    "termination": ("termination.prp", None),
    "no-overflow": ("no-overflow.prp", None),
    "valid-memcleanup": ("valid-memcleanup.prp", None),
    "valid-memsafety": ("valid-memsafety.prp", None),
    "valid-deref": ("valid-memsafety.prp", "valid-deref"),
    "valid-free": ("valid-memsafety.prp", "valid-free"),
    "valid-memtrack": ("valid-memsafety.prp", "valid-memtrack",),
    "def-behavior": ("def-behavior.prp", None),
}

CANDIDATE_REGEX = re.compile(r".*\.(c|i)")

DUMMY_SET = "__NO_SET__"
"""Dummy set name used for C files given on the command-line."""


def _get_prop(property_file, property_dir, task_dir):
    return os.path.relpath(os.path.join(property_dir, property_file), task_dir)


def handle_c(task_file) -> Tuple[str, dict]:
    """ Create yml task definition for the given file.
    Return a tuple of a recommended new task name and the yml info as dictionary.

    """
    properties = list()
    name_pcs_dot = task_file.split(".")
    new_name_pcs_dot = list()
    for pd in name_pcs_dot:
        name_pcs = pd.split("_")
        new_name_pcs = list()
        for p in name_pcs:
            offset = 0
            for name, prop in NAME_TO_PROP_AND_SUBPROP.items():
                if name not in p:
                    continue  # with next name_pc p
                if p.startswith("true"):
                    expected = "true"
                    offset += len("true-")
                elif p.startswith("false"):
                    expected = "false"
                    offset += len("false-")
                elif p.startswith("unknown-"):
                    expected = None
                    offset += len("unknown-")
                else:
                    continue  # with next name_pc p
                properties.append((prop, expected))
                offset += len(name)
                break  # for-loop over properties once one matches, because they are distinct
            new_p = p[offset:]
            if new_p or offset == 0:
                new_name_pcs.append(new_p)
        new_name_pcs_dot.append("_".join(new_name_pcs))

    yml_info = (task_file, properties)

    if CHANGE_FILE_NAME:
        new_task_file = ".".join(new_name_pcs_dot)
        if new_task_file[-4:] == ".c.i":
            new_task_file = new_task_file[:-4] + ".i"
    else:
        new_task_file = task_file
    return new_task_file, yml_info


def parse_args():
    parser = argparse.ArgumentParser(
        description="Script to transform old-style benchexec benchmark tasks with property and verdict in file name to new yml-based task-info style"
    )
    parser.add_argument(
        "--prop-dir",
        dest="prop_dir",
        type=str,
        default="properties/",
        required=False,
        help="directory that contains program properties to link to",
    )
    parser.add_argument(
        "files",
        metavar="file",
        nargs="+",
        help=".set files that contain task lists or C files to create yml for",
    )
    return parser.parse_args()


sets_to_tasks = dict()
all_tasks = set()

if __name__ == "__main__":
    args = parse_args()
    prop_dir = args.prop_dir

    verification_set_files = [f for f in args.files if f.endswith(".set")]
    other_files = [f for f in args.files if f not in verification_set_files]

    for verification_set in verification_set_files:
        sets_to_tasks[verification_set] = list()
        with open(verification_set, "r") as inp:
            for line in (l.strip() for l in inp.readlines()):
                if not line:
                    continue
                if "*" in line:
                    sets_to_tasks[verification_set].append("## " + line)
                for l in sorted(
                    l for l in glob.iglob(line) if CANDIDATE_REGEX.match(l)
                ):
                    all_tasks.add(l)
                    sets_to_tasks[verification_set].append(l)

    sets_to_tasks[DUMMY_SET] = other_files
    all_tasks = all_tasks.union(set(other_files))

    tasks_to_new_names_and_yml = dict()
    for task_file in all_tasks:
        # check whether preprocessed .i file exists for current .c file
        if task_file[-1] == "c" and (
            glob.glob(task_file[:-1] + "i") or glob.glob(task_file + ".i")
        ):
            print("Redundant file: ", task_file)
            continue
        new_task_file, yml_info = handle_c(task_file)
        tasks_to_new_names_and_yml[task_file] = [new_task_file, yml_info]
    # sort tasks by their new names to be deterministic
    sorted_tasks_to_new_names = list(
        sorted(tasks_to_new_names_and_yml.items(), key=lambda e: e[1][0])
    )
    for old_name, new_info in sorted_tasks_to_new_names:
        assert len(new_info) == 2
        curr_task = new_info[0]
        yml_info = new_info[1]

        def _compute_collisions(curr_task, tasks_to_new_names_and_yml):
            task_basename = os.path.basename(curr_task)
            if AVOID_COLLISIONS_ACROSS_DIRECTORIES:
                collisions = [
                    k
                    for k, v in tasks_to_new_names_and_yml.items()
                    if os.path.basename(v[0]).lower()[:-1] == task_basename.lower()[:-1]
                    and k != old_name
                ]
            else:
                collisions = [
                    k
                    for k, v in tasks_to_new_names_and_yml.items()
                    if v[0].lower()[:-1] == task_basename.lower()[:-1] and k != old_name
                ]
            return collisions

        # store original colissions for rename
        collisions = _compute_collisions(curr_task, tasks_to_new_names_and_yml)
        counter = 1
        while _compute_collisions(curr_task, tasks_to_new_names_and_yml):
            curr_task = curr_task[:-2] + "-" + str(counter) + curr_task[-2:]
            counter += 1
        tasks_to_new_names_and_yml[old_name][0] = curr_task
        for other in collisions:
            new_name = tasks_to_new_names_and_yml[other][0]
            while _compute_collisions(new_name, tasks_to_new_names_and_yml):
                new_name = new_name[:-2] + "-" + str(counter) + new_name[-2:]
                counter += 1
            tasks_to_new_names_and_yml[other][0] = new_name

        task_basename = os.path.basename(curr_task)
        yml_content = "format_version: '1.0'\n"
        yml_content += "\n"
        if CHANGE_FILE_NAME:
            yml_content += "# old file name: " + os.path.basename(old_name) + "\n"
        yml_content += "input_files: '" + task_basename + "'\n"
        yml_content += "\n"

        task_dir = os.path.dirname(curr_task)
        if not yml_info[1]:
            yml_content += "properties: []\n"
        else:
            yml_content += "properties:\n"
            for prop, expected in sorted(yml_info[1], key=lambda p: p[0][0]):
                prop_file = _get_prop(prop[0], prop_dir, task_dir)
                yml_content += "  - property_file: " + prop_file + "\n"
                if expected:
                    yml_content += "    expected_verdict: " + expected + "\n"
                if prop[1]:
                    yml_content += "    subproperty: " + prop[1] + "\n"
                if "unreach-call" in prop_file and expected == "false":
                    prop_file = _get_prop(
                        NAME_TO_PROP_AND_SUBPROP["cover-error"][0], prop_dir, task_dir
                    )
                    yml_content += "  - property_file: " + prop_file + "\n"
        yml_file = curr_task[:-2] + ".yml"
        with open(yml_file, "w+") as outp:
            outp.write(yml_content)

        if old_name != curr_task:
            os.rename(old_name, curr_task)
            if old_name[-1] == "i":
                # *.i -> *.c
                if os.path.exists(old_name[:-1] + "c"):
                    old_c = old_name[:-1] + "c"
                # *.c.i -> *.c
                elif os.path.exists(old_name[:-2]):
                    old_c = old_name[:-2]
                # ldv-memsafety/memleaks*.i -> ldv-memsafety/memleaks-notpreprocessed/memleaks*.c
                elif old_name.startswith("ldv-memsafety/memleaks"):
                    old_c = (
                        "ldv-memsafety/memleaks-notpreprocessed/"
                        + old_name.split("/")[-1][:-1]
                        + "c"
                    )
                else:
                    old_c = None
                if old_c:
                    assert old_c not in all_tasks
                    curr_task_name = curr_task.split("/")[-1]
                    new_c_name = (
                        os.path.dirname(old_c) + "/" + curr_task_name[:-1] + "c"
                    )

                    os.rename(old_c, new_c_name)
        for content in sets_to_tasks.values():
            try:
                idx = content.index(old_name)
                content[idx] = yml_file
            except ValueError:
                pass

    for task_set, content in sets_to_tasks.items():
        new_content = list()
        remaining = set(content)
        glob_suffix = "*"
        for task in content:
            if task not in remaining or task.startswith("#"):
                continue
            # get last occurrence of '/'
            try:
                last_pathsep = task.rindex("/")
                prefix_len = last_pathsep + 1
            except ValueError:
                prefix_len = 0
            prefix = task[:prefix_len]
            globbed_tasks = glob.glob(prefix + glob_suffix)
            globbed_tasks = [t for t in globbed_tasks if t.endswith(".yml")]
            assert len(globbed_tasks) > 0

            globbed_tasks = glob.glob(prefix + glob_suffix)
            globbed_tasks = [t for t in globbed_tasks if t.endswith(".yml")]
            if not task_set.endswith("testable.set") and (
                not USE_SUFFIX_WILDCARDS or len(globbed_tasks) > 3 or prefix[-1] == "/"
            ):
                new_content.append(prefix + "*.yml")
                remaining -= set(globbed_tasks)
            else:
                new_content.append(task)
                remaining.remove(task)
        if task_set != DUMMY_SET:
            with open(task_set, "w+") as outp:
                outp.writelines(l + "\n" for l in new_content)
