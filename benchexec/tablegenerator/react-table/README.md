This project was bootstrapped with [Create React App](https://github.com/facebook/create-react-app).

## Available Scripts

In the project directory, you can run:

### `npm start [<relative path to test data file>]`

Runs the app in the development mode with some test data.<br>
Open [http://localhost:3000](http://localhost:3000) to view it in the browser.

The page will reload if you make edits.<br>
You will also see any lint errors in the console.

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
for checking code style and best practices:

- `npx eslint src`<br>
  (use `--fix` to automatically apply fixes)
- `npx prettier $(find . \( -name build -o -name node_modules -o -name vendor \) -prune -type f -o -name "*.js" -o -name "*.json" -o -name "*.css" -o -name "*.scss") --ignore-path .gitignore --check`<br>
  (use `--write` to automatically reformat code)

## Learn More

- [React documentation](https://reactjs.org/)
- [react-table documentation](https://github.com/tannerlinsley/react-table/tree/v6)
- [react-vis documentation](https://uber.github.io/react-vis/documentation)
