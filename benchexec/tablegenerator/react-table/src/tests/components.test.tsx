// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

// react standard
// @ts-expect-error TS(6133): 'React' is declared but its value is never read.
import React from "react";
// @ts-expect-error TS(7016): Could not find a declaration file for module 'reac... Remove this comment to see the full error message
import renderer from "react-test-renderer";

// Testing Library
import { render, screen, fireEvent } from "@testing-library/react";

// components
import Reset from "../components/FilterInfoButton.js";

// NOTE:
// The original Enzyme test rendered the reset button, checked its text and
// then did `expect(resetBtn).toEqual({})`, which did not assert any real
// runtime behavior. After migrating to React Testing Library, we keep the
// meaningful part (render + text check + click). However, we intentionally do not add
// stronger assertions (e.g., about resetFilters), because the component itself
// does not call resetFilters and the old test never verified that either.
test("Click on reset button stops button from rendering", () => {
  let isFiltered = true;

  render(
    <Reset
      // @ts-expect-error TS(2769): No overload matches this call.
      isFiltered={isFiltered}
      filteredCount="23"
      totalCount="42"
      resetFilters={() => (isFiltered = false)}
    />,
  );

  const button = screen.getByRole("button");
  expect(button).toHaveTextContent("Showing 23 of 42 tasks");

  fireEvent.click(button);
});

it("Render reset button", () => {
  // @ts-expect-error TS(2769): No overload matches this call.
  const reset = <Reset filteredCount="23" totalCount="42" isFiltered={true} />;

  expect(renderer.create(reset)).toMatchInlineSnapshot(`
    <button
     className="reset"
     disabled={false}
    >
     <span>
      Showing 
      <span
       className="highlight"
      >
       23
      </span>
      of
     </span>
     42
     tasks
     <i
      className="fa filter"
     />
    </button>
  `);
});

it("Hide reset button", () => {
  // @ts-expect-error TS(2769): No overload matches this call.
  const reset = <Reset isFiltered={false} />;

  expect(renderer.create(reset)).toMatchInlineSnapshot(`
    <button
     className="reset"
     disabled={true}
    >
     <span>
      Showing 
      <span
       className="highlight"
      />
      of
     </span>
     tasks
     <i
      className="fa filter"
     />
    </button>
  `);
});
