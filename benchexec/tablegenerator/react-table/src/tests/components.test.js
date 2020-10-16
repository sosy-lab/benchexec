// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

// react standard
import React from "react";
import renderer from "react-test-renderer";

// enzyme
import { shallow, configure } from "enzyme";
import Adapter from "enzyme-adapter-react-16";

// components
import Reset from "../components/FilterInfoButton.js";

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

  expect(resetBtn.text()).toContain("Showing 23 of 42 tasks");

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
  const component = renderer.create(<Reset isFiltered={false} />).toJSON();

  expect(component).toMatchInlineSnapshot(`
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
