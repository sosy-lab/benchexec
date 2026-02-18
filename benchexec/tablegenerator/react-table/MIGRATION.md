<!--
This file is part of BenchExec, a framework for reliable benchmarking:
https://github.com/sosy-lab/benchexec

SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>

SPDX-License-Identifier: Apache-2.0
-->

# TypeScript Migration Plan

This document describes the planned migration of the BenchExec React
frontend from JavaScript to TypeScript.  
The goal is to ensure a reproducible, structured, and well-documented
migration process.

---

## 1. Migration Strategy

The migration follows a **sudden migration strategy**.

This means that the project is migrated to TypeScript as a whole,
instead of gradually introducing TypeScript while keeping JavaScript
as the primary language.

### Rationale

The sudden strategy was chosen for the following reasons:

- The project has a clearly separated frontend codebase.
- Introducing mixed JavaScript and TypeScript code long-term would
  increase maintenance complexity.
- A clean TypeScript-only codebase is the desired end state.
- The migration is performed in a controlled environment and not during
  active feature development.

Although the strategy is classified as _sudden_, a short technical
transition phase is allowed using `allowJs` in the TypeScript
configuration to enable incremental conversion of files.

---

## 2. Migration Steps

The migration is structured into the following steps:

1. Define migration strategy
2. Check library support for TypeScript
3. Add and configure TypeScript (`tsconfig.json`)
4. Integrate TypeScript into the build process
5. Configure linting for TypeScript
6. Adapt development environment and scripts
7. (Optional) Generate API type definitions
8. (Optional) Use migration tools
9. Migrate source files, starting with core modules

Each step is documented by one or more dedicated Git commits.

---

## 3. Commit Structure

To ensure traceability, each migration step is represented by
structured commits.

### Step Commits

Each migration step starts with a commit of the form:

chore: step &lt;n> &lt;short description>

---

### File Migration Commits

When migrating individual files or modules using automated tools,
the following commit sequence is used:

1. **Rename File**
   rename: &lt;file>.js to &lt;file>.ts/.tsx
2. **Tool output**
   tool: convert &lt;file>
3. **Minimal fixes**
   fix: make &lt;file> compile
4. **Manual cleanup**
   refactor: cleanup &lt;file>

This separation makes it explicit which changes were automated and
which were manual improvements.

---

## 4. Migration Order

The migration of source files follows a bottom-up approach:

1. Utility and helper modules
2. Shared types and hooks
3. Common components
4. Feature-specific components

This order minimizes cascading type errors and simplifies refactoring.

---

## 5. Goals and Non-Goals

### Goals

- Fully typed TypeScript codebase
- Strict type checking
- Clear distinction between automated and manual changes
- Reproducible migration process

### Non-Goals

- Functional changes to application behavior
- Refactoring unrelated to type safety
- Introduction of new features during migration

---

## Step 6: Development Environment

No specific IDE or editor is required for this project.
TypeScript support is provided via the TypeScript compiler and ESLint,
which are executed through npm scripts.

Developers are expected to use the following commands:

- `npm run typecheck` – perform standalone TypeScript type checking
- `npm run lint` – check code style and potential issues
- `npm run lint:fix` – automatically fix lint and formatting issues

This ensures a consistent development workflow independent of the
editor or IDE used.

## Step 7: API Type Generation (N/A)

The project does not use generated API clients (e.g., OpenAPI/Swagger, GraphQL codegen).
Therefore, no API type generation step was required.

## Step 8: Use of Migration Tools

Due to the size of the codebase, automated tools were used to support
the migration from JavaScript to TypeScript.

ChatGPT was used as an auxiliary tool to perform initial conversions
of JavaScript files to TypeScript. The tool-generated output was not
used directly without review.

Each automated conversion was followed by:

1. A commit containing only the tool-generated output
2. A commit fixing TypeScript compilation errors
3. A commit performing manual cleanup and refactoring

This approach ensures a clear separation between automated and manual
changes and improves the reproducibility of the migration process.

## Step 9: Migration Checklist

**Order (bottom-up):**

- [ ] `src/utils/` (utils.js, filters.js, stats.js, plot.js)
- [ ] `src/workers/` (workerDirector.js, dataUrls.js)
- [ ] `src/components/` (leaf components → central components)
  - [ ] `src/components/FilterBox/`
  - [ ] `src/components/Table/`
- [ ] Entry points (`src/App.js`, `src/index.js`)
- [ ] Tests as needed (`src/tests/**`, `src/App.test.js`)
- [ ] Node scripts (`scripts/*.js`)
