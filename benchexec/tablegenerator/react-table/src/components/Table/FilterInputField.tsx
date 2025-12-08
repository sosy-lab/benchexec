// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React, { memo, useEffect, useRef, useState, ChangeEvent } from "react";

interface FilterInputFieldComponentProps {
  id: string;
  setFilter?: { value: string };
  setCustomFilters: (filter: { id: string; value: string }) => void;
  disableTaskText: boolean;
  focusedFilter: string;
  setFocusedFilter: (filterId: string) => void;
}

const FilterInputFieldComponent: React.FC<FilterInputFieldComponentProps> =
  ({
     id,
     setFilter,
     setCustomFilters,
     disableTaskText,
     focusedFilter,
     setFocusedFilter,
   }) => {
    const elementId = `${id}_filter`;
    const initFilterValue: string = setFilter ? setFilter.value : "";

    const ref = useRef<HTMLInputElement | null>(null);
    let [typingTimer, setTypingTimer] = useState<ReturnType<typeof setTimeout> | null>(null);
    let [value, setValue] = useState<string>(initFilterValue);

    useEffect(() => {
      if (focusedFilter === elementId) {
        ref.current?.focus();
      }
    }, [focusedFilter, elementId]);

    const textPlaceholder: string =
      id === "id" && disableTaskText
        ? "To edit, please clear task filter in the sidebar"
        : "text";

    const onChange = (event: ChangeEvent<HTMLInputElement>): void => {
      const newValue: string = event.target.value;
      setValue(newValue);
      if (typingTimer) {
        clearTimeout(typingTimer);
      }
      const timer = setTimeout(() => {
        setCustomFilters({ id, value: newValue });
        document.getElementById(elementId)?.focus();
      }, 500);
      setTypingTimer(timer);
    };

    return (
      <input
        key={elementId}
        id={elementId}
        className="filter-field"
        placeholder={textPlaceholder}
        value={value}
        onChange={onChange}
        disabled={id === "id" ? disableTaskText : false}
        type="search"
        onFocus={() => setFocusedFilter(elementId)}
        ref={ref}
      />
    );
  }

export default memo(FilterInputFieldComponent);