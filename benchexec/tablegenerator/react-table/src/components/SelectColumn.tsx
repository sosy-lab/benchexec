// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import ReactModal from "react-modal";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faClose } from "@fortawesome/free-solid-svg-icons";
import { getRunSetName, setURLParameter } from "../utils/utils";

export default class SelectColumn extends React.Component {
  constructor(props: any) {
    super(props);

    // All unique display_titles of the columns of all runsets
    const selectableCols = props.tools
      .map((tool: any) => tool.columns)
      .flat()
      .filter(
        (col: any, idx: any, arr: any) =>
          idx ===
          arr.findIndex(
            (otherCol: any) => otherCol.display_title === col.display_title,
          ),
      )
      .map((col: any) => col.display_title);

    this.state = {
      isButtonOnDeselect: true,
      // @ts-expect-error TS(2339): Property 'hiddenCols' does not exist on type 'Read... Remove this comment to see the full error message
      hiddenCols: this.props.hiddenCols,
      selectableCols,
    };
  }

  componentDidMount() {
    window.history.pushState({}, "", "");
    // @ts-expect-error TS(2339): Property 'close' does not exist on type 'Readonly<... Remove this comment to see the full error message
    window.addEventListener("popstate", this.props.close, false);
  }

  componentWillUnmount() {
    // @ts-expect-error TS(2339): Property 'close' does not exist on type 'Readonly<... Remove this comment to see the full error message
    window.removeEventListener("popstate", this.props.close, false);

    const hiddenParams = {};
    const hiddenRunsets: any = [];

    // @ts-expect-error TS(2339): Property 'hiddenCols' does not exist on type 'Read... Remove this comment to see the full error message
    Object.entries(this.state.hiddenCols).forEach(([toolIdx, cols]) => {
      // If all columns of the runset are hidden, the runset will be added to the "hidden" parameter
      // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
      const colsOfTool = this.props.tools.find(
        (tool: any) => tool.toolIdx === parseInt(toolIdx),
      ).columns;
      // @ts-expect-error TS(2571): Object is of type 'unknown'.
      if (cols.length === colsOfTool.length) {
        hiddenRunsets.push(toolIdx);
        // Hidden columns of runset X will be added to the "hiddenX" parameter if not the entire runset is hidden yet
        // @ts-expect-error TS(2571): Object is of type 'unknown'.
      } else if (cols.length > 0) {
        // @ts-expect-error TS(7053): Element implicitly has an 'any' type because expre... Remove this comment to see the full error message
        hiddenParams["hidden" + toolIdx] = cols.toString();
      } else {
        // @ts-expect-error TS(7053): Element implicitly has an 'any' type because expre... Remove this comment to see the full error message
        hiddenParams["hidden" + toolIdx] = null;
      }
    });

    if (hiddenRunsets.length > 0) {
      // @ts-expect-error TS(7053): Element implicitly has an 'any' type because expre... Remove this comment to see the full error message
      hiddenParams["hidden"] = hiddenRunsets.toString();
    } else {
      // @ts-expect-error TS(7053): Element implicitly has an 'any' type because expre... Remove this comment to see the full error message
      hiddenParams["hidden"] = null;
    }

    setURLParameter(hiddenParams);
    // @ts-expect-error TS(2339): Property 'updateParentStateOnClose' does not exist... Remove this comment to see the full error message
    this.props.updateParentStateOnClose();
  }

  // -------------------------Rendering-------------------------
  renderTools = () => {
    // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
    return this.props.tools.map((tool: any) => {
      const toolIdx = tool.toolIdx;
      const isVisible =
        // @ts-expect-error TS(2339): Property 'hiddenCols' does not exist on type 'Read... Remove this comment to see the full error message
        this.state.hiddenCols[toolIdx].length !== tool.columns.length;
      const toolName = getRunSetName(tool);
      return (
        <tr id={toolName} key={"tr" + toolName + toolIdx}>
          <td id={toolName} className={isVisible ? "checked" : ""}>
            <label>
              {toolName}
              <input
                name={toolName + "--" + toolIdx}
                type="checkbox"
                checked={isVisible}
                onChange={(e) => this.toggleToolHidden(toolIdx, e)}
              ></input>
            </label>
          </td>
          {this.renderToolColumns(toolIdx)}
        </tr>
      );
    });
  };

  renderToolColumns = (toolIdx: any) => {
    // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
    const currentTool = this.props.tools.find(
      (tool: any) => tool.toolIdx === toolIdx,
    );
    // @ts-expect-error TS(2339): Property 'selectableCols' does not exist on type '... Remove this comment to see the full error message
    return this.state.selectableCols.map((colTitle: any) => {
      const hasToolCol = currentTool.columns.some(
        (col: any) => col.display_title === colTitle,
      );
      if (hasToolCol) {
        const colIdxs = currentTool.columns
          .filter((col: any) => col.display_title === colTitle)
          .map((col: any) => col.colIdx);
        const isVisible = !colIdxs.some((col: any) =>
          // @ts-expect-error TS(2339): Property 'hiddenCols' does not exist on type 'Read... Remove this comment to see the full error message
          this.state.hiddenCols[toolIdx].includes(col),
        );
        return (
          <td
            id={"td" + toolIdx + colTitle}
            key={colTitle}
            className={isVisible ? "checked" : ""}
          >
            <label>
              {colTitle}
              <input
                id={toolIdx + "--" + colTitle}
                name={toolIdx + "--" + colTitle}
                type="checkbox"
                checked={isVisible}
                onChange={(e) => this.toggleToolColHidden(toolIdx, colTitle, e)}
              ></input>
            </label>
          </td>
        );
      } else {
        return <td key={colTitle}></td>;
      }
    });
  };

  renderColumnHeaders = () => {
    // @ts-expect-error TS(2339): Property 'selectableCols' does not exist on type '... Remove this comment to see the full error message
    return this.state.selectableCols.map((colTitle: any) => {
      // Column is visible if there is at least one runset that contains this col and this col is not hidden for
      // @ts-expect-error TS(2339): Property 'hiddenCols' does not exist on type 'Read... Remove this comment to see the full error message
      const isVisible = Object.values(this.state.hiddenCols).some(
        (hiddenCols, idx) => {
          // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
          const currentTool = this.props.tools.find(
            (tool: any) => tool.toolIdx === idx,
          );
          const colIdxs = currentTool.columns
            .filter((col: any) => col.display_title === colTitle)
            .map((col: any) => col.colIdx);
          return (
            // @ts-expect-error TS(2571): Object is of type 'unknown'.
            !colIdxs.some((col: any) => hiddenCols.includes(col)) &&
            currentTool.columns.some(
              (toolCol: any) => toolCol.display_title === colTitle,
            )
          );
        },
      );
      return (
        <th
          id={"td-all-" + colTitle}
          key={"key" + colTitle}
          className={isVisible ? "checked" : ""}
        >
          <label>
            {colTitle}
            <input
              name={colTitle}
              type="checkbox"
              checked={isVisible}
              onChange={(e) => this.toggleWholeColHidden(colTitle, e)}
            ></input>
          </label>
        </th>
      );
    });
  };

  // -------------------------Handling-------------------------
  // Toggles all columns of all runsets
  toggleAllColsHidden = () => {
    let hiddenCols = {};
    // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
    this.props.tools.forEach((tool: any) => (hiddenCols[tool.toolIdx] = []));

    // @ts-expect-error TS(2339): Property 'isButtonOnDeselect' does not exist on ty... Remove this comment to see the full error message
    if (this.state.isButtonOnDeselect) {
      // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
      this.props.tools.forEach((tool: any) => {
        // @ts-expect-error TS(7053): Element implicitly has an 'any' type because expre... Remove this comment to see the full error message
        hiddenCols[tool.toolIdx] = tool.columns.map(
          (column: any) => column.colIdx,
        );
      });
    }

    this.setState((prevState) => ({
      // @ts-expect-error TS(2339): Property 'isButtonOnDeselect' does not exist on ty... Remove this comment to see the full error message
      isButtonOnDeselect: !prevState.isButtonOnDeselect,
      hiddenCols,
    }));
  };

  // Toggles all columns of the runset with the id of the target
  toggleToolHidden = (toolIdx: any, { target }: any) => {
    const isAlreadyHidden =
      target.type === "checkbox" ? target.checked : target.value;
    const newHiddenCols = isAlreadyHidden
      ? []
      : // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
        this.props.tools
          .find((tool: any) => tool.toolIdx === toolIdx)
          .columns.map((col: any) => col.colIdx);
    this.setHiddenColsForTool(toolIdx, newHiddenCols);
  };

  // Toggles all columns with the display title of the target within a single runset
  toggleToolColHidden = (toolIdx: any, colTitle: any, { target }: any) => {
    const isAlreadyHidden =
      target.type === "checkbox" ? target.checked : target.value;
    // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
    const colIdxs = this.props.tools
      .find((tool: any) => tool.toolIdx === toolIdx)
      .columns.filter((col: any) => col.display_title === colTitle)
      .map((col: any) => col.colIdx);
    isAlreadyHidden
      ? this.removeFromHiddenCols(toolIdx, colIdxs)
      : this.addToHiddenCols(toolIdx, colIdxs);
  };

  // Toggles all columns with the display title of the target column in all runsets
  toggleWholeColHidden = (colTitle: any, { target }: any) => {
    const isAlreadyHidden =
      target.type === "checkbox" ? target.checked : target.value;

    // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
    this.props.tools.forEach((tool: any) => {
      const cols = tool.columns.filter(
        (col: any) => col.display_title === colTitle,
      );
      if (cols.length > 0) {
        const colIdxs = cols.map((col: any) => col.colIdx);
        isAlreadyHidden
          ? this.removeFromHiddenCols(tool.toolIdx, colIdxs)
          : this.addToHiddenCols(tool.toolIdx, colIdxs);
      }
    });
  };

  // Adds the given column indexes of the given runset to the hidden columns
  addToHiddenCols = (toolIdx: any, colIdxs: any) => {
    const newHiddenCols = [
      // @ts-expect-error TS(2339): Property 'hiddenCols' does not exist on type 'Read... Remove this comment to see the full error message
      ...new Set(this.state.hiddenCols[toolIdx].concat(colIdxs)),
    ];
    this.setHiddenColsForTool(toolIdx, newHiddenCols);
  };

  // Removes the given column indexes of the given runset to the hidden columns
  removeFromHiddenCols = (toolIdx: any, colIdxs: any) => {
    // @ts-expect-error TS(2339): Property 'hiddenCols' does not exist on type 'Read... Remove this comment to see the full error message
    const newHiddenCols = this.state.hiddenCols[toolIdx].filter(
      (hiddenColIdx: any) => !colIdxs.includes(hiddenColIdx),
    );
    this.setHiddenColsForTool(toolIdx, newHiddenCols);
  };

  setHiddenColsForTool(toolIdx: any, newHiddenCols: any) {
    this.setState((prevState) => ({
      hiddenCols: {
        // @ts-expect-error TS(2339): Property 'hiddenCols' does not exist on type 'Read... Remove this comment to see the full error message
        ...prevState.hiddenCols,
        [toolIdx]: newHiddenCols,
      },
    }));
  }

  handlePopState = () => {
    window.history.back();
  };

  render() {
    // @ts-expect-error TS(2345): Argument of type 'HTMLElement | null' is not assig... Remove this comment to see the full error message
    ReactModal.setAppElement(document.getElementById("root"));
    // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
    const areAllColsDisabled = this.props.tools.every(
      (tool: any) =>
        // @ts-expect-error TS(2339): Property 'hiddenCols' does not exist on type 'Read... Remove this comment to see the full error message
        tool.columns.length === this.state.hiddenCols[tool.toolIdx].length,
    );
    return (
      <ReactModal
        ariaHideApp={false}
        className="overlay"
        isOpen={true}
        onRequestClose={() => this.handlePopState()}
      >
        <div className="link-overlay-header-container">
          <FontAwesomeIcon
            icon={faClose}
            onClick={() => this.handlePopState()}
            className="closing"
          />
        </div>
        <h1>Select the columns to display</h1>
        <table className="selectRows">
          <tbody>
            <tr className="selectColumn_all">
              <th></th>
              {this.renderColumnHeaders()}
            </tr>
            {this.renderTools()}
          </tbody>
        </table>
        <div className="overlay__buttons">
          <button className="btn" onClick={this.toggleAllColsHidden}>
            // @ts-expect-error TS(2339): Property 'isButtonOnDeselect' does not
            exist on ty... Remove this comment to see the full error message
            {this.state.isButtonOnDeselect ? "Deselect all" : "Select all"}
          </button>
          <button
            className="btn btn-apply"
            onClick={() => this.handlePopState()}
            disabled={areAllColsDisabled}
          >
            Apply and close
          </button>
          <input />
        </div>
      </ReactModal>
    );
  }
}
