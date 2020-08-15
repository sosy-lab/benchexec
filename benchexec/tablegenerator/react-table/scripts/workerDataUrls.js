const fs = require("fs");
const path = require("path");

const workerFilePath = path.join(__dirname, "../src/workers/scripts");
const dataUrlFile = path.join(__dirname, "../src/workers/dataUrls.js");

const template = "data:text/plain;base64,";

const workerFiles = fs.readdirSync(workerFilePath);

let output = "";
const workerNames = [];

for (const worker of workerFiles) {
  const workerName = worker.split(".")[0];
  workerNames.push(workerName);
  const workerPath = path.join(workerFilePath, worker);
  output += "\n";
  output += `const ${workerName} = "${template}${Buffer.from(
    fs.readFileSync(workerPath).toString(),
  ).toString("base64")}";`;
}
output += "\n\n\n";
output += `export { ${workerNames.join(", ")} };`;

fs.writeFileSync(dataUrlFile, output);

console.log("Injected data urls for workers");
