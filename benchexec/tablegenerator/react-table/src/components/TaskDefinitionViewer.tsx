// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import yamlParser, { Document } from "yaml";

type TaskDefinitionViewerProps = {
  yamlText: string;
  loadNewFile: (fileName: string) => void;
  createHref: (fileName: string) => string;
};

type TaskDefinitionViewerState = {
  splitterTag: string;
  fileTag: string;
  content: string | Document;
};

/* ============================================================================
 * Internal helper types
 * ========================================================================== */

/** Minimal shape of a YAML sequence node that we need in this component. */
type YamlSeqLike<TItem> = {
  items: TItem[];
};

type YamlScalarLike<T> = {
  value: T;
};

type YamlPairLike<TKey, TValue> = {
  key: YamlScalarLike<TKey>;
  value: YamlScalarLike<TValue>;
};

/* ============================================================================
 * Type guards / helpers
 * ========================================================================== */

const hasItemsArray = <TItem,>(value: unknown): value is YamlSeqLike<TItem> =>
  typeof value === "object" &&
  value !== null &&
  Array.isArray((value as { items?: unknown }).items);

const isYamlDocument = (value: unknown): value is Document =>
  typeof value === "object" &&
  value !== null &&
  "toString" in value &&
  "errors" in value;

const toText = (value: unknown): string => {
  // NOTE (JS->TS): Keep behavior tolerant for YAML nodes and primitives by normalizing to string.
  return typeof value === "string" ? value : String(value);
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
      });

      const inputFiles = yamlObj.get("input_files") as unknown;
      if (inputFiles) {
        if (hasItemsArray<YamlScalarLike<unknown>>(inputFiles)) {
          inputFiles.items.forEach((inputFileItem) => {
            inputFileItem.value = this.encloseFileInTags(
              toText(inputFileItem.value),
            );
          });
        } else {
          yamlObj.set(
            "input_files",
            this.encloseFileInTags(toText(inputFiles)),
          );
        }
      }

      const properties = yamlObj.get("properties") as unknown;
      if (properties) {
        if (
          hasItemsArray<YamlSeqLike<YamlPairLike<unknown, unknown>>>(properties)
        ) {
          properties.items.forEach((property) => {
            if (hasItemsArray<YamlPairLike<unknown, unknown>>(property)) {
              property.items.forEach((propertyItem) => {
                if (propertyItem.key.value === "property_file") {
                  propertyItem.value.value = this.encloseFileInTags(
                    toText(propertyItem.value.value),
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

  render(): React.ReactNode {
    const { content } = this.state;

    if (
      isYamlDocument(content) &&
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

    const contentBySplitter = content.toString().split(this.state.splitterTag);
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
