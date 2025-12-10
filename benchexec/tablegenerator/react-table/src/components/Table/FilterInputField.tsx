

interface FilterInputFieldComponentProps {
id: any;
setFilter: any;
disableTaskText: boolean;
setCustomFilters: (newFilter: any) => void;
focusedFilter: null;
setFocusedFilter: Dispatch<SetStateAction<string | null>>;
}// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import { Dispatch, memo, SetStateAction, useEffect, useRef, useState } from "react";

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
  setFocusedFilter,
}: FilterInputFieldComponentProps) {
  const elementId = id + "_filter";
  const initFilterValue = setFilter ? setFilter.value : "";

  const ref = useRef<HTMLInputElement | null>(null);
  const [typingTimer, setTypingTimer] = useState<number | undefined>(undefined);
  let [value, setValue] = useState(initFilterValue);

  useEffect(() => {
    if (focusedFilter === elementId) {
      ref.current?.focus();
    }
  }, [focusedFilter, elementId]);

  const textPlaceholder =
    id === "id" && disableTaskText
      ? "To edit, please clear task filter in the sidebar"
      : "text";

  const onChange = (event: any) => {
    const newValue = event.target.value;
    setValue(newValue);
    if (typingTimer !== undefined) {
      clearTimeout(typingTimer);
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
      ref={ref}
    />
  );
}

export default memo(FilterInputFieldComponent);
