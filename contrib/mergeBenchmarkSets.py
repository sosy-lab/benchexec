#!/usr/bin/env python3

# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import sys

import argparse
from decimal import Decimal, InvalidOperation
import os
import io
from xml.etree import ElementTree
import bz2

from benchexec import result
from benchexec import tablegenerator
from benchexec.tablegenerator import util

sys.dont_write_bytecode = True  # prevent creation of .pyc files


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "resultsXML",
        metavar="results-xml",
        help="XML-file containing the verification results.",
    )
    parser.add_argument(
        "witnessXML",
        nargs="*",
        metavar="witness-xml",
        help="Any number of XML-files containing validation results.",
    )
    parser.add_argument(
        "--no-overwrite-status-true",
        action="store_true",
        help="Do not overwrite true results with results from validation.",
    )
    parser.add_argument(
        "-o",
        "--outputpath",
        metavar="OUT_PATH",
        help="Directory in which the generated output files will be placed.",
    )
    return parser.parse_args(argv)


def xml_to_string(elem, qualified_name=None, public_id=None, system_id=None):
    """
    Return a pretty-printed XML string for the Element.
    Also allows setting a document type.
    """
    from xml.dom import minidom

    rough_string = ElementTree.tostring(elem, "utf-8")
    reparsed = minidom.parseString(rough_string)
    if qualified_name:
        doctype = minidom.DOMImplementation().createDocumentType(
            qualified_name, public_id, system_id
        )
        reparsed.insertBefore(doctype, reparsed.documentElement)
    return reparsed.toprettyxml(indent="  ")


def get_witnesses(witness_xml):
    witnesses = {}
    for run in witness_xml.findall("run"):
        name = run.get("name")
        witnesses[name] = run
    return witnesses


def get_witness_result(witness, verification_result):

    if witness is None:
        # If there is no witness, then this is an error of the verifier.
        return "witness missing", result.CATEGORY_ERROR

    status_from_validation = witness.find('column[@title="status"]').get("value")
    try:
        status_from_verification = verification_result.find(
            'column[@title="status"]'
        ).get("value")
        category_from_verification = verification_result.find(
            'column[@title="category"]'
        ).get("value")
    except AttributeError:
        status_from_verification = "not found"
        category_from_verification = "not found"

    # If the result from witness validation matches the result from verification,
    # then leave status and category as is.
    if status_from_validation == status_from_verification:
        return status_from_verification, category_from_verification
    # An invalid witness counts as error of the verifier.
    if status_from_validation == "ERROR (invalid witness syntax)":
        return (
            f"witness invalid ({status_from_verification})",
            result.CATEGORY_ERROR,
        )
    # Other unconfirmed witnesses count as CATEGORY_CORRECT_UNCONFIRMED.
    if category_from_verification == result.CATEGORY_CORRECT:
        return status_from_verification, result.CATEGORY_CORRECT_UNCONFIRMED

    return f"result invalid ({status_from_verification})", result.CATEGORY_ERROR


def get_validation_result(
    run, witness_sets, status_from_verification, category_from_verification
):
    status_wit, category_wit = None, None
    name = run.get("name")
    for witnessSet in witness_sets:
        witness = witnessSet.get(name)
        if not witness:
            continue
        # copy data from witness
        if run.get("properties") == "coverage-error-call":
            status_from_validation = witness.find('column[@title="status"]').get(
                "value"
            )
            if status_from_validation == "true":
                status_wit, category_wit = (
                    status_from_verification,
                    result.CATEGORY_CORRECT,
                )
                category_from_verification = result.CATEGORY_CORRECT
                score_column = ElementTree.Element("column", title="score", value="1")
                run.append(score_column)
        elif run.get("properties") == "coverage-branches":
            try:
                coverage_value = (
                    witness.find('column[@title="branches_covered"]')
                    .get("value")
                    .replace("%", "")
                )
            except AttributeError:
                coverage_value = "0.00"
            status_wit, category_wit = (
                status_from_verification,
                result.CATEGORY_CORRECT,
            )
            category_from_verification = result.CATEGORY_CORRECT
            try:
                coverage_percentage = Decimal(coverage_value) / 100
            except InvalidOperation:
                continue
            score_column = ElementTree.Element(
                "column",
                title="score",
                value=util.print_decimal(coverage_percentage),
            )
            run.append(score_column)
        else:
            # For verification
            if status_wit and status_wit.startswith("witness invalid"):
                continue
            status_wit_new, category_wit_new = get_witness_result(witness, run)
            if (
                category_wit is None
                or not category_wit.startswith(result.CATEGORY_CORRECT)
                or category_wit_new == result.CATEGORY_CORRECT
                or status_wit_new.startswith("witness invalid")
            ):
                status_wit, category_wit = (status_wit_new, category_wit_new)
    return (
        status_wit,
        category_wit,
        status_from_verification,
        category_from_verification,
    )


def merge(result_xml, witness_sets, overwrite_status):
    for run in result_xml.findall("run"):
        try:
            status_from_verification = run.find('column[@title="status"]').get("value")
        except AttributeError:
            status_from_verification = "not found"
        try:
            category_from_verification = run.find('column[@title="category"]').get(
                "value"
            )
        except AttributeError:
            category_from_verification = "not found"
        (
            statusWit,
            categoryWit,
            status_from_verification,
            category_from_verification,
        ) = get_validation_result(
            run,
            witness_sets,
            status_from_verification,
            category_from_verification,
        )
        # Overwrite status with status from witness
        if (
            (
                overwrite_status
                or result.RESULT_CLASS_FALSE
                == result.get_result_classification(status_from_verification)
            )
            and "correct" == category_from_verification
            and statusWit is not None
            and categoryWit is not None
        ):
            try:
                run.find('column[@title="status"]').set("value", statusWit)
            except AttributeError:
                status_column = ElementTree.Element(
                    "column", title="status", value=statusWit
                )
                run.append(status_column)
            try:
                run.find('column[@title="category"]').set("value", categoryWit)
            except AttributeError:
                category_column = ElementTree.Element(
                    "column", title="category", value=categoryWit
                )
                run.append(category_column)
        # Clean-up an entry that can be inferred by table-generator automatically, avoids path confusion
        del run.attrib["logfile"]


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    args = parse_args(argv)
    result_file = args.resultsXML
    witness_files = args.witnessXML
    overwrite_status = not args.no_overwrite_status_true
    out_dir = args.outputpath
    assert witness_files or not overwrite_status

    if not os.path.exists(result_file) or not os.path.isfile(result_file):
        sys.exit(f"File {result_file!r} does not exist.")
    result_xml = tablegenerator.parse_results_file(result_file)
    witness_sets = []
    for witnessFile in witness_files:
        if not os.path.exists(witnessFile) or not os.path.isfile(witnessFile):
            sys.exit(f"File {witnessFile!r} does not exist.")
        witness_xml = tablegenerator.parse_results_file(witnessFile)
        witness_sets.append(get_witnesses(witness_xml))

    merge(result_xml, witness_sets, overwrite_status)

    filename = result_file + ".merged.xml.bz2"
    if out_dir is not None:
        outfile = os.path.join(out_dir, os.path.basename(filename))
    else:
        outfile = filename
    os.makedirs(os.path.dirname(outfile), exist_ok=True)
    print("    " + outfile)
    with io.TextIOWrapper(bz2.BZ2File(outfile, "wb"), encoding="utf-8") as xml_file:
        xml_file.write(
            xml_to_string(result_xml).replace("    \n", "").replace("  \n", "")
        )


if __name__ == "__main__":
    sys.exit(main())
