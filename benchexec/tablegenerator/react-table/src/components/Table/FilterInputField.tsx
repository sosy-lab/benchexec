

// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import { ChangeEvent, memo, useEffect, useRef, useState } from "react";

interface FilterInputFieldProps {
  id: string,
  setFilter: any,
  setCustomFilters: (filter: { id: string, value: string }) => void;
  disableTaskText: boolean,
  focusedFilter?: string,
  setFocusedFilter: (id: string) => void;
}

/**
 * General filter input field for text columns.
 * This file default exports a memoized version of the FilterInputFieldComponent function.
 */
function FilterInputFieldComponent({
  id,
  setFilter,
  setCustomFilters,
  disableTaskText,
  focusedFilter,
  setFocusedFilter
}: FilterInputFieldProps) {
  const elementId = id + "_filter";
  const initFilterValue = setFilter ? setFilter.value : "";

  const ref = useRef<HTMLInputElement | null>(null);
  const [typingTimer, setTypingTimer] = useState<number | undefined>(undefined);
  const [value, setValue] = useState(initFilterValue);

  useEffect(() => {
    if (focusedFilter === elementId) {
      ref.current?.focus();
    }
  }, [focusedFilter, elementId]);

  const textPlaceholder =
  id === "id" && disableTaskText ?
  "To edit, please clear task filter in the sidebar" :
  "text";

  const onChange = (event: ChangeEvent<HTMLInputElement>) => {
    const newValue = event.target.value;
    setValue(newValue);
    if (typingTimer !== undefined) {
      window.clearTimeout(typingTimer);
    }
    const timerId = window.setTimeout(() => {
      setCustomFilters({ id, value: newValue });
      document.getElementById(elementId)?.focus();
    }, 500);
    setTypingTimer(timerId);
  };

  return (
    <input
      key={elementId}
      id={elementId}
      className="filter-field"
      placeholder={textPlaceholder}
      defaultValue={value}
      onChange={onChange}
      disabled={id === "id" ? disableTaskText : false}
      type="search"
      onFocus={() => setFocusedFilter(elementId)}
      ref={ref} />);


}

export default memo(FilterInputFieldComponent);