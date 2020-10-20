// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import yamlParser from "yaml";

/** Special view for YAML files in the LinkOverlay component. */
export default class TaskDefinitionViewer extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      splitterTag: "<splitter#9d81y23>",
      fileTag: "<file#092nt43>",
      content: this.props.yamlText,
    };
  }

  componentDidMount() {
    this.prepareTextForRendering();
  }

  componentDidUpdate(prevProps) {
    if (prevProps.yamlText !== this.props.yamlText) {
      this.prepareTextForRendering();
    }
  }

  /**
   * Parses the YAML file and encloses all input and property files with a fileTag as well as a splitterTag,
   * so they can be rendered separately as links. Takes the following assumptions:
   * input_files is either a string or a list of strings
   * properties is a list of dicts, each with a "property_file" key
   */
  prepareTextForRendering = () => {
    if (this.props.yamlText !== "") {
      const yamlObj = yamlParser.parseDocument(this.props.yamlText);

      const inputFiles = yamlObj.get("input_files");
      if (inputFiles) {
        if (Array.isArray(inputFiles.items)) {
          inputFiles.items.forEach((inputFileItem) => {
            inputFileItem.value = this.encloseFileInTags(inputFileItem.value);
          });
        } else {
          yamlObj.set("input_files", this.encloseFileInTags(inputFiles));
        }
      }

      const properties = yamlObj.get("properties");
      if (properties) {
        if (Array.isArray(properties.items)) {
          properties.items.forEach((property) => {
            if (Array.isArray(property.items)) {
              property.items.forEach((propertyItem) => {
                if (propertyItem.key.value === "property_file") {
                  propertyItem.value.value = this.encloseFileInTags(
                    propertyItem.value.value,
                  );
                }
              });
            }
          });
        }
      }

      this.setState({ content: yamlObj.toString() });
    }
  };

  encloseFileInTags = (fileName) => {
    return (
      this.state.splitterTag +
      this.state.fileTag +
      fileName +
      this.state.fileTag +
      this.state.splitterTag
    );
  };

  loadFileInViewer = (event, contentPart) => {
    event.preventDefault();
    this.props.loadNewFile(contentPart);
  };

  render() {
    const contentBySplitter = this.state.content.split(this.state.splitterTag);
    const jsxContent = contentBySplitter.map((contentPart) => {
      // If contentPart is enclosed with file tags (= if contentPart is a file which should be linked)
      if (
        contentPart.match(`^${this.state.fileTag}(?:.)+${this.state.fileTag}$`)
      ) {
        contentPart = contentPart.replace(
          new RegExp(this.state.fileTag, "g"),
          "",
        );
        return (
          /* Custom onClick disables the default behavior of an <a> tag to load a new page and instead loads
             the file in the same LinkOverlay. At the same time other benefits from <a> tags such as downloading
             or opening in a new tab are preserved, because they don't affect the onClick event. */
          <a
            onClick={(e) => this.loadFileInViewer(e, contentPart)}
            className="link-overlay-file-link"
            key={contentPart}
            href={this.props.createHref(contentPart)}
          >
            {contentPart}
          </a>
        );
      } else {
        return contentPart;
      }
    });

    return <pre className="link-overlay-text">{jsxContent}</pre>;
  }
}
