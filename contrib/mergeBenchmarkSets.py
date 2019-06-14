#!/usr/bin/env python

# BenchExec is a framework for reliable benchmarking.
# This file is part of BenchExec.
#
# Copyright (C) 2007-2017  Dirk Beyer
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import sys

sys.dont_write_bytecode = True  # prevent creation of .pyc files

import os
import io
import xml.etree.ElementTree as ET
import bz2

from benchexec import util
import benchexec.result as Result
import benchexec.tablegenerator as TableGenerator


def xml_to_string(elem, qualified_name=None, public_id=None, system_id=None):
    """
    Return a pretty-printed XML string for the Element.
    Also allows setting a document type.
    """
    from xml.dom import minidom

    rough_string = ET.tostring(elem, "utf-8")
    reparsed = minidom.parseString(rough_string)
    if qualified_name:
        doctype = minidom.DOMImplementation().createDocumentType(
            qualified_name, public_id, system_id
        )
        reparsed.insertBefore(doctype, reparsed.documentElement)
    return reparsed.toprettyxml(indent="  ")


def getWitnesses(witnessXML):
    witnesses = {}
    for result in witnessXML.findall("run"):
        run = result.get("name")
        witnesses[run] = result
    return witnesses


def getWitnessResult(witness, verification_result):

    if witness is None:
        # If there is no witness, then this is an error of the verifier.
        return "witness missing", Result.CATEGORY_ERROR

    # print(witness.get('name'))
    status_from_validation = witness.findall('column[@title="status"]')[0].get("value")
    try:
        status_from_verification = verification_result.findall(
            'column[@title="status"]'
        )[0].get("value")
        category_from_verification = verification_result.findall(
            'column[@title="category"]'
        )[0].get("value")
    except:
        status_from_verification = "not found"
        category_from_verification = "not found"

    # If the result from witness validation matches the result from verification,
    # then leave status and category as is.
    if status_from_validation == status_from_verification:
        return status_from_verification, category_from_verification
    # An invalid witness counts as error of the verifier.
    if status_from_validation == "ERROR (invalid witness file)":
        return (
            "witness invalid (" + status_from_verification + ")",
            Result.CATEGORY_ERROR,
        )
    # Other unconfirmed witnesses count as CATEGORY_CORRECT_UNCONFIRMED.
    if category_from_verification == Result.CATEGORY_CORRECT:
        return status_from_verification, Result.CATEGORY_CORRECT_UNCONFIRMED

    return "result invalid (" + status_from_verification + ")", Result.CATEGORY_ERROR


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
    resultXML = TableGenerator.parse_results_file(resultFile)
    witnessSets = []
    for witnessFile in witnessFiles:
        if not os.path.exists(witnessFile) or not os.path.isfile(witnessFile):
            sys.exit("File {0} does not exist.".format(repr(witnessFile)))
        witnessXML = TableGenerator.parse_results_file(witnessFile)
        witnessSets.append(getWitnesses(witnessXML))

    for result in resultXML.findall("run"):
        run = result.get("name")
        try:
            status_from_verification = result.findall('column[@title="status"]')[0].get(
                "value"
            )
            category_from_verification = result.findall('column[@title="category"]')[
                0
            ].get("value")
        except:
            status_from_verification = "not found"
            category_from_verification = "not found"
        statusWit, categoryWit = (None, None)
        for witnessSet in witnessSets:
            witness = witnessSet.get(run, None)
            # copy data from witness
            if witness is not None:
                if result.get("properties") == "coverage-error-call":
                    status_from_validation = witness.findall('column[@title="status"]')[
                        0
                    ].get("value")
                    if status_from_validation == "true":
                        statusWit, categoryWit = (status_from_verification, "correct")
                        category_from_verification = "correct"
                        scoreColumn = ET.Element(
                            "column", {"title": "score", "value": "1"}
                        )
                        result.append(scoreColumn)
                elif result.get("properties") == "coverage-branches":
                    try:
                        coverage_value = (
                            witness.findall('column[@title="branches_covered"]')[0]
                            .get("value")
                            .replace("%", "")
                        )
                    except IndexError:
                        coverage_value = "0.00"
                    statusWit, categoryWit = (status_from_verification, "correct")
                    category_from_verification = "correct"
                    scoreColumn = ET.Element(
                        "column",
                        {"title": "score", "value": str(float(coverage_value) / 100)},
                    )
                    result.append(scoreColumn)
                else:
                    # For verification
                    statusWitNew, categoryWitNew = getWitnessResult(witness, result)
                    if (
                        categoryWit is None
                        or not categoryWit.startswith(Result.CATEGORY_CORRECT)
                        or categoryWitNew == Result.CATEGORY_CORRECT
                        or statusWitNew.startswith("witness invalid")
                    ):
                        statusWit, categoryWit = (statusWitNew, categoryWitNew)
        # Overwrite status with status from witness
        if (
            (
                isOverwrite
                or Result.RESULT_CLASS_FALSE
                == Result.get_result_classification(status_from_verification)
            )
            and "correct" == category_from_verification
            and statusWit is not None
            and categoryWit is not None
        ):
            # print(run, statusWit, categoryWit)
            try:
                result.findall('column[@title="status"]')[0].set("value", statusWit)
                result.findall('column[@title="category"]')[0].set("value", categoryWit)
            except:
                pass
        # Clean-up an entry that can be inferred by table-generator automatically, avoids path confusion
        del result.attrib["logfile"]

    filename = resultFile + ".merged.xml.bz2"
    print("    " + filename)
    with io.TextIOWrapper(bz2.BZ2File(filename, "wb"), encoding="utf-8") as xml_file:
        xml_file.write(
            xml_to_string(resultXML).replace("    \n", "").replace("  \n", "")
        )


if __name__ == "__main__":
    sys.exit(main())
