// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import { memo, useEffect, useRef, useState } from "react";

type FilterValueState = {
  value: string;
};

type CustomFilterUpdate = {
  id: string;
  value: string;
};

type SetCustomFilters = (update: CustomFilterUpdate) => void;

type SetFocusedFilter = (filterId: string) => void;

type FilterInputFieldProps = {
  id: string;
  setFilter?: FilterValueState | null;
  setCustomFilters: SetCustomFilters;
  disableTaskText: boolean;
  focusedFilter: string;
  setFocusedFilter: SetFocusedFilter;
};

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
}: FilterInputFieldProps) {
  const elementId = id + "_filter";
  const initFilterValue = setFilter ? setFilter.value : "";

  const ref = useRef<HTMLInputElement | null>(null);
  // NOTE (JS->TS): Changed from string to timeout handle type because setTimeout/clearTimeout work with a timer id, not text.
  const [typingTimer, setTypingTimer] = useState<
    ReturnType<typeof setTimeout> | undefined
  >(undefined);
  const [value, setValue] = useState<string>(initFilterValue);

  useEffect(() => {
    if (focusedFilter === elementId) {
      // NOTE (JS->TS): Optional chaining prevents a crash if the ref is not set yet.
      ref.current?.focus();
    }
  }, [focusedFilter, elementId]);

  const textPlaceholder =
    id === "id" && disableTaskText
      ? "To edit, please clear task filter in the sidebar"
      : "text";

  const onChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = event.target.value;
    setValue(newValue);
    if (typingTimer !== undefined) {
      clearTimeout(typingTimer);
    }
    setTypingTimer(
      setTimeout(() => {
        setCustomFilters({ id, value: newValue });
        // NOTE (JS->TS): document.getElementById may return a non-input element or null, so we guard before focusing.
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
