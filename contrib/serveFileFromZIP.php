<?php

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


function handleError($message) {
  header('HTTP/1.0 404 Not Found');
  echo '<html>' . PHP_EOL;
  echo '<body>' . PHP_EOL;
  echo '<h1>Error 404: Not Found</h1>' . PHP_EOL;
  echo '<p>' . $message . '</p>' . PHP_EOL;
  echo '</body>' . PHP_EOL;
  echo '</html>' . PHP_EOL;
  exit();
}

# Remove query from URI.
$path = preg_replace("/\?.*/", "", $_SERVER['REQUEST_URI']);
# Example: /2016/results/results-verified/xyz.2016-01-02_2242.logfiles/sv-comp16.standard_find_true-unreach-call_ground.i.log

# Use SCRIPT_FILENAME to get absolute path to this script.
$pathPrefix = preg_replace("/serveFileFromZIP\.php/", "", $_SERVER['SCRIPT_FILENAME']);
# Example: /srv/web/Org/SV-COMP/2016/results/results-verified/

# Make $pathPrefix relative to document root.
$pathPrefix = '/' . preg_replace("/(^" . str_replace('/', '\/', $_SERVER['DOCUMENT_ROOT']) . "|\?.*)/", "", $pathPrefix);
# Example: /2016/results/results-verified/

# Make $path relative to pathPrefix.
$path = preg_replace("/(^" . str_replace('/', '\/', $pathPrefix) . "|\?.*)/", "", $path);
# Example: xyz.2016-01-02_2242.logfiles/sv-comp16.standard_find_true-unreach-call_ground.i.log

# Split $path into a prefix $zipName and suffix $fileName
# such that $zipName is refering to a zip file and $fileName is a file inside the zip file.
$zipName  = ".";
$fileName = ".";
$isBeforeZip = true;
foreach (explode("/", $path) as $pathComponent) {
  if ($isBeforeZip && file_exists($zipName . "/" . $pathComponent)) {
    $zipName .= "/" . $pathComponent;
  } else {
    $isBeforeZip = false;
    if (file_exists($zipName . "/" . $pathComponent . ".zip")) {
      $zipName = $zipName . "/" . $pathComponent . ".zip";
    }
    $fileName .= "/" . $pathComponent;
  }
}
$zipName = preg_replace("/^\.\//", "", $zipName);
# Example: xyz.2016-01-02_2242.logfiles.zip

$fileName = preg_replace("/^\.\//", "", $fileName);
# Example: xyz.2016-01-02_2242.logfiles/sv-comp16.standard_find_true-unreach-call_ground.i.log

#echo $zipName  . PHP_EOL;
#echo $fileName . PHP_EOL;

if ( !preg_match("/\.zip$/", $zipName) || !file_exists($zipName) ) {
  handleError("Error: ZIP file not found (tried '$zipName').");
}
$zip = new ZipArchive();
if ($zip->open($zipName) !== TRUE) {
  handleError("Error: Could not open ZIP file '$zipName'.");
}
$contents = $zip->getFromName($fileName);
$zip->close();
if ($contents === FALSE) {
  handleError("Error: Could not find file '$fileName' in ZIP file '$zipName'.");
}
$fileSize = strlen($contents);
$fileName = preg_replace("/.*\//", "", $fileName);
header('Content-Description: File Download from ZIP File');
header("Content-Disposition: attachment; filename=$fileName");
header('Content-Type: text/plain');
header('Content-Length: ' . $fileSize);
echo $contents;
?>
