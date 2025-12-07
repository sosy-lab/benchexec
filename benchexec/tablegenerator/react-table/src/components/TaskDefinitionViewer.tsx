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
  constructor(props: any) {
    super(props);
    this.state = {
      splitterTag: "<splitter#9d81y23>",
      fileTag: "<file#092nt43>",
      // @ts-expect-error TS(2339): Property 'yamlText' does not exist on type 'Readon... Remove this comment to see the full error message
      content: this.props.yamlText,
    };
  }

  componentDidMount() {
    this.prepareTextForRendering();
  }

  componentDidUpdate(prevProps: any) {
    // @ts-expect-error TS(2339): Property 'yamlText' does not exist on type 'Readon... Remove this comment to see the full error message
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
    // @ts-expect-error TS(2339): Property 'yamlText' does not exist on type 'Readon... Remove this comment to see the full error message
    if (this.props.yamlText !== "") {
      // @ts-expect-error TS(2339): Property 'yamlText' does not exist on type 'Readon... Remove this comment to see the full error message
      const yamlObj = yamlParser.parseDocument(this.props.yamlText, {
        prettyErrors: true,
      });

      const inputFiles = yamlObj.get("input_files");
      if (inputFiles) {
        if (Array.isArray(inputFiles.items)) {
          inputFiles.items.forEach((inputFileItem: any) => {
            inputFileItem.value = this.encloseFileInTags(inputFileItem.value);
          });
        } else {
          yamlObj.set("input_files", this.encloseFileInTags(inputFiles));
        }
      }

      const properties = yamlObj.get("properties");
      if (properties) {
        if (Array.isArray(properties.items)) {
          properties.items.forEach((property: any) => {
            if (Array.isArray(property.items)) {
              property.items.forEach((propertyItem: any) => {
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

      this.setState({ content: yamlObj });
    }
  };

  encloseFileInTags = (fileName: any) => {
    return (
      // @ts-expect-error TS(2339): Property 'splitterTag' does not exist on type 'Rea... Remove this comment to see the full error message
      this.state.splitterTag +
      // @ts-expect-error TS(2339): Property 'fileTag' does not exist on type 'Readonl... Remove this comment to see the full error message
      this.state.fileTag +
      fileName +
      // @ts-expect-error TS(2339): Property 'fileTag' does not exist on type 'Readonl... Remove this comment to see the full error message
      this.state.fileTag +
      // @ts-expect-error TS(2339): Property 'splitterTag' does not exist on type 'Rea... Remove this comment to see the full error message
      this.state.splitterTag
    );
  };

  loadFileInViewer = (event: any, contentPart: any) => {
    event.preventDefault();
    // @ts-expect-error TS(2339): Property 'loadNewFile' does not exist on type 'Rea... Remove this comment to see the full error message
    this.props.loadNewFile(contentPart);
  };

  render() {
    // @ts-expect-error TS(2339): Property 'content' does not exist on type 'Readonl... Remove this comment to see the full error message
    if (this.state.content.errors && this.state.content.errors.length > 0) {
      return (
        <>
          <div className="link-overlay-text">
            Errors parsing YAML file:
            <ul>
              // @ts-expect-error TS(2339): Property 'content' does not exist on
              type 'Readonl... Remove this comment to see the full error message
              {this.state.content.errors.map((err: any, i: any) => (
                <li key={i}>
                  <pre>{err.message}</pre>
                </li>
              ))}
            </ul>
            // @ts-expect-error TS(2339): Property 'yamlText' does not exist on
            type 'Readon... Remove this comment to see the full error message
            <pre>{this.props.yamlText}</pre>;
          </div>
        </>
      );
    }

    // ugly: global override of YAML options, but we use it only here
    // @ts-expect-error TS(2741): Property 'minContentWidth' is missing in type '{ l... Remove this comment to see the full error message
    yamlParser.scalarOptions.str.fold = { lineWidth: 0 };
    // @ts-expect-error TS(2339): Property 'content' does not exist on type 'Readonl... Remove this comment to see the full error message
    const contentBySplitter = this.state.content
      .toString()
      // @ts-expect-error TS(2339): Property 'splitterTag' does not exist on type 'Rea... Remove this comment to see the full error message
      .split(this.state.splitterTag);
    const jsxContent = contentBySplitter.map((contentPart: any) => {
      // If contentPart is enclosed with file tags (= if contentPart is a file which should be linked)
      if (
        // @ts-expect-error TS(2339): Property 'fileTag' does not exist on type 'Readonl... Remove this comment to see the full error message
        contentPart.match(`^${this.state.fileTag}(?:.)+${this.state.fileTag}$`)
      ) {
        contentPart = contentPart.replace(
          // @ts-expect-error TS(2339): Property 'fileTag' does not exist on type 'Readonl... Remove this comment to see the full error message
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
            // @ts-expect-error TS(2339): Property 'createHref' does not exist on type 'Read... Remove this comment to see the full error message
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
