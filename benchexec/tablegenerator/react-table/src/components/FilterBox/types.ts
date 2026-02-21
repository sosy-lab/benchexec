// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

export type FilterType = "status" | "text" | "measure" | "number";

export interface FilterUpdatePayload {
  values: string[];
  title: string;
}

export interface AvailableFilter {
  idx: number;
  display_title: string;
  title: string;
}

/**
 * Describes the externally provided filter state (values/filtering).
 * This is merged into the internal filter definitions on updates.
 */
export interface CurrentFilterUpdate {
  values: string[];
  filtering?: boolean;
}

/**
 * Common fields for all filter types.
 */
export interface BaseFilterDefinition {
  idx: number;
  title: string;
  display_title: string;
  type: FilterType;
  unit?: string;
  number_of_significant_digits?: number;

  // Runtime state
  values?: string[];
  filtering?: boolean;
  touched: number;
  numCards: number;

  // Optional fields that are specific to certain types
  // but kept here for easier access and migration.
  categories?: string[];
  statuses?: string[];
  min?: number;
  max?: number;

  [key: string]: unknown;
}

export interface StatusFilter extends BaseFilterDefinition {
  type: "status";
  categories: string[];
  statuses: string[];
}

export interface NumberFilter extends BaseFilterDefinition {
  type: "measure" | "number";
  min?: number;
  max?: number;
}

export interface TextFilter extends BaseFilterDefinition {
  type: "text";
}

export type FilterDefinition = StatusFilter | NumberFilter | TextFilter;
