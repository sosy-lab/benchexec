// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React, { useState, useEffect, useRef, useCallback } from "react";
import equals from "deep-equal";
import { pathOr } from "../../utils/utils";
import "rc-slider/assets/index.css";

let debounceHandler: ReturnType<typeof setTimeout>;

interface TaskFilterCardProps {
  ids: Record<string, string>;
  filters?: any[];
  resetFilterHook: (fun: () => void) => void;
  updateFilters: (values: Record<string, string>) => void;
}

const TaskFilterCard: React.FC<TaskFilterCardProps> = (props) => {
  const { ids, filters = [], resetFilterHook, updateFilters } = props;

  const extractFilters = useCallback(() => {
    let i = 0;
    const newVal: Record<string, any> = {};
    for (const id of Object.keys(ids)) {
      newVal[id] = pathOr(["filters", i++], "", props);
    }
    return newVal;
  }, [ids, props]);

  const [values, setValues] = useState<Record<string, string>>(extractFilters());

  // Register reset hook on mount
  useEffect(() => {
    resetFilterHook(() => resetIdFilters());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const resetIdFilters = useCallback(() => {
    setValues({});
    sendFilterUpdate({});
  }, []);

  const sendFilterUpdate = useCallback(
    (vals: Record<string, string>) => {
      updateFilters(vals);
    },
    [updateFilters]
  );

  useEffect(() => {
    if (!equals(props.filters, filters)) {
      const newVal = extractFilters();
      setValues(newVal);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.filters]);

  const handleChange = (key: string, textValue: string) => {
    clearTimeout(debounceHandler);
    const newState = { ...values, [key]: textValue };
    setValues(newState);
    debounceHandler = setTimeout(() => {
      sendFilterUpdate(newState);
    }, 500);
  };

  const makeHeader = () => (
    <div className="filter-card--header">
      <h4 className="title">Task filter</h4>
    </div>
  );

  const makeFilterBody = () => {
    const body = Object.entries(ids).map(([key, example]) => {
      const value = values[key] || "";
      const id = `text-task-${key}`;
      return (
        <div key={id} className="task-id-filters">
          <label htmlFor={id}>{key}</label>
          <br />
          <input
            type="text"
            name={id}
            placeholder={example}
            value={value}
            onChange={({ target: { value: textValue } }) => handleChange(key, textValue)}
          />
        </div>
      );
    });
    return <div className="filter-card--body">{body}</div>;
  };

  return (
    <div className="filterBox--container">
      <div className="filter-card">
        {makeHeader()}
        {makeFilterBody()}
      </div>
    </div>
  );
};

export default TaskFilterCard;