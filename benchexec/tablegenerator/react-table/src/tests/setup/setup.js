// enzyme
import { configure } from "enzyme";
import Adapter from "enzyme-adapter-react-16";

// mock uniqid to have consistent names
// https://stackoverflow.com/a/44538270/396730
jest.mock("uniqid", () => (i) => i + "uniqid");

configure({ adapter: new Adapter() });
