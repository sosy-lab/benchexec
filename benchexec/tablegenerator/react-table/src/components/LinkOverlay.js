// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import ReactModal from "react-modal";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faTimes, faArrowLeft } from "@fortawesome/free-solid-svg-icons";
import { isOkStatus } from "../utils/utils";
import classNames from "classnames";
import path from "path";
import TaskDefinitionViewer from "./TaskDefinitionViewer.js";
import * as zip from "@zip.js/zip.js/dist/zip-no-worker-inflate.min";

zip.configure({
  useWebWorkers: false,
});

const zipEntriesCache = {};

export default class LinkOverlay extends React.Component {
  constructor(props) {
    super(props);
    const isYAML = props.link ? this.isYAMLFile(props.link) : false;
    this.state = {
      isYAML,
      content: `loading file: ${props.link}`,
      currentFile: props.link,
      isSecondLevel: false,
    };
  }

  componentDidMount() {
    this.loadFile(this.props.link);
    window.history.pushState({}, "", "");
    window.addEventListener("popstate", this.props.close, false);
  }

  // Focus modal container when new content is loaded into the modal for accessibility via keyboard
  componentDidUpdate() {
    const modalContainer = document.getElementById("modal-container");
    if (modalContainer) {
      modalContainer.focus();
    }
  }

  componentWillUnmount() {
    window.removeEventListener("popstate", this.props.close, false);
    window.removeEventListener("click", this.props.close, false);
  }

  isYAMLFile(filePath) {
    return filePath.endsWith(".yml");
  }

  loadNewFile = (relativeURL) => {
    const newURL = this.createFileUrl(relativeURL);
    this.setState({
      isYAML: this.isYAMLFile(relativeURL),
      isSecondLevel: true,
      content: `loading file: ${newURL}`,
    });
    this.loadFile(newURL);
  };

  loadOriginalFile = () => {
    this.setState({
      isYAML: this.isYAMLFile(this.props.link),
      isSecondLevel: false,
      content: `loading file: ${this.props.link}`,
      error: undefined,
    });
    this.loadFile(this.props.link);
  };

  loadOriginalFileIfEnter = (e) => {
    if (e.key === "Enter") {
      this.loadOriginalFile();
    }
  };

  createFileUrl = (fileUrl) => path.join(this.props.link, "../" + fileUrl);

  /*
   * Loads the file of the given url. Four different approaches to load the file will be made in case the previous one fails:
   * 1) AJAX request -> fails for ZIP archives
   * 2) HTTP Range request for file in ZIP archive -> fails for ZIPs on the local disk
   * 3) Normal HTTP request for file in ZIP archive -> fails for Google Chrome for ZIPs on the local disk
   * 4) Manually via XMLHttpRequest
   */
  async loadFile(url) {
    if (url) {
      this.setState({ currentFile: url });
      try {
        const response = await fetch(url);
        if (isOkStatus(response.status)) {
          const content = await response.text();
          this.setState({ content });
        } else {
          throw Error(`Received response status ${response.status}`);
        }
      } catch (e) {
        this.loadFileFromZip(url);
      }
    }
  }

  /* Loads the file from a ZIP archive and stores the entries in a cache for faster future access. */
  loadFileFromZip = (url) => {
    const decodedUrl = decodeURIComponent(url);
    const folderSplitterSlash =
      decodedUrl.lastIndexOf("/") > decodedUrl.lastIndexOf("\\") ? "/" : "\\";
    const folderSplitPos = decodedUrl.lastIndexOf(folderSplitterSlash);
    const zipPath = decodedUrl.substring(0, folderSplitPos) + ".zip";
    const splittedUrl = decodedUrl.split(folderSplitterSlash);
    const zipFile = `${splittedUrl[splittedUrl.length - 2]}/${
      splittedUrl[splittedUrl.length - 1]
    }`;

    if (zipPath in zipEntriesCache) {
      this.loadFileFromZipEntries(zipEntriesCache[zipPath], zipFile, zipPath);
    } else {
      this.readZipArchive(zipPath, zipFile);
    }
  };

  /* Tries to read the file from a ZIP archive with a HTTP range request.  */
  readZipArchive = (zipPath, zipFile) => {
    const reader = new zip.ZipReader(new zip.HttpRangeReader(zipPath));
    reader.getEntries().then(
      (entries) => {
        this.handleZipEntries(entries, zipFile, zipPath);
      },
      (error) => {
        if (error.message === zip.ERR_HTTP_RANGE) {
          this.readZipArchiveNoHttpRange(zipPath, zipFile);
        } else {
          this.setError(`HTTP request for the file "${zipFile}" failed`, error);
        }
      },
    );
  };

  /* Tries to read the file from a ZIP archive with a normal HTTP request.  */
  readZipArchiveNoHttpRange = (zipPath, zipFile) => {
    const reader = new zip.ZipReader(new zip.HttpReader(zipPath));
    reader.getEntries().then(
      (entries) => {
        this.handleZipEntries(entries, zipFile, zipPath);
      },
      (error) => {
        this.readZipArchiveManually(zipPath, zipFile);
      },
    );
  };

  /*
   * Loads a file from the zip archive with a HTTP request manually. This should only be necessary
   * for Google Chrome as a HTTP Reader does not work there.
   */
  readZipArchiveManually = (zipPath, zipFile) => {
    try {
      const xhr = new XMLHttpRequest();
      xhr.responseType = "arraybuffer";
      xhr.addEventListener(
        "load",
        () => {
          const array = new Uint8Array(xhr.response);
          const reader = new zip.ZipReader(new zip.Uint8ArrayReader(array));
          reader
            .getEntries()
            .then(
              (entries) => this.handleZipEntries(entries, zipFile, zipPath),
              this.setError,
            );
        },
        false,
      );
      xhr.addEventListener("error", this.setError, false);
      xhr.open("GET", zipPath);
      xhr.send();
    } catch (error) {
      this.setError(`HTTP request for the file "${zipFile}" failed`, error);
    }
  };

  handleZipEntries = (entries, zipFile, zipPath) => {
    zipEntriesCache[zipPath] = entries;
    this.loadFileFromZipEntries(entries, zipFile, zipPath);
  };

  loadFileFromZipEntries = (entries, zipFile, zipPath) => {
    const entry = entries.find((entry) => entry.filename === zipFile);
    if (entry) {
      entry.getData(new zip.TextWriter()).then((content) => {
        this.setState({ content });
      });
    } else {
      this.setError(`Could not find the file "${zipFile}" in "${zipPath}"`);
    }
  };

  /*
   * Sets the error message of the overlay. In case an error object was provided and the
   * error object is a plain string, this error object will be set for the message. Otherwise
   * the simple error message, i.e. the first parameter, will be set.
   */
  setError = (errorMsg, errorObj) => {
    const error =
      errorObj && typeof errorObj === "string" ? errorObj : errorMsg;
    this.setState({ error: `${error}` });
  };

  handlePopState = () => {
    window.history.back();
    window.addEventListener("click", this.props.close, false);
  };

  render() {
    ReactModal.setAppElement(document.getElementById("root"));
    return (
      <ReactModal
        id="modal-container"
        ariaHideApp={false}
        className={classNames("overlay", {
          "second-level": this.state.isSecondLevel,
        })}
        isOpen={true}
        onRequestClose={() => this.handlePopState()}
      >
        <div className="link-overlay-header-container">
          <FontAwesomeIcon
            icon={faTimes}
            onClick={() => this.handlePopState()}
            className="closing"
          />
          {this.state.isSecondLevel ? (
            <span
              className="link-overlay-back-button"
              tabIndex="0"
              role="button"
              onClick={this.loadOriginalFile}
              onKeyDown={this.loadOriginalFileIfEnter}
            >
              <FontAwesomeIcon
                className="link-overlay-back-icon"
                icon={faArrowLeft}
              />
              Back to task definition
            </span>
          ) : (
            ""
          )}
        </div>
        {!this.state.error ? (
          this.state.isYAML ? (
            <TaskDefinitionViewer
              yamlText={this.state.content}
              createHref={this.createFileUrl}
              loadNewFile={this.loadNewFile}
            />
          ) : (
            <pre className="link-overlay-text">{this.state.content}</pre>
          )
        ) : (
          <div className="link-overlay-text">
            <p style={{ marginTop: "0" }}>
              Error while loading content ({this.state.error}).
            </p>
            <p>
              This could be a problem of the{" "}
              <a href="https://en.wikipedia.org/wiki/Same-origin_policy">
                same-origin policy
              </a>{" "}
              of your browser.
            </p>
            {window.location.href.indexOf("file://") === 0 ? (
              <>
                <p>
                  If you are using Chrome or a Chrome-based browser, try
                  launching it with the command-line option{" "}
                  <code>--allow-file-access-from-files</code>.
                </p>
                <p>
                  If you are using Firefox, please open the extended settings by
                  entering <code>about:config</code> in the URL bar, search for{" "}
                  <code>privacy.file_unique_origin</code> and set this option to{" "}
                  <code>false</code> by double-clicking on it (
                  <a href="https://developer.mozilla.org/docs/Web/HTTP/CORS/Errors/CORSRequestNotHttp">
                    more details
                  </a>
                  ). Access to files that are not beneath the same directory as
                  this HTML page is still forbidden.
                </p>
              </>
            ) : null}
            <p>
              You can try to download the file:{" "}
              <a href={this.state.currentFile}>{this.state.currentFile}</a>
            </p>
          </div>
        )}
      </ReactModal>
    );
  }
}
