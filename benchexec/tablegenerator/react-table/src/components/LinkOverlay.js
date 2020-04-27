/* SPDX-License-Identifier: Apache-2.0
 *
 * BenchExec is a framework for reliable benchmarking.
 * This file is part of BenchExec.
 * Copyright (C) Dirk Beyer. All rights reserved.
 */
import React from "react";
import ReactModal from "react-modal";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faTimes, faArrowLeft } from "@fortawesome/free-solid-svg-icons";
import { isOkStatus } from "../utils/utils";
import zip from "../vendor/zip.js/index.js";
import path from "path";
import TaskDefinitionViewer from "./TaskDefinitionViewer.js";

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
  }

  // Focus modal container when new content is loaded into the modal for accessibility via keyboard
  componentDidUpdate() {
    const modalContainer = document.getElementById("modal-container");
    if (modalContainer) {
      modalContainer.focus();
    }
  }

  isYAMLFile(filePath) {
    return filePath.endsWith(".yml");
  }

  loadNewFile = relativeURL => {
    const newURL = path.join(this.props.link, "../" + relativeURL);
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

  loadOriginalFileIfEnter = e => {
    if (e.key === "Enter") {
      this.loadOriginalFile();
    }
  };

  /*
   * Loads the file of the given url. Four different approaches to load the file will be made in case the previous one fails:
   * 1) AJAX request -> fails for ZIP archives
   * 2) HTTP Range request for file in ZIP archive -> fails for ZIPs on the local disk
   * 3) Normal HTTP request for file in ZIP archive -> fails for Google Chrome for ZIPs on the local disk
   * 4) XML request
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
          this.loadFileFromZip(url);
        }
      } catch (e) {
        this.loadFileFromZip(url);
      }
    }
  }

  /* Loads the file from a ZIP archive and stores the entries in a cache for faster future access. */
  loadFileFromZip(url) {
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
      this.loadFileFromZipEntries(zipEntriesCache[zipPath], zipFile);
    } else {
      this.readZipArchive(zipPath, zipFile, true);
    }
  }

  /*
   * Tries to read the file from a ZIP archive. A flag decides whether to use a HTTP range request for faster access.
   * Automatically tries again with a normal HTTP request in case a HTTP range request is not supported. Tries to load
   * the file via XML in case the HTTP request in general fails.
   */
  readZipArchive(zipPath, zipFile, useHttpRange) {
    const reader = useHttpRange
      ? new zip.HttpRangeReader(zipPath)
      : new zip.HttpReader(zipPath);
    try {
      zip.createReader(
        reader,
        zipReader => this.loadFileFromZipArchive(zipReader, zipFile, zipPath),
        error => {
          if (useHttpRange && error === "HTTP Range not supported.") {
            this.readZipArchive(zipPath, zipFile, false);
          } else if (!useHttpRange) {
            this.loadFileFromZipViaXML(zipPath, zipFile);
          } else {
            const errorMsg =
              typeof error === "string"
                ? error
                : `Could not read the file ${zipFile}`;
            this.setError(errorMsg);
          }
        },
      );
    } catch (error) {
      const errorMsg =
        typeof error === "string"
          ? error
          : "ZIP reader could not be initialized";
      this.setError(errorMsg);
    }
  }

  /* Loads a file from the zip archive via an XML request.
   * This should only be necessary for Google Chrome as a HTTP Reader does not work there.
   */
  loadFileFromZipViaXML(zipPath, zipFile) {
    try {
      const xhr = new XMLHttpRequest();
      xhr.responseType = "arraybuffer";
      xhr.addEventListener(
        "load",
        () => {
          zip.createReader(
            new zip.ArrayBufferReader(xhr.response),
            zipReader =>
              this.loadFileFromZipArchive(zipReader, zipFile, zipPath),
            this.setError,
          );
        },
        false,
      );
      xhr.addEventListener("error", this.setError, false);
      xhr.open("GET", zipPath);
      xhr.send();
    } catch (error) {
      const errorMsg = typeof error === "string" ? error : "XML request failed";
      this.setError(errorMsg);
    }
  }

  loadFileFromZipArchive = (zipReader, zipFile, zipPath) => {
    zipReader.getEntries(entries => {
      zipEntriesCache[zipPath] = entries;
      this.loadFileFromZipEntries(entries, zipFile);
    });
  };

  loadFileFromZipEntries(entries, zipFile) {
    const entry = entries.find(entry => entry.filename === zipFile);
    if (entry) {
      entry.getData(new zip.TextWriter(), content =>
        this.setState({ content }),
      );
    } else {
      this.setError(`Could not find the file "${zipFile}`);
    }
  }

  setError = error => {
    this.setState({ error: `${error}` });
  };

  render() {
    ReactModal.setAppElement(document.getElementById("root"));
    return (
      <ReactModal
        id="modal-container"
        ariaHideApp={false}
        className={`overlay ${this.state.isSecondLevel ? "second-level" : ""}`}
        isOpen={true}
        onRequestClose={this.props.close}
      >
        <div className="link-overlay-header-container">
          <FontAwesomeIcon
            icon={faTimes}
            onClick={this.props.close}
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
                  If you are using Google Chrome, try launching it with a flag
                  --allow-file-access-from-files.
                </p>
                <p>
                  Reading files from within ZIP archives on the local disk does
                  not work with Google Chrome, if the target file is within a
                  ZIP archive you need to extract it.
                </p>
                <p>
                  Firefox can access files from local directories by default,
                  but this does not work for files that are not beneath the same
                  directory as this HTML page.
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
