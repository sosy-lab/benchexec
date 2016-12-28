#!/usr/bin/env python

# BenchExec is a framework for reliable benchmarking.
# This file is part of BenchExec.
#
# Copyright (C) 2007-2016  Dirk Beyer
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
sys.dont_write_bytecode = True # prevent creation of .pyc files

import os
import io
import xml.etree.ElementTree as ET
import bz2

from benchexec import util
import benchexec.tablegenerator as tablegenerator
import benchexec

def xml_to_string(elem, qualified_name=None, public_id=None, system_id=None):
    """
    Return a pretty-printed XML string for the Element.
    Also allows setting a document type.
    """
    from xml.dom import minidom
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    if qualified_name:
        doctype = minidom.DOMImplementation().createDocumentType(
                qualified_name, public_id, system_id)
        reparsed.insertBefore(doctype, reparsed.documentElement)
    return reparsed.toprettyxml(indent="  ")

def getWitnesses(witnessXML):
    witnesses = {}
    for result in witnessXML.findall('run'):
        run = result.get('name')
        witnesses[run] = result
    return witnesses


def getWitnessResult(witness, expected_result):

    if witness is None:
        # If there is no witness, then this is an error of the verifier.
        return ('witness missing', 'error')

    sourcefile = witness.get('name')
    status = witness.findall('column[@title="status"]')[0].get('value')
    category = witness.findall('column[@title="category"]')[0].get('value')

    # remove 's' for seconds and parse time as float
    wallTime = float(witness.findall('column[@title="walltime"]')[0].get('value')[:-1])
    cpuTime = float(witness.findall('column[@title="cputime"]')[0].get('value')[:-1])

    # Unconfirmed witnesses count as 'unknown'.
    if expected_result == False:
        if status.startswith('true') or status.startswith('unknown'):
            return ('witness unconfirmed', 'unknown')
        if max(wallTime, cpuTime) > 90:
            return ('witness timeout', 'unknown')
        if status.startswith('false('):
            return (status, category)
    if expected_result == True:
        if status.startswith('false(') or status.startswith('unknown'):
            return ('witness unconfirmed', 'unknown')
        if max(wallTime, cpuTime) > 900:
            return ('witness timeout', 'unknown')
        if status.startswith('true'):
            return (status, category)
    if status.startswith('OUT OF MEMORY'):
        return ('witness out of memory', 'unknown')

    # An invalid witness counts as error of the verifier.
    return ('witness invalid (' + status + ')', 'error')

def main(argv=None):

    if argv is None:
        argv = sys.argv

    if len(argv) < 3:
        sys.exit('Usage: ' + argv[0] + ' <results-xml> [<witness-xml>]* [--no-overwrite-status].\n')

    resultFile   = argv[1]
    witnessFiles = []
    isOverwrite = True
    for i in range(2, len(argv)):
        if len(argv) > i and not argv[i].startswith('--'):
            witnessFiles.append(argv[i])
        if argv[i] == '--no-overwrite-status':
            isOverwrite = False

    if not os.path.exists(resultFile) or not os.path.isfile(resultFile):
        sys.exit('File {0} does not exist.'.format(repr(resultFile)))
    resultXML   = tablegenerator.parse_results_file(resultFile)
    witnessSets = []
    for witnessFile in witnessFiles:
        if not os.path.exists(witnessFile) or not os.path.isfile(witnessFile):
            sys.exit('File {0} does not exist.'.format(repr(witnessFile)))
        witnessXML = tablegenerator.parse_results_file(witnessFile)
        witnessSets.append(getWitnesses(witnessXML))
        resultXML.set('options', '' + resultXML.get('options', default='') + ' [[ ' + witnessXML.get('options', default='') + ' ]]')
        resultXML.set('date',    '' + resultXML.get('date', default='')    + ' [[ ' + witnessXML.get('date', default='')    + ' ]]')

    for result in resultXML.findall('run'):
        run = result.get('name')
        basename = os.path.basename(run)
        if 'correct' == result.findall('column[@title="category"]')[0].get('value'):
                statusVer   = result.findall('column[@title="status"]')[0]
                categoryVer = result.findall('column[@title="category"]')[0]
                properties = result.get('properties').split(' ');
                expected_result = benchexec.result.satisfies_file_property(basename, properties);

                statusWit, categoryWit = (None, None)
                i = 0
                for witnessSet in witnessSets:
                    i = i + 1
                    witness = witnessSet.get(run, None)
                    # copy data from witness
                    if witness is not None:
                        for column in witness:
                            newColumn = ET.Element('column', {
                                 'title': 'wit' + str(i) + '_' + column.get('title'),
                                 'value':  column.get('value'),
                                 'hidden': column.get('hidden','false')
                                 })
                            result.append(newColumn)
                        witnessSet.pop(run)
                        statusWitNew, categoryWitNew = getWitnessResult(witness, expected_result)
                        if expected_result == False:
                            if statusWitNew.startswith('false(') or statusWit is None:
                                statusWit, categoryWit = (statusWitNew, categoryWitNew)
                        if expected_result == True:
                            if statusWitNew.startswith('true') or statusWit is None:
                                statusWit, categoryWit = (statusWitNew, categoryWitNew)
                # Overwrite status with status from witness
                if isOverwrite and statusWit is not None and categoryWit is not None:
                    result.findall('column[@title="status"]')[0].set('value', statusWit)
                    result.findall('column[@title="category"]')[0].set('value', categoryWit)
        # Clean-up an entry that can be inferred by table-generator automatically, avoids path confusion
        del result.attrib['logfile']

    filename = resultFile + '.merged.xml.bz2'
    print ('    ' + filename)
    open_func = bz2.BZ2File if hasattr(bz2.BZ2File, 'writable') else util.BZ2FileHack
    with io.TextIOWrapper(open_func(filename, 'wb'), encoding='utf-8') as xml_file:
        xml_file.write(xml_to_string(resultXML).replace('    \n','').replace('  \n',''))

if __name__ == '__main__':
    sys.exit(main())
