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
      <svg
        aria-hidden="true"
        className="svg-inline--fa fa-filter fa-w-16 filter-icon"
        data-icon="filter"
        data-prefix="fas"
        focusable="false"
        role="img"
        viewBox="0 0 512 512"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          d="M487.976 0H24.028C2.71 0-8.047 25.866 7.058 40.971L192 225.941V432c0 7.831 3.821 15.17 10.237 19.662l80 55.98C298.02 518.69 320 507.493 320 487.98V225.941l184.947-184.97C520.021 25.896 509.338 0 487.976 0z"
          fill="currentColor"
        />
      </svg>
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
      <svg
        aria-hidden="true"
        className="svg-inline--fa fa-filter fa-w-16 filter-icon"
        data-icon="filter"
        data-prefix="fas"
        focusable="false"
        role="img"
        viewBox="0 0 512 512"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          d="M487.976 0H24.028C2.71 0-8.047 25.866 7.058 40.971L192 225.941V432c0 7.831 3.821 15.17 10.237 19.662l80 55.98C298.02 518.69 320 507.493 320 487.98V225.941l184.947-184.97C520.021 25.896 509.338 0 487.976 0z"
          fill="currentColor"
        />
      </svg>
    </button>
  `);
});
