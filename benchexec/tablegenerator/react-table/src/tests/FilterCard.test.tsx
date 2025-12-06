// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import renderer from "react-test-renderer";

import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import FilterCard from "../components/FilterBox/FilterCard.js";

const createFilterCard = (props) => <FilterCard {...props} />;

describe("FilterCard tests", () => {
  test("FilterCard should allow selection of available filters", () => {
    const availableFilters = [
      { display_title: "Filter1", idx: 0 },
      { display_title: "Filter2", idx: 1 },
    ];
    const Card = createFilterCard({ availableFilters, editable: true });

    expect(renderer.create(Card)).toMatchSnapshot();
  });

  test("FilterCard should display checkboxes for status filters", () => {
    const filter = {
      display_title: "Status",
      categories: ["cat1", "correct", "wrong"],
      statuses: ["true", "false(reach)"],
      type: "status",
    };
    const Card = createFilterCard({ title: "Status", filter });

    expect(renderer.create(Card)).toMatchSnapshot();
  });

  test("FilterCard should display range slider for number filters", () => {
    const filter = {
      display_title: "cputime",
      min: 1337,
      max: 9001,
      type: "measure",
    };
    const Card = createFilterCard({ title: "cputime", filter });

    expect(renderer.create(Card)).toMatchSnapshot();
  });

  test("FilterCard should display textbox for text filters", () => {
    const filter = {
      display_title: "host",
      type: "text",
    };
    const Card = createFilterCard({ title: "host", filter });

    expect(renderer.create(Card)).toMatchSnapshot();
  });

  test("FilterCard should correctly reflect already set status filters", () => {
    const filter = {
      display_title: "Status",
      categories: ["cat1", "correct", "wrong"],
      statuses: ["true", "false(reach)"],
      values: ["true"],
      type: "status",
    };
    const Card = createFilterCard({ title: "Status", filter });

    expect(renderer.create(Card)).toMatchSnapshot();
  });

  test("FilterCard should correctly reflect already set number filters", () => {
    const filter = {
      display_title: "cputime",
      min: 1337,
      max: 9001,
      values: ["1500:3000"],
      type: "measure",
    };
    const Card = createFilterCard({ title: "cputime", filter });

    expect(renderer.create(Card)).toMatchSnapshot();
  });

  test("FilterCard should correctly reflect already set text filters", () => {
    const filter = {
      display_title: "host",
      type: "text",
      values: ["node-"],
    };
    const Card = createFilterCard({ title: "host", filter });

    expect(renderer.create(Card)).toMatchSnapshot();
  });

  // NOTE:
  // This test used to rely on Enzyme's shallow rendering and .simulate().
  // It now uses React Testing Library to render into a real DOM container
  // and triggers the change via a user-like click on the checkbox. This
  // makes the test closer to actual runtime behavior and allows us to
  // drop the Enzyme dependency.
  test("FilterCard should send correct updates on selection of filters", async () => {
    let response = {};

    const handler = (obj) => {
      response = obj;
    };
    const filter = {
      display_title: "Status",
      categories: ["cat1", "correct", "wrong"],
      statuses: ["true", "false(reach)"],
      type: "status",
    };
    const Card = createFilterCard({
      title: "Status",
      filter,
      onFilterUpdate: handler,
    });
    const { container } = render(Card);

    const checkBox = container.querySelector('input[name="stat-true"]');

    expect(checkBox).not.toBeNull();

    await userEvent.click(checkBox);

    expect(response).toEqual({ values: ["true"], title: "Status" });
  });
});
