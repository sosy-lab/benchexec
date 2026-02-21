// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import yamlParser, { Document } from "yaml";
import { Scalar, YAMLSeq, YAMLMap, Pair } from "yaml/types";

type TaskDefinitionViewerProps = {
  yamlText: string;
  loadNewFile: (fileName: string) => void;
  createHref: (fileName: string) => string;
};

type TaskDefinitionViewerState = {
  content: string | Document;
};

const SPLITTER_TAG = "<splitter#9d81y23>";
const FILE_TAG = "<file#092nt43>";

/** Special view for YAML files in the LinkOverlay component. */
export default class TaskDefinitionViewer extends React.Component<
  TaskDefinitionViewerProps,
  TaskDefinitionViewerState
> {
  constructor(props: TaskDefinitionViewerProps) {
    super(props);
    this.state = {
      content: this.props.yamlText,
    };
  }

  componentDidMount(): void {
    this.prepareTextForRendering();
  }

  componentDidUpdate(prevProps: TaskDefinitionViewerProps): void {
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
  prepareTextForRendering = (): void => {
    if (this.props.yamlText !== "") {
      const yamlObj = yamlParser.parseDocument(this.props.yamlText, {
        prettyErrors: true,
      });

      // NOTE (JS->TS): Official yaml node classes (Scalar, YAMLSeq, YAMLMap, Pair)
      // are used instead of structural "Like" types. This makes the code more robust
      // against internal library changes and provides precise type narrowing
      // via instanceof checks instead of manual shape inspection.
      const inputFiles = yamlObj.get("input_files");
      if (inputFiles instanceof YAMLSeq) {
        inputFiles.items.forEach((item) => {
          if (item instanceof Scalar) {
            item.value = this.encloseFileInTags(String(item.value));
          }
        });
      } else if (inputFiles instanceof Scalar) {
        inputFiles.value = this.encloseFileInTags(String(inputFiles.value));
      } else if (typeof inputFiles === "string") {
        yamlObj.set("input_files", this.encloseFileInTags(inputFiles));
      }

      const properties = yamlObj.get("properties");
      if (properties instanceof YAMLSeq) {
        properties.items.forEach((property) => {
          if (property instanceof YAMLMap) {
            property.items.forEach((propertyItem) => {
              if (propertyItem instanceof Pair) {
                const key = propertyItem.key;
                if (key instanceof Scalar && key.value === "property_file") {
                  const value = propertyItem.value;
                  if (value instanceof Scalar) {
                    value.value = this.encloseFileInTags(String(value.value));
                  }
                }
              }
            });
          }
        });
      }

      this.setState({ content: yamlObj });
    }
  };

  encloseFileInTags = (fileName: string): string => {
    return SPLITTER_TAG + FILE_TAG + fileName + FILE_TAG + SPLITTER_TAG;
  };

  loadFileInViewer = (
    event: React.MouseEvent<HTMLAnchorElement>,
    contentPart: string,
  ): void => {
    event.preventDefault();
    this.props.loadNewFile(contentPart);
  };

  render(): React.ReactNode {
    const { content } = this.state;

    if (
      content instanceof Document &&
      content.errors &&
      content.errors.length > 0
    ) {
      return (
        <>
          <div className="link-overlay-text">
            Errors parsing YAML file:
            <ul>
              {content.errors.map((err, i) => (
                <li key={i}>
                  <pre>{err.message}</pre>
                </li>
              ))}
            </ul>
            <pre>{this.props.yamlText}</pre>;
          </div>
        </>
      );
    }

    // ugly: global override of YAML options, but we use it only here
    (
      yamlParser.scalarOptions.str as unknown as {
        fold: { lineWidth: number };
      }
    ).fold = { lineWidth: 0 };

    const contentBySplitter = content.toString().split(SPLITTER_TAG);
    const jsxContent = contentBySplitter.map((contentPart) => {
      // If contentPart is enclosed with file tags (= if contentPart is a file which should be linked)
      if (contentPart.match(`^${FILE_TAG}(?:.)+${FILE_TAG}$`)) {
        contentPart = contentPart.replace(new RegExp(FILE_TAG, "g"), "");
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
