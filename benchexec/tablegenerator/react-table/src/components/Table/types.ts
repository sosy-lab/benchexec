// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

export type FilterValueState = {
  value: string;
};

export type CustomFilterUpdate = Readonly<{
  id: string;
  value: string;
}>;

export type SetCustomFilters = (update: CustomFilterUpdate) => void;

export type FilterElementId = `${string}_filter`;

export type SetFocusedFilter = (filterId: FilterElementId) => void;
