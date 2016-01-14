<?php

header('Content-Type: text/plain');

# Remove query from URI.
$path = preg_replace("/\?.*/", "", $_SERVER['REQUEST_URI']);
# Example: /2016/results/results-verified/xyz.2016-01-02_2242.logfiles/sv-comp16.standard_find_true-unreach-call_ground.i.log

# Use SCRIPT_FILENAME to get absolute path to this script.
$pathPrefix = preg_replace("/fileservice\.php/", "", $_SERVER['SCRIPT_FILENAME']);
# Example: /srv/web/Org/SV-COMP/2016/results/results-verified/

# Make pathPrefix relative to document root.
$pathPrefix = '/' . preg_replace("/(^" . str_replace('/', '\/', $_SERVER['DOCUMENT_ROOT']) . "|\?.*)/", "", $pathPrefix);
# Example: /2016/results/results-verified/

# Make path relative to pathPrefix.
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

if ($fileName == "") {
  if (!file_exists($zipName)) {
    echo "Error: ZIP file does not exist." . PHP_EOL;
    exit();
  }
  if (!preg_match("\.zip$", $zipName)) {
    echo "Error: File is not a ZIP file." . PHP_EOL;
    exit();
  }
}

$zip = new ZipArchive();
if ($zip->open($zipName) === FALSE) {
  echo "Error: Could not open ZIP file." . PHP_EOL;
  exit();
}

echo $zip->getFromName($fileName);

$zip->close();
?>

