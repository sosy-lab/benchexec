#!/usr/bin/env python3

# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import sys

from decimal import Decimal
import os
import io
from xml.etree import ElementTree
import bz2

from benchexec import result
from benchexec import tablegenerator
from benchexec.tablegenerator import util

sys.dont_write_bytecode = True  # prevent creation of .pyc files


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
    for result_tag in witnessXML.findall("run"):
        run = result_tag.get("name")
        witnesses[run] = result_tag
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


def main(argv=None):

    if argv is None:
        argv = sys.argv

    if len(argv) < 3:
        sys.exit(
            "Usage: "
            + argv[0]
            + " <results-xml> [<witness-xml>]* [--no-overwrite-status-true].\n"
        )

    resultFile = argv[1]
    witnessFiles = []
    isOverwrite = True
    for i in range(2, len(argv)):
        if len(argv) > i and not argv[i].startswith("--"):
            witnessFiles.append(argv[i])
        if argv[i] == "--no-overwrite-status-true":
            isOverwrite = False

    if not os.path.exists(resultFile) or not os.path.isfile(resultFile):
        sys.exit("File {0} does not exist.".format(repr(resultFile)))
    resultXML = tablegenerator.parse_results_file(resultFile)
    witnessSets = []
    for witnessFile in witnessFiles:
        if not os.path.exists(witnessFile) or not os.path.isfile(witnessFile):
            sys.exit("File {0} does not exist.".format(repr(witnessFile)))
        witnessXML = tablegenerator.parse_results_file(witnessFile)
        witnessSets.append(getWitnesses(witnessXML))

    for result_tag in resultXML.findall("run"):
        run = result_tag.get("name")
        try:
            status_from_verification = result_tag.find('column[@title="status"]').get(
                "value"
            )
            category_from_verification = result_tag.find(
                'column[@title="category"]'
            ).get("value")
        except AttributeError:
            status_from_verification = "not found"
            category_from_verification = "not found"
        statusWit, categoryWit = (None, None)
        for witnessSet in witnessSets:
            witness = witnessSet.get(run, None)
            # copy data from witness
            if witness is not None and len(witness) > 0:
                if result_tag.get("properties") == "coverage-error-call":
                    status_from_validation = witness.find(
                        'column[@title="status"]'
                    ).get("value")
                    if status_from_validation == "true":
                        statusWit, categoryWit = (status_from_verification, "correct")
                        category_from_verification = "correct"
                        scoreColumn = ElementTree.Element(
                            "column", title="score", value="1"
                        )
                        result_tag.append(scoreColumn)
                elif result_tag.get("properties") == "coverage-branches":
                    try:
                        coverage_value = (
                            witness.find('column[@title="branches_covered"]')
                            .get("value")
                            .replace("%", "")
                        )
                    except AttributeError:
                        coverage_value = "0.00"
                    statusWit, categoryWit = (status_from_verification, "correct")
                    category_from_verification = "correct"
                    try:
                        coverage_percentage = Decimal(coverage_value) / 100
                    except ValueError:
                        continue
                    scoreColumn = ElementTree.Element(
                        "column",
                        title="score",
                        value=util.print_decimal(coverage_percentage),
                    )
                    result_tag.append(scoreColumn)
                else:
                    # For verification
                    if statusWit and statusWit.startswith("witness invalid"):
                        continue
                    statusWitNew, categoryWitNew = getWitnessResult(witness, result_tag)
                    if (
                        categoryWit is None
                        or not categoryWit.startswith(result.CATEGORY_CORRECT)
                        or categoryWitNew == result.CATEGORY_CORRECT
                        or statusWitNew.startswith("witness invalid")
                    ):
                        statusWit, categoryWit = (statusWitNew, categoryWitNew)
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
                result_tag.find('column[@title="status"]').set("value", statusWit)
                result_tag.find('column[@title="category"]').set("value", categoryWit)
            except AttributeError:
                pass
        # Clean-up an entry that can be inferred by table-generator automatically, avoids path confusion
        del result_tag.attrib["logfile"]

    filename = resultFile + ".merged.xml.bz2"
    print("    " + filename)
    with io.TextIOWrapper(bz2.BZ2File(filename, "wb"), encoding="utf-8") as xml_file:
        xml_file.write(
            xml_to_string(resultXML).replace("    \n", "").replace("  \n", "")
        )


if __name__ == "__main__":
    sys.exit(main())
