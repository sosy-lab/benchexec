// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import { memo, useEffect, useRef, useState, ChangeEvent } from "react";

interface FilterValue {
  value?: string;
}

interface FilterInputFieldProps {
  id: string;
  setFilter?: FilterValue;
  setCustomFilters: (filter: { id: string; value: string }) => void;
  disableTaskText?: boolean;
  focusedFilter: string | null;
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
                                     disableTaskText = false,
                                     focusedFilter,
                                     setFocusedFilter,
                                   }: FilterInputFieldProps) {
  const elementId = `${id}_filter`;
  const initFilterValue = setFilter?.value ?? "";

  const ref = useRef<HTMLInputElement | null>(null);
  const [typingTimer, setTypingTimer] = useState<ReturnType<typeof setTimeout> | null>(null);
  const [value, setValue] = useState<string>(initFilterValue);

  useEffect(() => {
    if (focusedFilter === elementId && ref.current) {
      ref.current.focus();
    }
  }, [focusedFilter, elementId]);

  const textPlaceholder =
    id === "id" && disableTaskText
      ? "To edit, please clear task filter in the sidebar"
      : "text";

  const onChange = (event: ChangeEvent<HTMLInputElement>) => {
    const newValue = event.target.value;
    setValue(newValue);

    if (typingTimer) {
      clearTimeout(typingTimer);
    }

    const timer = setTimeout(() => {
      setCustomFilters({ id, value: newValue });

      const el = document.getElementById(elementId) as HTMLInputElement | null;
      el?.focus();
    }, 500);

    setTypingTimer(timer);
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
