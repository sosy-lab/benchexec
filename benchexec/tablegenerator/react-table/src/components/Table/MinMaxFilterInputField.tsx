// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import { memo, useEffect, useRef, useState } from "react";
import type {
  FilterElementId,
  FilterValueState,
  SetCustomFilters,
  SetFocusedFilter,
} from "./types";

const numericPattern =
  "([+\\-]?[0-9]*(\\.[0-9]*)?)(:[+\\-]?[0-9]*(\\.[0-9]*)?)?";

type MinMaxFilterInputFieldProps = Readonly<{
  id: string;
  setFilter?: FilterValueState;
  setCustomFilters: SetCustomFilters;
  focusedFilter: string;
  setFocusedFilter: SetFocusedFilter;
}>;

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
}: MinMaxFilterInputFieldProps) {
  const elementId: FilterElementId = `${id}_filter`;
  const initFilterValue = setFilter?.value ?? "";

  const ref = useRef<HTMLInputElement | null>(null);
  // NOTE (JS->TS): Use the proper timer handle type for setTimeout/clearTimeout instead of a string.
  const [typingTimer, setTypingTimer] = useState<
    ReturnType<typeof setTimeout> | undefined
  >(undefined);
  const [value, setValue] = useState<string>(initFilterValue);

  useEffect(() => {
    if (focusedFilter === elementId) {
      // NOTE (JS->TS): Guard against null ref during initial render.
      ref.current?.focus();
    }
  }, [focusedFilter, elementId]);

  const onChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = event.target.value;
    setValue(newValue);
    if (typingTimer !== undefined) {
      clearTimeout(typingTimer);
    }
    setTypingTimer(
      setTimeout(() => {
        setCustomFilters({ id, value: newValue });

        // NOTE (JS->TS): document.getElementById can return null or a non-input element, so guard before focusing.
        const el = document.getElementById(elementId);
        if (el instanceof HTMLInputElement) {
          el.focus();
        } else {
          ref.current?.focus();
        }
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
