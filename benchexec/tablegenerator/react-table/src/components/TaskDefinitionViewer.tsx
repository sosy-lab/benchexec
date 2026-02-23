// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import yamlParser from "yaml";

type TaskDefinitionViewerProps = {
  yamlText: string;
  loadNewFile: (fileName: string) => void;
  createHref: (fileName: string) => string;
};

type YamlParseError = {
  message: string;
};

/**
 * Minimal shape we rely on from yamlParser.parseDocument(...).
 * We keep it intentionally small to stay close to the original JS code.
 */
type YamlDocumentLike = {
  errors?: YamlParseError[];
  get: (key: string) => unknown;
  set: (key: string, value: unknown) => void;
  toString: () => string;
};

type TaskDefinitionViewerState = {
  splitterTag: string;
  fileTag: string;
  content: string | YamlDocumentLike;
};

/** Special view for YAML files in the LinkOverlay component. */
export default class TaskDefinitionViewer extends React.Component<
  TaskDefinitionViewerProps,
  TaskDefinitionViewerState
> {
  constructor(props: TaskDefinitionViewerProps) {
    super(props);
    this.state = {
      splitterTag: "<splitter#9d81y23>",
      fileTag: "<file#092nt43>",
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
      }) as unknown as YamlDocumentLike;

      const inputFiles = yamlObj.get("input_files") as unknown as
        | { items?: Array<{ value: string }> }
        | string
        | undefined;

      if (inputFiles) {
        if (Array.isArray((inputFiles as { items?: unknown }).items)) {
          (inputFiles as { items: Array<{ value: string }> }).items.forEach(
            (inputFileItem) => {
              inputFileItem.value = this.encloseFileInTags(inputFileItem.value);
            },
          );
        } else {
          yamlObj.set(
            "input_files",
            this.encloseFileInTags(String(inputFiles)),
          );
        }
      }

      const properties = yamlObj.get("properties") as unknown as
        | {
            items?: Array<{
              items?: Array<{
                key: { value: unknown };
                value: { value: unknown };
              }>;
            }>;
          }
        | undefined;

      if (properties) {
        if (Array.isArray((properties as { items?: unknown }).items)) {
          (
            properties as {
              items: Array<{
                items?: Array<{
                  key: { value: unknown };
                  value: { value: unknown };
                }>;
              }>;
            }
          ).items.forEach((property) => {
            if (Array.isArray((property as { items?: unknown }).items)) {
              (
                property as {
                  items: Array<{
                    key: { value: unknown };
                    value: { value: unknown };
                  }>;
                }
              ).items.forEach((propertyItem) => {
                if (propertyItem.key.value === "property_file") {
                  const v = propertyItem.value.value;
                  if (typeof v === "string") {
                    propertyItem.value.value = this.encloseFileInTags(v);
                  }
                }
              });
            }
          });
        }
      }

      this.setState({ content: yamlObj });
    }
  };

  encloseFileInTags = (fileName: string): string => {
    return (
      this.state.splitterTag +
      this.state.fileTag +
      fileName +
      this.state.fileTag +
      this.state.splitterTag
    );
  };

  loadFileInViewer = (
    event: React.MouseEvent<HTMLAnchorElement>,
    contentPart: string,
  ): void => {
    event.preventDefault();
    this.props.loadNewFile(contentPart);
  };

  render = (): React.ReactNode => {
    const content = this.state.content;

    if (
      typeof content !== "string" &&
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
    // NOTE (JS->TS): yamlParser's TS types don't expose scalarOptions; keep original behavior via a narrow cast.
    (
      yamlParser as unknown as {
        scalarOptions: { str: { fold: { lineWidth: number } } };
      }
    ).scalarOptions.str.fold = { lineWidth: 0 };

    const asText = typeof content === "string" ? content : content.toString();

    const contentBySplitter = asText.split(this.state.splitterTag);
    const jsxContent = contentBySplitter.map((contentPartOriginal) => {
      let contentPart = contentPartOriginal;
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
  };
}
