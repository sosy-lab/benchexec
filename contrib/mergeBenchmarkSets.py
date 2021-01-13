#!/usr/bin/env python3

# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import sys

import argparse
from decimal import Decimal
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


def getWitnesses(witnessXML):
    witnesses = {}
    for run in witnessXML.findall("run"):
        name = run.get("name")
        witnesses[name] = run
    return witnesses


def getWitnessResult(witness, verification_result):

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
            "witness invalid (" + status_from_verification + ")",
            result.CATEGORY_ERROR,
        )
    # Other unconfirmed witnesses count as CATEGORY_CORRECT_UNCONFIRMED.
    if category_from_verification == result.CATEGORY_CORRECT:
        return status_from_verification, result.CATEGORY_CORRECT_UNCONFIRMED

    return "result invalid (" + status_from_verification + ")", result.CATEGORY_ERROR


def getValidationResult(
    run, witnessSets, status_from_verification, category_from_verification
):
    statusWit, categoryWit = None, None
    name = run.get("name")
    for witnessSet in witnessSets:
        witness = witnessSet.get(name)
        if not witness:
            continue
        # copy data from witness
        if run.get("properties") == "coverage-error-call":
            status_from_validation = witness.find('column[@title="status"]').get(
                "value"
            )
            if status_from_validation == "true":
                statusWit, categoryWit = (
                    status_from_verification,
                    result.CATEGORY_CORRECT,
                )
                category_from_verification = result.CATEGORY_CORRECT
                scoreColumn = ElementTree.Element("column", title="score", value="1")
                run.append(scoreColumn)
        elif run.get("properties") == "coverage-branches":
            try:
                coverage_value = (
                    witness.find('column[@title="branches_covered"]')
                    .get("value")
                    .replace("%", "")
                )
            except AttributeError:
                coverage_value = "0.00"
            statusWit, categoryWit = (status_from_verification, result.CATEGORY_CORRECT)
            category_from_verification = result.CATEGORY_CORRECT
            try:
                coverage_percentage = Decimal(coverage_value) / 100
            except ValueError:
                continue
            scoreColumn = ElementTree.Element(
                "column",
                title="score",
                value=util.print_decimal(coverage_percentage),
            )
            run.append(scoreColumn)
        else:
            # For verification
            if statusWit and statusWit.startswith("witness invalid"):
                continue
            statusWitNew, categoryWitNew = getWitnessResult(witness, run)
            if (
                categoryWit is None
                or not categoryWit.startswith(result.CATEGORY_CORRECT)
                or categoryWitNew == result.CATEGORY_CORRECT
                or statusWitNew.startswith("witness invalid")
            ):
                statusWit, categoryWit = (statusWitNew, categoryWitNew)
    return statusWit, categoryWit, status_from_verification, category_from_verification


def merge(resultXML, witnessSets, isOverwrite):
    for run in resultXML.findall("run"):
        try:
            status_from_verification = run.find('column[@title="status"]').get("value")
            category_from_verification = run.find('column[@title="category"]').get(
                "value"
            )
        except AttributeError:
            status_from_verification = "not found"
            category_from_verification = "not found"
        (
            statusWit,
            categoryWit,
            status_from_verification,
            category_from_verification,
        ) = getValidationResult(
            run,
            witnessSets,
            status_from_verification,
            category_from_verification,
        )
        # Overwrite status with status from witness
        if (
            (
                isOverwrite
                or result.RESULT_CLASS_FALSE
                == result.get_result_classification(status_from_verification)
            )
            and "correct" == category_from_verification
            and statusWit is not None
            and categoryWit is not None
        ):
            try:
                run.find('column[@title="status"]').set("value", statusWit)
                run.find('column[@title="category"]').set("value", categoryWit)
            except AttributeError:
                pass
        # Clean-up an entry that can be inferred by table-generator automatically, avoids path confusion
        del run.attrib["logfile"]


def main(argv=None):

    if argv is None:
        argv = sys.argv

    args = parse_args(argv[1:])
    resultFile = args.resultsXML
    witnessFiles = args.witnessXML
    isOverwrite = not args.no_overwrite_status_true
    assert witnessFiles or not isOverwrite

    if not os.path.exists(resultFile) or not os.path.isfile(resultFile):
        sys.exit("File {0} does not exist.".format(repr(resultFile)))
    resultXML = tablegenerator.parse_results_file(resultFile)
    witnessSets = []
    for witnessFile in witnessFiles:
        if not os.path.exists(witnessFile) or not os.path.isfile(witnessFile):
            sys.exit("File {0} does not exist.".format(repr(witnessFile)))
        witnessXML = tablegenerator.parse_results_file(witnessFile)
        witnessSets.append(getWitnesses(witnessXML))

    merge(resultXML, witnessSets, isOverwrite)

    filename = resultFile + ".merged.xml.bz2"
    print("    " + filename)
    with io.TextIOWrapper(bz2.BZ2File(filename, "wb"), encoding="utf-8") as xml_file:
        xml_file.write(
            xml_to_string(resultXML).replace("    \n", "").replace("  \n", "")
        )


if __name__ == "__main__":
    sys.exit(main())
