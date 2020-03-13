/* SPDX-License-Identifier: Apache-2.0
 *
 * BenchExec is a framework for reliable benchmarking.
 * This file is part of BenchExec.
 * Copyright (C) Dirk Beyer. All rights reserved.
 */
// react standard
import React from "react";
import renderer from "react-test-renderer";

// enzyme
import { shallow, configure } from "enzyme";
import Adapter from "enzyme-adapter-react-16";

// components
import Reset from "../components/Reset.js";

configure({ adapter: new Adapter() });

test("Click on reset button stops button from rendering", () => {
  let isFiltered = true;

  const resetBtn = shallow(
    <Reset
      isFiltered={isFiltered}
      filteredCount="23"
      totalCount="42"
      resetFilters={() => (isFiltered = false)}
    />,
  );

  expect(resetBtn.text()).toEqual("Showing 23 of 42 tasks (Reset Filters)");

  resetBtn.simulate("click");

  expect(resetBtn).toEqual({});
});

it("Render reset button", () => {
  const component = renderer
    .create(<Reset filteredCount="23" totalCount="42" isFiltered={true} />)
    .toJSON();

  expect(component).toMatchInlineSnapshot(`
    <button
      className="reset"
      disabled={false}
    >
      <span
        className="hide"
      >
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
      <span
        className="hide"
      >
         
        (
        <span
          className="highlight"
        >
          Reset Filters
        </span>
        )
      </span>
    </button>
  `);
});

it("Hide reset button", () => {
  const component = renderer.create(<Reset isFiltered={false} />).toJSON();

  expect(component).toMatchInlineSnapshot(`
    <button
      className="reset"
      disabled={true}
    >
      <span
        className="hide"
      >
        Showing 
        <span
          className="highlight"
        />
         of
         
      </span>
       tasks
      <span
        className="hide"
      >
         
        (
        <span
          className="highlight"
        >
          Reset Filters
        </span>
        )
      </span>
    </button>
  `);
});
