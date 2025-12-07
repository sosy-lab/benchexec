// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import ReactModal from "react-modal";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faClose, faArrowLeft } from "@fortawesome/free-solid-svg-icons";
import {
  CopyableNode,
  isOkStatus,
  splitUrlPathForMatchingPrefix,
} from "../utils/utils";
import classNames from "classnames";
// @ts-expect-error TS(7016): Could not find a declaration file for module 'path... Remove this comment to see the full error message
import path from "path-browserify";
import TaskDefinitionViewer from "./TaskDefinitionViewer.js";
// @ts-expect-error TS(7016): Could not find a declaration file for module '@zip... Remove this comment to see the full error message
import * as zip from "@zip.js/zip.js/lib/zip-no-worker-inflate";

zip.configure({
  useWebWorkers: false,
});

const zipEntriesCache = {};

export default class LinkOverlay extends React.Component {
  constructor(props: any) {
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
    // @ts-expect-error TS(2339): Property 'link' does not exist on type 'Readonly<{... Remove this comment to see the full error message
    this.loadFile(this.props.link);
    window.history.pushState({}, "", "");
    // @ts-expect-error TS(2339): Property 'close' does not exist on type 'Readonly<... Remove this comment to see the full error message
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
    // @ts-expect-error TS(2339): Property 'close' does not exist on type 'Readonly<... Remove this comment to see the full error message
    window.removeEventListener("popstate", this.props.close, false);
    // @ts-expect-error TS(2339): Property 'close' does not exist on type 'Readonly<... Remove this comment to see the full error message
    window.removeEventListener("click", this.props.close, false);
  }

  isYAMLFile(filePath: any) {
    return filePath.endsWith(".yml");
  }

  loadNewFile = (relativeURL: any) => {
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
      // @ts-expect-error TS(2339): Property 'link' does not exist on type 'Readonly<{... Remove this comment to see the full error message
      isYAML: this.isYAMLFile(this.props.link),
      isSecondLevel: false,
      // @ts-expect-error TS(2339): Property 'link' does not exist on type 'Readonly<{... Remove this comment to see the full error message
      content: `loading file: ${this.props.link}`,
      error: undefined,
    });
    // @ts-expect-error TS(2339): Property 'link' does not exist on type 'Readonly<{... Remove this comment to see the full error message
    this.loadFile(this.props.link);
  };

  loadOriginalFileIfEnter = (e: any) => {
    if (e.key === "Enter") {
      this.loadOriginalFile();
    }
  };

  // @ts-expect-error TS(2339): Property 'link' does not exist on type 'Readonly<{... Remove this comment to see the full error message
  createFileUrl = (fileUrl: any) => path.join(this.props.link, "../" + fileUrl);

  /*
   * Loads the file of the given url. Four different approaches to load the file will be made in case the previous one fails:
   * 1) AJAX request -> fails for ZIP archives
   * 2) HTTP Range request for file in ZIP archive -> fails for ZIPs on the local disk
   * 3) Normal HTTP request for file in ZIP archive -> fails for Google Chrome for ZIPs on the local disk
   * 4) Manually via XMLHttpRequest
   *
   * In principle, we would like to use loadFileFetch.
   * However, in Chrome the parameter --allow-file-access-from-files
   * does not affect fetch requests, only XMLHttpRequest.
   * So we need to use the latter for now.
   */
  loadFile = this.loadFileXMLHttpRequest;

  async loadFileFetch(url: any) {
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

  loadFileXMLHttpRequest(url: any) {
    if (url) {
      try {
        this.setState({ currentFile: url });
        const xhr = new XMLHttpRequest();
        xhr.addEventListener("load", () => {
          if (isOkStatus(xhr.status)) {
            const content = xhr.responseText;
            this.setState({ content });
          } else {
            this.loadFileFromZip(url);
          }
        });
        xhr.addEventListener("error", () => this.loadFileFromZip(url));
        xhr.open("GET", url);
        xhr.send();
      } catch (e) {
        this.loadFileFromZip(url);
      }
    }
  }

  /* Loads the file from a ZIP archive and stores the entries in a cache for faster future access. */
  loadFileFromZip = (url: any) => {
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
      // @ts-expect-error TS(7053): Element implicitly has an 'any' type because expre... Remove this comment to see the full error message
      this.loadFileFromZipEntries(zipEntriesCache[zipPath], zipFile, zipPath);
    } else {
      this.readZipArchive(zipPath, zipFile);
    }
  };

  /* Tries to read the file from a ZIP archive with a HTTP range request.  */
  readZipArchive = (zipPath: any, zipFile: any) => {
    const reader = new zip.ZipReader(new zip.HttpRangeReader(zipPath));
    reader.getEntries().then(
      (entries: any) => {
        this.handleZipEntries(entries, zipFile, zipPath);
      },
      // @ts-expect-error TS(6133): 'error' is declared but its value is never read.
      (error: any) => {
        this.readZipArchiveNoHttpRange(zipPath, zipFile);
      },
    );
  };

  /* Tries to read the file from a ZIP archive with a normal HTTP request.  */
  readZipArchiveNoHttpRange = (zipPath: any, zipFile: any) => {
    const reader = new zip.ZipReader(new zip.HttpReader(zipPath));
    reader.getEntries().then(
      (entries: any) => {
        this.handleZipEntries(entries, zipFile, zipPath);
      },
      // @ts-expect-error TS(6133): 'error' is declared but its value is never read.
      (error: any) => {
        this.readZipArchiveManually(zipPath, zipFile);
      },
    );
  };

  /*
   * Loads a file from the zip archive with a HTTP request manually. This should only be necessary
   * for Google Chrome as a HTTP Reader does not work there.
   */
  readZipArchiveManually = (zipPath: any, zipFile: any) => {
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
              (entries: any) =>
                this.handleZipEntries(entries, zipFile, zipPath),
              this.setError,
            );
        },
        false,
      );
      // @ts-expect-error TS(2769): No overload matches this call.
      xhr.addEventListener("error", this.setError, false);
      xhr.open("GET", zipPath);
      xhr.send();
    } catch (error) {
      this.setError(`HTTP request for the file "${zipFile}" failed`, error);
    }
  };

  handleZipEntries = (entries: any, zipFile: any, zipPath: any) => {
    // @ts-expect-error TS(7053): Element implicitly has an 'any' type because expre... Remove this comment to see the full error message
    zipEntriesCache[zipPath] = entries;
    this.loadFileFromZipEntries(entries, zipFile, zipPath);
  };

  loadFileFromZipEntries = (entries: any, zipFile: any, zipPath: any) => {
    const entry = entries.find((entry: any) => entry.filename === zipFile);
    if (entry) {
      entry.getData(new zip.TextWriter()).then((content: any) => {
        this.setState({ content });
      });
    } else {
      // @ts-expect-error TS(2554): Expected 2 arguments, but got 1.
      this.setError(`Could not find the file "${zipFile}" in "${zipPath}"`);
    }
  };

  /*
   * Sets the error message of the overlay. In case an error object was provided and the
   * error object is a plain string, this error object will be set for the message. Otherwise
   * the simple error message, i.e. the first parameter, will be set.
   */
  setError = (errorMsg: any, errorObj: any) => {
    const error =
      errorObj && typeof errorObj === "string" ? errorObj : errorMsg;
    this.setState({ error: `${error}` });
  };

  handlePopState = () => {
    window.history.back();
    // @ts-expect-error TS(2339): Property 'close' does not exist on type 'Readonly<... Remove this comment to see the full error message
    window.addEventListener("click", this.props.close, false);
  };

  renderHelpMessageForLocalLogs = () => {
    if (window.location.protocol !== "file:") {
      return null; // not relevant
    }

    const browserSettingsMessage = (
      <>
        <p>
          If you are using <strong>Chrome</strong> or a Chrome-based browser,
          try launching it with the command-line option{" "}
          <strong>
            <code>--allow-file-access-from-files</code>
          </strong>
          .
        </p>
        <p>
          If you are using <strong>Firefox</strong>, please open the extended
          settings by entering <code>about:config</code> in the URL bar, search
          for{" "}
          <strong>
            <code>security.fileuri.strict_origin_policy</code>
          </strong>{" "}
          and set this option to <code>false</code> by double-clicking on it and
          restart your browser (
          <a href="https://kb.mozillazine.org/Security.fileuri.strict_origin_policy">
            more details
          </a>
          ).
        </p>
        <p>
          <strong>
            Note that these settings will allow local web pages to access all of
            your files, so make sure to not open any untrusted local HTML
            documents.
          </strong>
        </p>
      </>
    );

    // Users can also start a local HTTP server, and we want to explain this
    // and generate the necessary command for them such that this is easy.
    // We need the base directory of the HTTP server (document root)
    // that should contain both the table and the result files.
    // @ts-expect-error TS(2339): Property 'currentFile' does not exist on type 'Rea... Remove this comment to see the full error message
    const absCurrentFile = new URL(this.state.currentFile, document.baseURI);
    let [baseDir, pathSuffix] = splitUrlPathForMatchingPrefix(
      window.location,
      absCurrentFile,
    );

    // There are three known path variants:
    // Unix: looks like: /home/...
    // Regular Windows: looks like /C:/Users/...
    // Network share on Windows (including WSL): looks like //host/dir/...
    // For regular Windows path, we need to remove the leading slash,
    // and if the partitions differ there is no possible base directory,
    // so we give up.
    if (window.location.pathname[2] === ":") {
      // Very likely we are on Windows.
      if (baseDir) {
        if (baseDir[0] === "/") {
          baseDir = baseDir.substring(1);
        }
      } else {
        // Table and logs are on different partitions, we have no chance
        // of providing a working command line.
        return (
          <>
            {browserSettingsMessage}
            <p>
              Alternatively, you can start a local web server serving the
              directories with the tables and result files, but for doing so you
              first need to make sure that table and result files are on the
              same partition.
            </p>
          </>
        );
      }
    }

    const ip = "127.0.0.1";
    const port = 8000;
    const url = `http://${ip}:${port}/${pathSuffix}${window.location.hash}`;
    return (
      <>
        {browserSettingsMessage}
        <p>
          Alternatively, you can start a local web server serving the
          directories with the tables and result files.
          <br />
          To do so, execute the following command and then open{" "}
          <a href={url}>this link</a> (adjust the port number {port} if it is
          already used on your system):
          <br />
          <CopyableNode>
            <code>
              python3 -m http.server -b {ip} {port} -d {baseDir || "/"}
            </code>
          </CopyableNode>
        </p>
      </>
    );
  };

  render() {
    // @ts-expect-error TS(2345): Argument of type 'HTMLElement | null' is not assig... Remove this comment to see the full error message
    ReactModal.setAppElement(document.getElementById("root"));
    return (
      <ReactModal
        id="modal-container"
        ariaHideApp={false}
        className={classNames("overlay", {
          // @ts-expect-error TS(2339): Property 'isSecondLevel' does not exist on type 'R... Remove this comment to see the full error message
          "second-level": this.state.isSecondLevel,
        })}
        isOpen={true}
        onRequestClose={() => this.handlePopState()}
      >
        <div className="link-overlay-header-container">
          <FontAwesomeIcon
            icon={faClose}
            onClick={() => this.handlePopState()}
            className="closing"
          />
          // @ts-expect-error TS(2339): Property 'isSecondLevel' does not exist on type 'R... Remove this comment to see the full error message
          {this.state.isSecondLevel ? (
            <span
              className="link-overlay-back-button"
              // @ts-expect-error TS(2322): Type 'string' is not assignable to type 'number'.
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
        // @ts-expect-error TS(2339): Property 'error' does not exist on type 'Readonly<... Remove this comment to see the full error message
        {!this.state.error ? (
          // @ts-expect-error TS(2339): Property 'isYAML' does not exist on type 'Readonly... Remove this comment to see the full error message
          this.state.isYAML ? (
            <TaskDefinitionViewer
              // @ts-expect-error TS(2322): Type '{ yamlText: any; createHref: (fileUrl: any) ... Remove this comment to see the full error message
              yamlText={this.state.content}
              createHref={this.createFileUrl}
              loadNewFile={this.loadNewFile}
            />
          ) : (
            // @ts-expect-error TS(2339): Property 'content' does not exist on type 'Readonl... Remove this comment to see the full error message
            <pre className="link-overlay-text">{this.state.content}</pre>
          )
        ) : (
          <div className="link-overlay-text">
            <p style={{ marginTop: "0" }}>
              // @ts-expect-error TS(2339): Property 'error' does not exist on type 'Readonly<... Remove this comment to see the full error message
              Error while loading content ({this.state.error}).
            </p>
            <p>
              This could be a problem of the{" "}
              <a href="https://en.wikipedia.org/wiki/Same-origin_policy">
                same-origin policy
              </a>{" "}
              of your browser.
            </p>
            {this.renderHelpMessageForLocalLogs()}
            <p>
              You can also try to download the file:{" "}
              // @ts-expect-error TS(2339): Property 'currentFile' does not exist on type 'Rea... Remove this comment to see the full error message
              <a href={this.state.currentFile}>{this.state.currentFile}</a>
            </p>
          </div>
        )}
      </ReactModal>
    );
  }
}
