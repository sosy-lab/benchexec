import React from "react";
import Overview from "../components/Overview";
import Reset from "../components/Reset.js";
// import { shallow } from "enzyme";
import renderer from "react-test-renderer";
// import Utils from "../utils/utils";

// const data = require("../data/data.json");

it("snapshot test Overview", () => {
	const overview = renderer.create(<Overview />).toJSON();
	// const overviewInstance = overview.getInstance();

	const component = renderer
		.create(
			<Reset resetFilters={overview.resetFilters} />
		).toJSON();
	expect(component).toMatchSnapshot();
});
