// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

const fs = require("fs");
const path = require("path");

const workerFilePath = path.join(__dirname, "../src/workers/scripts");
const dataUrlFile = path.join(__dirname, "../src/workers/dataUrls.js");

const template = "data:text/plain;base64,";

const workerFiles = fs.readdirSync(workerFilePath);

let output = `
// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
`;
const workerNames = [];

for (const worker of workerFiles) {
  const workerName = worker.split(".")[0];
  workerNames.push(workerName);
  const workerPath = path.join(workerFilePath, worker);
  const workerScript = fs.readFileSync(workerPath);
  output += workerScript
    .toString()
    .match(/^ *\/\/\s?SPDX-.*?$/gim)
    .join("\n//\n");
  output += "\n\n";
  output += `const ${workerName} = "${template}${Buffer.from(
    workerScript,
  ).toString("base64")}";`;
}
output += "\n\n\n";
output += `export { ${workerNames.join(", ")} };`;

fs.writeFileSync(dataUrlFile, output);

console.log("Injected data urls for workers");
