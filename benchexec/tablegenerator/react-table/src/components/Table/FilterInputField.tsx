// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import { memo, useEffect, useRef, useState } from "react";

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
}: any) {
  const elementId = id + "_filter";
  const initFilterValue = setFilter ? setFilter.value : "";

  const ref = useRef(null);
  let [typingTimer, setTypingTimer] = useState("");
  let [value, setValue] = useState(initFilterValue);

  useEffect(() => {
    if (focusedFilter === elementId) {
      // @ts-expect-error TS(2531): Object is possibly 'null'.
      ref.current.focus();
    }
  }, [focusedFilter, elementId]);

  const textPlaceholder =
    id === "id" && disableTaskText
      ? "To edit, please clear task filter in the sidebar"
      : "text";

  const onChange = (event: any) => {
    const newValue = event.target.value;
    setValue(newValue);
    clearTimeout(typingTimer);
    setTypingTimer(
      // @ts-expect-error TS(2345): Argument of type 'Timeout' is not assignable to pa... Remove this comment to see the full error message
      setTimeout(() => {
        setCustomFilters({ id, value: newValue });
        // @ts-expect-error TS(2531): Object is possibly 'null'.
        document.getElementById(elementId).focus();
      }, 500),
    );
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
