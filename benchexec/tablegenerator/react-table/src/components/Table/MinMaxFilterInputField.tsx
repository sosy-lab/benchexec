// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import { memo, useEffect, useRef, useState } from "react";

const numericPattern =
  "([+\\-]?[0-9]*(\\.[0-9]*)?)(:[+\\-]?[0-9]*(\\.[0-9]*)?)?";

/**
 * Filter input field for numeric columns with min and max values.
 * This file default exports a memoized version of the MinMaxFilterInputFieldComponent function.
 */
function MinMaxFilterInputFieldComponent({
  id,
  setFilter,
  setCustomFilters,
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
      id={elementId}
      key={elementId}
      className="filter-field"
      placeholder="Min:Max"
      defaultValue={value}
      onChange={onChange}
      type="search"
      pattern={numericPattern}
      onFocus={() => setFocusedFilter(elementId)}
      ref={ref}
    />
  );
}

export default memo(MinMaxFilterInputFieldComponent);
