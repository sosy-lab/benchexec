// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

// NOTE (JS->TS): Re-export types from the main zip.js entry so that the deep import
// "zip-no-worker-inflate" has proper TypeScript typings.
declare module "@zip.js/zip.js/lib/zip-no-worker-inflate" {
  export * from "@zip.js/zip.js";
}
