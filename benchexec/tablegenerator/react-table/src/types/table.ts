// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

/* ============================================================================
 * Table UI: Filter input state helpers (components/Table/*)
 * ========================================================================== */

type FilterValueState = {
  value: string;
};

type CustomFilterUpdate = Readonly<{
  id: string;
  value: string;
}>;

type SetCustomFilters = (update: CustomFilterUpdate) => void;

type FilterElementId = `${string}_filter`;

type SetFocusedFilter = (filterId: FilterElementId) => void;

export type {
  FilterValueState,
  SetCustomFilters,
  FilterElementId,
  SetFocusedFilter,
};
