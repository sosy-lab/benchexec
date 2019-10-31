/* SPDX-License-Identifier: Apache-2.0
 *
 * BenchExec is a framework for reliable benchmarking.
 * This file is part of BenchExec.
 * Copyright (C) Dirk Beyer. All rights reserved.
 */
import React from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faTimes } from "@fortawesome/free-solid-svg-icons";
import JSZip from "jszip";
import { isOkStatus } from "../utils/utils";

export default class LinkOverlay extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      content: `loading file: ${this.props.link}`
    };
    this.cachedZipFileEntries = {};

    this.loadContent(this.props.link);
  }

  loadContent = async url => {
    console.log("load content", url);
    if (url) {
      try {
        const response = await fetch(url);
        //status 404/403 => error?
        if (isOkStatus(response.status)) {
          try {
            const content = await response.text();
            this.setState({ content });
          } catch (e) {
            console.log("Error: Stream not readable", url, e);
            this.attemptLoadingFromZIP(url);
          }
        } else {
          console.log("Error: Loading file not possible", response);
          this.attemptLoadingFromZIP(url);
        }
      } catch (e) {
        console.log("Error: Resource not found", url, e);
        this.attemptLoadingFromZIP(url);
      }
    }
  };

  attemptLoadingFromZIP = async url => {
    console.log("Text is not received. Try as zip?", url);
    const splitPos = url.lastIndexOf("/");
    const zipUrl = url.substring(0, splitPos) + ".zip";
    const urlArray = url.split("/");
    const logfile = decodeURIComponent(
      `${urlArray[urlArray.length - 2]}/${urlArray[urlArray.length - 1]}`
    ); // <folder>/<logfile>

    const response = await fetch(zipUrl);
    const { status, statusText } = response;
    if (isOkStatus(status)) {
      try {
        const data = await response.blob();
        const zip = await JSZip.loadAsync(data);

        const fileContent = await zip.file(logfile).async("string");

        this.setState({ content: fileContent });
      } catch (error) {
        console.log("ERROR receiving ZIP", error);
        this.setState({ error: `${error}` });
      }
    } else {
      throw new Error(statusText);
    }
  };

  escFunction = event => {
    if (event.keyCode === 27) {
      this.props.close();
    }
  };
  componentDidMount = () => {
    document.addEventListener("keydown", this.escFunction, false);
  };
  componentWillUnmount = () => {
    document.removeEventListener("keydown", this.escFunction, false);
  };

  render() {
    return (
      <div className="overlay">
        <FontAwesomeIcon
          icon={faTimes}
          onClick={this.props.close}
          className="closing"
        />
        {!this.state.error ? (
          <>
            <pre>{this.state.content}</pre>
            <input />
          </>
        ) : (
          <div>
            <p>Error while loading content ({this.state.error}).</p>
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
              <a href={this.props.link}>{this.props.link}</a>
            </p>
          </div>
        )}
      </div>
    );
  }
}
