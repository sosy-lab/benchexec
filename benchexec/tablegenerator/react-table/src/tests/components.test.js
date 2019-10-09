// react standard
import React from "react";
import renderer from "react-test-renderer";

// enzyme
import { shallow, configure } from "enzyme";
import Adapter from 'enzyme-adapter-react-16';

// components
import Overview from "../components/Overview";
import Reset from "../components/Reset.js";
import Summary from "../components/Summary.js";
// import Utils from "../utils/utils";

configure({adapter: new Adapter()});

let overview, overviewJson, overviewInstance;

beforeAll(() => {
	// IMPORTANT! - data should remain the same to keep the table snapshot correct.
	// maybe provide own simple data for tests
	window.data = require('../data/data.json'); 

	overview = renderer.create(<Overview />);
	overviewJson = overview.toJSON();
	overviewInstance = overview.getInstance();
});

test('Click on reset button stops button from rendering', () => {
	let isFiltered = true;

	const resetBtn = shallow(<Reset isFiltered={isFiltered} resetFilters={() => isFiltered = false} />);
  
	expect(resetBtn.text()).toEqual('Reset Filters');
  
	resetBtn.simulate('click');
  
	expect(resetBtn).toEqual({});
});

it("Render reset button", () => {
	const component = renderer
		.create(
			<Reset isFiltered={true} />
		).toJSON();

	expect(component).toMatchSnapshot();
});

it("Hide reset button", () => {
	const component = renderer
		.create(
			<Reset isFiltered={false} />
		).toJSON();

	expect(component).toMatchSnapshot();
});

it("Render Summary", () => {
	const component = renderer
		.create(
			<Summary    
				tools={overviewInstance.originalTools}
				tableHeader={overviewInstance.tableHeader}
				selectColumn={overviewInstance.toggleSelectColumns}
				stats = {overviewInstance.stats}
				prepareTableValues = {overviewInstance.prepareTableValues}
				getRunSets={overviewInstance.getRunSets}
				changeTab= {overviewInstance.changeTab} />
		).toJSON();

	expect(component).toMatchSnapshot();
});
