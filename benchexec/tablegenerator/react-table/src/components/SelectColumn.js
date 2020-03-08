/* SPDX-License-Identifier: Apache-2.0
 *
 * BenchExec is a framework for reliable benchmarking.
 * This file is part of BenchExec.
 * Copyright (C) Dirk Beyer. All rights reserved.
 */
import React from "react";
import ReactModal from "react-modal";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faTimes } from "@fortawesome/free-solid-svg-icons";
import { getRunSetName } from "../utils/utils";

export default class SelectColumn extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      deselect: true,
      list: [...this.props.tools]
    };
    this.selectable = [];
  }

  // -------------------------Rendering-------------------------
  renderRunSets = () => {
    return this.state.list.map((tool, i) => {
      const isVisible = tool.columns.some(value => value.isVisible === true);
      const toolName = getRunSetName(tool);
      return (
        <tr id={toolName} key={`tr${toolName}`}>
          <td
            id={toolName}
            key={`key${toolName}`}
            className={isVisible ? "checked" : ""}
          >
            <label>
              {toolName}
              <input
                name={toolName}
                type="checkbox"
                checked={isVisible}
                onChange={e => this.deselectTool(i, e)}
              ></input>
            </label>
          </td>
          {this.renderColumns(i)}
        </tr>
      );
    });
  };

  renderColumns = index => {
    const { columns } = this.state.list[index];
    return this.selectable.map((headerRow, idxHeader) => {
      const column = columns.find(
        el => el.display_title === headerRow.display_title
      );
      if (column !== undefined) {
        return (
          <td
            id={`td${index}${column.display_title}`}
            key={`key${idxHeader}${column.display_title}`}
            className={column.isVisible ? "checked" : ""}
          >
            <label>
              {column.display_title}
              <input
                id={`${index}--${column.display_title}`}
                name={`${index}--${column.display_title}`}
                type="checkbox"
                checked={column.isVisible}
                onChange={this.handleSelecion}
              ></input>
            </label>
          </td>
        );
      }
      return <td key={idxHeader}></td>;
    });
  };

  renderSelectColumns = () => {
    this.state.list.forEach(tool => {
      tool.columns.forEach(column => {
        if (
          !this.selectable.some(
            value => value.display_title === column.display_title
          )
        ) {
          this.selectable.push(column);
        }
      });
    });
    return this.selectable.map(column => {
      const isVisible = this.state.list.some(tool =>
        tool.columns.some(
          col =>
            col.isVisible === true && col.display_title === column.display_title
        )
      );
      return (
        <th
          id={`td-all-${column.display_title}`}
          key={`key${column.display_title}`}
          className={isVisible ? "checked" : ""}
        >
          <label>
            {column.display_title}
            <input
              name={column.display_title}
              type="checkbox"
              checked={isVisible}
              onChange={this.handleSelectColumns}
            ></input>
          </label>
        </th>
      );
    });
  };

  // -------------------------Handling-------------------------
  handleSelecion = ({ target }) => {
    const [tool, column] = target.name.split("--");
    const value = target.type === "checkbox" ? target.checked : target.value;
    const list = [...this.state.list];

    list[tool].columns.find(
      el => el.display_title === column
    ).isVisible = value;

    this.checkTools(list);
  };

  handleSelectColumns = ({ target }) => {
    const value = target.type === "checkbox" ? target.checked : target.value;
    const list = [...this.state.list];

    list.forEach(tool => {
      const column = tool.columns.find(el => el.display_title === target.name);
      if (column) {
        column.isVisible = value;
      }
    });

    this.checkTools(list);
  };

  deselectTool = (i, { target }) => {
    const value = target.type === "checkbox" ? target.checked : target.value;
    const list = [...this.state.list];

    list[i].columns.forEach(column => {
      // eslint-disable-next-line no-param-reassign
      column.isVisible = value;
    });

    this.checkTools(list);
  };

  deselectAll = () => {
    const list = [...this.state.list];

    list.forEach(tool =>
      tool.columns.forEach(column => {
        // eslint-disable-next-line no-param-reassign
        column.isVisible = !this.state.deselect;
      })
    );

    this.checkTools(list);
    this.setState(prevState => ({
      deselect: !prevState.deselect
    }));
  };

  checkTools = list => {
    list.forEach(tool => {
      // eslint-disable-next-line no-param-reassign
      tool.isVisible = tool.columns.some(column => column.isVisible);
    });

    this.setState({ list });
  };

  render() {
    ReactModal.setAppElement(document.getElementById("root"));
    return (
      <ReactModal
        ariaHideApp={false}
        className="overlay"
        isOpen={true}
        onRequestClose={this.props.close}
      >
        <FontAwesomeIcon
          icon={faTimes}
          onClick={this.props.close}
          className="closing"
        />
        <h1>Select the columns to display</h1>
        <table className="selectRows">
          <tbody>
            <tr className="selectColumn_all">
              <th></th>
              {this.renderSelectColumns()}
            </tr>
            {this.renderRunSets()}
          </tbody>
        </table>
        <div className="overlay__buttons">
          <button className="btn" onClick={this.deselectAll}>
            {this.state.deselect ? "Deselect all" : "Select all"}
          </button>
          <button
            className="btn btn-apply"
            onClick={this.props.close}
            disabled={!this.state.list.filter(tool => tool.isVisible).length}
          >
            Apply and close
          </button>
          <input />
        </div>
      </ReactModal>
    );
  }
}
