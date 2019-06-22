function loadContent(url) {
  var contentPane = $('<pre id="content"></pre>').appendTo("#contentPane")
  function writeToContentPane(text) {
    debug(text);
    newtext = text.replace(/&/g, "&amp;")
                  .replace(/"/g, "&quot;")
                  .replace(/</g, "&lt;")
                  .replace(/>/g, "&gt;");
    contentPane.html(newtext);
  }

  function giveUp(error) {
    var _contentPane = $('#contentPane');
    _contentPane.html("Error while loading content (" + error + ").<br>" +
      "This could be a problem of the <a href='https://en.wikipedia.org/wiki/Same-origin_policy'>same-origin policy</a> of your browser.<br><br>");
    if (window.location.href.indexOf("file://") == 0) {
      _contentPane.append(
        "If you are using Google Chrome, try launching it with a flag --allow-file-access-from-files.<br>" +
        "Reading files from within ZIP archives on the local disk does not work with Google Chrome,<br>" +
        "if the target file is within a ZIP archive you need to extract it.<br><br>" +
        "Firefox can access files from local directories by default,<br>" +
        "but this does not work for files that are not beneath the same directory as this HTML page.<br><br>");
    }
    _contentPane.append("You can try to download the file: <a href=" + url + ">" + url + "</a>");
  }

  showContentPane();
  writeToContentPane("Loading file " + url);

  // 1) Try loading url with normal Ajax request for uncompressed results.
  // 2) Try loading url from within ZIP archive using HTTP Range header for efficient access
  //    (this fails for ZIPs on the local disk).
  // 3) Try loading url from within ZIP archive without Range header.

  function attemptLoadingFromZIP() {
    var splitPos = url.lastIndexOf('/');
    var zipUrl = url.substring(0, splitPos) + ".zip";
    var logfile = decodeURIComponent(url.substring(splitPos));

    function loadFileFromZipEntries(entries) {
      for (var i = 0; i < entries.length; i++) {
        if (entries[i].filename.indexOf(logfile) >= 0) {
          entries[i].getData(new zip.TextWriter(), writeToContentPane);
          return;
        }
      }
      giveUp('did not find file "' + logfile.substring(1) + '" in "' + zipUrl + '"');
    }

    function loadFileFromZip(logZip) {
      logZip.getEntries(function(entries) {
        cachedZipFileEntries[zipUrl] = entries;
        loadFileFromZipEntries(entries);
      });
    }

    function attemptLoadingZIPManually() {
      var xhr = new XMLHttpRequest();
      xhr.responseType = 'arraybuffer';
      xhr.addEventListener("load", function() {
          zip.createReader(new zip.ArrayBufferReader(xhr.response), loadFileFromZip, giveUp);
        }, false);
      xhr.addEventListener("error", giveUp, false);
      xhr.open('GET', zipUrl);
      xhr.send();
    }

    writeToContentPane('Loading file "' + logfile.substring(1) + '" from ZIP archive "' + zipUrl + '"');
    if (zipUrl in cachedZipFileEntries) {
      loadFileFromZipEntries(cachedZipFileEntries[zipUrl]);
    } else {
      try {
        zip.createReader(new zip.HttpRangeReader(zipUrl), loadFileFromZip,
          function(error) {
            if (error == "HTTP Range not supported.") {
              // try again without HTTP Range header
              writeToContentPane('Loading file "' + logfile.substring(1) + '" from ZIP archive "' + zipUrl + '" without using HTTP Range header.');
              // Try with HttpReader, but this fails in Chrome for local files,
              // so fall back to a manual XMLHttpRequest.
              zip.createReader(new zip.HttpReader(zipUrl), loadFileFromZip, attemptLoadingZIPManually);
            } else {
              giveUp(error);
            }
          });
      } catch (ex) {
        debug(ex);
        giveUp(ex.message);
      }
    }
  }

  $.ajax({ url: url, dataType: "text" })
    .done(writeToContentPane)
    .fail(function(jqXHR, textStatus, errorThrown) {
            debug(errorThrown);
          })
    .fail(attemptLoadingFromZIP);
}