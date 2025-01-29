<!--
This file is part of BenchExec, a framework for reliable benchmarking:
https://github.com/sosy-lab/benchexec

SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>

SPDX-License-Identifier: Apache-2.0
-->

This project was bootstrapped with [Create React App](https://github.com/facebook/create-react-app).

## Dependencies

This project requires Node.js 12 or newer.

## Available Scripts

In the project directory, you can run:

### `npm start [<relative path to test data file>]`

Runs the app in the development mode with some test data.<br>
Open [http://localhost:3000](http://localhost:3000) to view it in the browser.

The page will reload if you make edits.<br>
You will also see any lint errors in the console.

Some of the links in the table tab work and point to files
that allow testing of components like our table-definition viewer.

You are also able to pass an optional `relative path to test data file` to be used instead of the
default file under `./src/data/data.json`.

A selection of test files can be found under `<project-root>/tablegenerator/test_integration/expected` in form
of HTML files filled with plain JSON.

### `npm test`

Launches the test runner in the interactive watch mode.<br>
See the section about [running tests](https://facebook.github.io/create-react-app/docs/running-tests) for more information.

### `npm run build`

Builds the app for production to the `build` folder.<br>
It correctly bundles React in production mode and optimizes the build for the best performance.

This needs to be done before committing changes to the JavaScript and style files.

## Suggested Development Environment

The easiest way to get a suitable development environment
for running the above scripts is to use Docker with the following command:

```
docker run --network=host -v $(pwd)/..:$(pwd)/..:rw -w $(pwd) -it node bash
```

## Code Style and Linting

We use [ESLint](https://eslint.org/) and [Prettier](https://prettier.io/)
for checking code style and best practices.

Run `npm run lint` to check the code and `npm run lint:fix` to apply fixes and the code formatter.

## Utilities

- For viewing outdated dependencies: `npm outdated`
- Updating dependencies within one major version: `npm update` and `npm update --depth=10` for transitive dependencies
- Upgrading dependencies across major versions: [npm-check-updates](https://www.npmjs.com/package/npm-check-updates) or [npm-check](https://www.npmjs.com/package/npm-check)
- Upgrading `react-scripts` needs to be done manually according to their instructions in the [changelog](https://github.com/facebook/create-react-app/releases).

## Learn More

- [React documentation](https://reactjs.org/)
- [Documentation of create-react-app and react-scripts](https://create-react-app.dev/) (our build system)
- [react-table documentation](https://github.com/tannerlinsley/react-table/tree/v6)
- [react-vis documentation](https://uber.github.io/react-vis/documentation)
