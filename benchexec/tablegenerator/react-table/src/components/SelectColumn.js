// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import ReactModal from "react-modal";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faTimes } from "@fortawesome/free-solid-svg-icons";
import { getRunSetName, setHashSearch } from "../utils/utils";

export default class SelectColumn extends React.Component {
  constructor(props) {
    super(props);

    // All unique display_titles of the columns of all runsets
    const selectableCols = props.tools
      .map((tool) => tool.columns)
      .flat()
      .filter(
        (col, idx, arr) =>
          idx ===
          arr.findIndex(
            (otherCol) => otherCol.display_title === col.display_title,
          ),
      )
      .map((col) => col.display_title);

    this.state = {
      isButtonOnDeselect: true,
      hiddenCols: this.props.hiddenCols,
      selectableCols,
    };
  }

  componentDidMount() {
    window.history.pushState({}, "", "");
    window.addEventListener("popstate", this.props.close, false);
  }

  componentWillUnmount() {
    window.removeEventListener("popstate", this.props.close, false);

    const hiddenParams = {};
    const hiddenRunsets = [];

    Object.entries(this.state.hiddenCols).forEach(([toolIdx, cols]) => {
      // If all columns of the runset are hidden, the runset will be added to the "hidden" parameter
      const colsOfTool = this.props.tools.find(
        (tool) => tool.toolIdx === parseInt(toolIdx),
      ).columns;
      if (cols.length === colsOfTool.length) {
        hiddenRunsets.push(toolIdx);
        // Hidden columns of runset X will be added to the "hiddenX" parameter if not the entire runset is hidden yet
      } else if (cols.length > 0) {
        hiddenParams["hidden" + toolIdx] = cols.toString();
      } else {
        hiddenParams["hidden" + toolIdx] = null;
      }
    });

    if (hiddenRunsets.length > 0) {
      hiddenParams["hidden"] = hiddenRunsets.toString();
    } else {
      hiddenParams["hidden"] = null;
    }

    setHashSearch(hiddenParams, {
      keepOthers: true,
      history: this.props.history,
    });
  }

  // -------------------------Rendering-------------------------
  renderTools = () => {
    return this.props.tools.map((tool) => {
      const toolIdx = tool.toolIdx;
      const isVisible =
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

  renderToolColumns = (toolIdx) => {
    const currentTool = this.props.tools.find(
      (tool) => tool.toolIdx === toolIdx,
    );
    return this.state.selectableCols.map((colTitle) => {
      const hasToolCol = currentTool.columns.some(
        (col) => col.display_title === colTitle,
      );
      if (hasToolCol) {
        const colIdxs = currentTool.columns
          .filter((col) => col.display_title === colTitle)
          .map((col) => col.colIdx);
        const isVisible = !colIdxs.some((col) =>
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
    return this.state.selectableCols.map((colTitle) => {
      // Column is visible if there is at least one runset that contains this col and this col is not hidden for
      const isVisible = Object.values(this.state.hiddenCols).some(
        (hiddenCols, idx) => {
          const currentTool = this.props.tools.find(
            (tool) => tool.toolIdx === idx,
          );
          const colIdxs = currentTool.columns
            .filter((col) => col.display_title === colTitle)
            .map((col) => col.colIdx);
          return (
            !colIdxs.some((col) => hiddenCols.includes(col)) &&
            currentTool.columns.some(
              (toolCol) => toolCol.display_title === colTitle,
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
    this.props.tools.forEach((tool) => (hiddenCols[tool.toolIdx] = []));

    if (this.state.isButtonOnDeselect) {
      this.props.tools.forEach((tool) => {
        hiddenCols[tool.toolIdx] = tool.columns.map((column) => column.colIdx);
      });
    }

    this.setState((prevState) => ({
      isButtonOnDeselect: !prevState.isButtonOnDeselect,
      hiddenCols,
    }));
  };

  // Toggles all columns of the runset with the id of the target
  toggleToolHidden = (toolIdx, { target }) => {
    const isAlreadyHidden =
      target.type === "checkbox" ? target.checked : target.value;
    const newHiddenCols = isAlreadyHidden
      ? []
      : this.props.tools
          .find((tool) => tool.toolIdx === toolIdx)
          .columns.map((col) => col.colIdx);
    this.setHiddenColsForTool(toolIdx, newHiddenCols);
  };

  // Toggles all columns with the display title of the target within a single runset
  toggleToolColHidden = (toolIdx, colTitle, { target }) => {
    const isAlreadyHidden =
      target.type === "checkbox" ? target.checked : target.value;
    const colIdxs = this.props.tools
      .find((tool) => tool.toolIdx === toolIdx)
      .columns.filter((col) => col.display_title === colTitle)
      .map((col) => col.colIdx);
    isAlreadyHidden
      ? this.removeFromHiddenCols(toolIdx, colIdxs)
      : this.addToHiddenCols(toolIdx, colIdxs);
  };

  // Toggles all columns with the display title of the target column in all runsets
  toggleWholeColHidden = (colTitle, { target }) => {
    const isAlreadyHidden =
      target.type === "checkbox" ? target.checked : target.value;

    this.props.tools.forEach((tool) => {
      const cols = tool.columns.filter((col) => col.display_title === colTitle);
      if (cols.length > 0) {
        const colIdxs = cols.map((col) => col.colIdx);
        isAlreadyHidden
          ? this.removeFromHiddenCols(tool.toolIdx, colIdxs)
          : this.addToHiddenCols(tool.toolIdx, colIdxs);
      }
    });
  };

  // Adds the given column indexes of the given runset to the hidden columns
  addToHiddenCols = (toolIdx, colIdxs) => {
    const newHiddenCols = [
      ...new Set(this.state.hiddenCols[toolIdx].concat(colIdxs)),
    ];
    this.setHiddenColsForTool(toolIdx, newHiddenCols);
  };

  // Removes the given column indexes of the given runset to the hidden columns
  removeFromHiddenCols = (toolIdx, colIdxs) => {
    const newHiddenCols = this.state.hiddenCols[toolIdx].filter(
      (hiddenColIdx) => !colIdxs.includes(hiddenColIdx),
    );
    this.setHiddenColsForTool(toolIdx, newHiddenCols);
  };

  setHiddenColsForTool(toolIdx, newHiddenCols) {
    this.setState((prevState) => ({
      hiddenCols: {
        ...prevState.hiddenCols,
        [toolIdx]: newHiddenCols,
      },
    }));
  }

  handlePopState = () => {
    window.history.back();
  };

  render() {
    ReactModal.setAppElement(document.getElementById("root"));
    const areAllColsDisabled = this.props.tools.every(
      (tool) =>
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
            icon={faTimes}
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
