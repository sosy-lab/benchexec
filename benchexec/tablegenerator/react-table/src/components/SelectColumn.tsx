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

/* ============================================================
 * Domain Types
 * ============================================================
 */

type RunSetColumnLike = {
  display_title: React.ReactNode;
  colIdx: number;
};

type RunSetLike = {
  toolIdx: number;
  tool: string;
  date: string;
  niceName: string;
  columns: RunSetColumnLike[];
};

type HiddenColsByTool = Record<number, number[]>;

/* ============================================================
 * Component Types
 * ============================================================
 */

type SelectColumnProps = {
  close: () => void;
  tools: RunSetLike[];
  hiddenCols: HiddenColsByTool;
  updateParentStateOnClose: () => void;
};

type SelectColumnState = {
  isButtonOnDeselect: boolean;
  hiddenCols: HiddenColsByTool;
  selectableCols: React.ReactNode[];
};

export default class SelectColumn extends React.Component<
  SelectColumnProps,
  SelectColumnState
> {
  constructor(props: SelectColumnProps) {
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

  componentDidMount(): void {
    window.history.pushState({}, "", "");
    window.addEventListener("popstate", this.props.close, false);
  }

  componentWillUnmount(): void {
    window.removeEventListener("popstate", this.props.close, false);

    const hiddenParams: Record<string, string | null> = {};
    const hiddenRunsets: string[] = [];

    Object.entries(this.state.hiddenCols).forEach(([toolIdxStr, cols]) => {
      // Object.entries returns string keys.
      // We convert to number for numeric comparison with tool.toolIdx,
      // but keep the original string for building URL parameters.
      const toolIdx = Number(toolIdxStr);

      // If all columns of the runset are hidden, the runset will be added to the "hidden" parameter
      const colsOfTool =
        this.props.tools.find((tool) => tool.toolIdx === toolIdx)?.columns ??
        [];

      if (cols.length === colsOfTool.length) {
        hiddenRunsets.push(toolIdxStr);
        // Hidden columns of runset X will be added to the "hiddenX" parameter if not the entire runset is hidden yet
      } else if (cols.length > 0) {
        hiddenParams["hidden" + toolIdxStr] = cols.toString();
      } else {
        hiddenParams["hidden" + toolIdxStr] = null;
      }
    });

    if (hiddenRunsets.length > 0) {
      hiddenParams["hidden"] = hiddenRunsets.toString();
    } else {
      hiddenParams["hidden"] = null;
    }

    setURLParameter(hiddenParams);
    this.props.updateParentStateOnClose();
  }

  // -------------------------Rendering-------------------------
  renderTools = (): React.ReactNode => {
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

  renderToolColumns = (toolIdx: number): React.ReactNode => {
    const currentTool = this.props.tools.find(
      (tool) => tool.toolIdx === toolIdx,
    );

    if (!currentTool) {
      return this.state.selectableCols.map((colTitle) => (
        <td key={String(colTitle)}></td>
      ));
    }

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
            id={"td" + toolIdx + String(colTitle)}
            key={String(colTitle)}
            className={isVisible ? "checked" : ""}
          >
            <label>
              {colTitle}
              <input
                id={toolIdx + "--" + String(colTitle)}
                name={toolIdx + "--" + String(colTitle)}
                type="checkbox"
                checked={isVisible}
                onChange={(e) => this.toggleToolColHidden(toolIdx, colTitle, e)}
              ></input>
            </label>
          </td>
        );
      } else {
        return <td key={String(colTitle)}></td>;
      }
    });
  };

  renderColumnHeaders = (): React.ReactNode => {
    return this.state.selectableCols.map((colTitle) => {
      // Column is visible if there is at least one runset that contains this col and this col is not hidden for
      const isVisible = Object.values(this.state.hiddenCols).some(
        (hiddenCols, idx) => {
          const currentTool = this.props.tools.find(
            (tool) => tool.toolIdx === idx,
          );
          if (!currentTool) {
            return false;
          }

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
          id={"td-all-" + String(colTitle)}
          key={"key" + String(colTitle)}
          className={isVisible ? "checked" : ""}
        >
          <label>
            {colTitle}
            <input
              name={String(colTitle)}
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
  toggleAllColsHidden = (): void => {
    const hiddenCols: HiddenColsByTool = {};
    this.props.tools.forEach((tool) => {
      hiddenCols[tool.toolIdx] = [];
    });

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
  toggleToolHidden = (
    toolIdx: number,
    { target }: React.ChangeEvent<HTMLInputElement>,
  ): void => {
    const isAlreadyHidden =
      target.type === "checkbox" ? target.checked : Boolean(target.value);

    const newHiddenCols = isAlreadyHidden
      ? []
      : this.props.tools
          .find((tool) => tool.toolIdx === toolIdx)
          ?.columns.map((col) => col.colIdx) ?? [];

    this.setHiddenColsForTool(toolIdx, newHiddenCols);
  };

  // Toggles all columns with the display title of the target within a single runset
  toggleToolColHidden = (
    toolIdx: number,
    colTitle: React.ReactNode,
    { target }: React.ChangeEvent<HTMLInputElement>,
  ): void => {
    const isAlreadyHidden =
      target.type === "checkbox" ? target.checked : Boolean(target.value);
    const colIdxs =
      this.props.tools
        .find((tool) => tool.toolIdx === toolIdx)
        ?.columns.filter((col) => col.display_title === colTitle)
        .map((col) => col.colIdx) ?? [];

    isAlreadyHidden
      ? this.removeFromHiddenCols(toolIdx, colIdxs)
      : this.addToHiddenCols(toolIdx, colIdxs);
  };

  // Toggles all columns with the display title of the target column in all runsets
  toggleWholeColHidden = (
    colTitle: React.ReactNode,
    { target }: React.ChangeEvent<HTMLInputElement>,
  ): void => {
    const isAlreadyHidden =
      target.type === "checkbox" ? target.checked : Boolean(target.value);

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
  addToHiddenCols = (toolIdx: number, colIdxs: number[]) => {
    const newHiddenCols = [
      ...new Set(this.state.hiddenCols[toolIdx].concat(colIdxs)),
    ];
    this.setHiddenColsForTool(toolIdx, newHiddenCols);
  };

  // Removes the given column indexes of the given runset to the hidden columns
  removeFromHiddenCols = (toolIdx: number, colIdxs: number[]) => {
    const newHiddenCols = this.state.hiddenCols[toolIdx].filter(
      (hiddenColIdx) => !colIdxs.includes(hiddenColIdx),
    );
    this.setHiddenColsForTool(toolIdx, newHiddenCols);
  };

  setHiddenColsForTool(toolIdx: number, newHiddenCols: number[]): void {
    this.setState((prevState) => ({
      hiddenCols: {
        ...prevState.hiddenCols,
        [toolIdx]: newHiddenCols,
      },
    }));
  }

  handlePopState = (): void => {
    window.history.back();
  };

  render(): React.ReactNode {
    // NOTE (JS->TS): ReactModal.setAppElement can accept null; we keep behavior but provide a safe fallback.
    ReactModal.setAppElement(document.getElementById("root") ?? document.body);

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
