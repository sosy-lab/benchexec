<?php

// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

/*
 * This script serves files included in ZIP archives transparently to the client.
 * For example, if the client requests /foo/bar/file.txt and this request
 * gets handled by this script,
 * it checks whether an archive /foo/bar.zip with a contained file bar/file.txt
 * or an archive /foo.zip with a contained file foo/bar/file.txt exists
 * and serves the content of this file.
 *
 * This can be used for BenchExec's log-file archives.
 * To use it on an Apache server,
 * put this script in your results directory or a directory above it,
 * and insert the following in the ".htaccess" file in the same directory:
 *
 * This file is maintained at
 * https://github.com/sosy-lab/benchexec/blob/main/contrib/serveFileFromZIP.php

RewriteEngine On
# Only redirect if target does not exist as file or directory
RewriteCond %{DOCUMENT_ROOT}/%{REQUEST_URI} !-f
RewriteCond %{DOCUMENT_ROOT}/%{REQUEST_URI} !-d
# If Apache has option MultiViews set it rewrites the URL to include ".zip",
# so we match both
RewriteRule ^.*\.logfiles(\.zip)?/.* serveFileFromZIP.php

 * This requires mod_rewrite and the permission to configure it from ".htaccess"
 * (given with "AllowOverride FileInfo" in the server config).
 * Alternatively, you can also put this rewrite rule directly into your server config,
 * but you probably need to adjust the path to the PHP script.
 *
 * TODO: Currently this script always sets Content-Type "text/plain".
 */

// CONFIGURATION
// Base directory for the files to be served, only necessary if files are not
// inside the server's document root:
$baseDir = "";
// Path segments to skip at the beginning of the URL before appending it to
// $baseDir:
$skipUrlSegments = 0;

// ---------------------------------------------------------------------------

/* Send error 404 to client. */
function handleError($message) {
  header('HTTP/1.1 404 Not Found');
  ?>
    <html><head>
    <title>404 Not Found</title>
    </head><body>
    <h1>Not Found</h1>
    <p><?php echo $message;?>.</p>
    </body></html>
  <?php
  exit();
}

function strEndsWith($str, $end) {
  return substr_compare($str, $end, -strlen($end)) === 0;
}

/* Read a file from a ZIP archive and send content to client. */
function serveFileFromZIP($baseDir, $zipName, $fileName) {
  $zip = new ZipArchive();
  if ($zip->open($baseDir . $zipName) !== TRUE) {
    handleError("Could not open ZIP file '$zipName'");
  }

  $contents = $zip->getStream($fileName);
  if ($contents === FALSE) {
    $zip->close();
    handleError("Could not find file '$fileName' in ZIP file '$zipName'");
  }

  $fileSize = $zip->statName($fileName)['size'];
  header('Content-Length: ' . $fileSize);
  $contentType = "text/plain";
  if (strEndsWith($fileName, ".graphml")) {
    $contentType = "text/xml";
  }
  header('Content-Type: ' . $contentType);

  fpassthru($contents);
  fclose($contents);
  $zip->close();
  exit();
}

# Remove query from URI (and decode URI), example: /foo/bar/file.txt
$path = urldecode(preg_replace("/\?.*/", "", $_SERVER['REQUEST_URI']));

# Parts of path, example: ["foo", "bar", "file.txt"]
$parts = array_slice(explode("/", ltrim($path, "/")), $skipUrlSegments);

# Base directory (document root), example: /var/www/
if ($baseDir == "") {
  $baseDir = $_SERVER['DOCUMENT_ROOT'];
}
$baseDir = rtrim($baseDir, "/") . "/";

# Iterate backwards through $parts,
# check if archive with name $parts[0,...,$i-1] exists
# and serve file $parts[$i-1,...] from it.
for ($i = count($parts)-1; $i > 0; $i--) {
  $dirName = implode("/", array_slice($parts, 0, $i));
  $fileName = implode("/", array_slice($parts, $i-1));
  $zipName = $dirName . ".zip";

  if (file_exists($baseDir . $dirName)) {
    # Abort if we have found a path component that exists.
    handleError("The requested URL '$path' was not found on this server");
  }

  if (file_exists($baseDir . $zipName)) {
    serveFileFromZIP($baseDir, $zipName, $fileName);
  }
}

handleError("The requested URL '$path' was not found on this server");
?>
