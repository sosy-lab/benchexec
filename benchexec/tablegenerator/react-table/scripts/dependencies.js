/* SPDX-License-Identifier: Apache-2.0
 *
 * BenchExec is a framework for reliable benchmarking.
 * This file is part of BenchExec.
 * Copyright (C) Dirk Beyer. All rights reserved.
 */
"use strict";

const checker = require("license-checker");
const fs = require("fs");

const stripPrefix = (str, prefix) =>
  prefix && str.startsWith(prefix)
    ? str.substring(prefix.length).trimStart()
    : str;

console.log("Checking licenses of dependencies...");
checker.init(
  {
    start: ".",
    production: true,
    excludePrivatePackages: true,
    onlyAllow: "BSD-3-Clause; CC-BY-4.0; ISC; MIT; Zlib",
    customFormat: {
      name: "",
      version: "",
      licenses: "",
      copyright: "",
      repository: "",
      licenseText: ""
    }
  },
  function(err, packages) {
    if (err) {
      console.log(err);
      process.exit(1);
    } else {
      // zip.js is a special case because we do not retrieve it from npm
      packages["zip.js"] = {
        name: "zip.js",
        version: "3e79208",
        repository: "https://github.com/gildas-lormeau/zip.js",
        copyright: "Copyright (c) 2013 Gildas Lormeau. All rights reserved.",
        licenses: "BSD-3-Clause",
        licenseText: fs.readFileSync("src/vendor/zip.js/LICENSE.txt", "utf-8")
      };

      // We store some metadata for each package, including its license.
      // Because licenses are large, we deduplicate them:
      // We store each occurring license in licensesTexts and refer to it via its index.
      const licenseTextMapping = {};
      const licenseTexts = Array();
      const dependencies = Array();
      Object.keys(packages).forEach(key => {
        const dependency = packages[key];

        var license = dependency.licenseText;

        if (dependency.licenses == "(MIT OR GPL-3.0)") {
          // Trim long GPL from dual-licenses dependency, we choose MIT anyway
          const gplStart = license.indexOf("GPL version 3");
          if (gplStart) {
            license = license.substring(0, gplStart).trimEnd();
          }
        }

        // Many license texts differ only in a small header.
        // Because we show the copyright and the license name separately anyway,
        // we can remove such prefixes and increase the chance of deduplication.
        // This list is a heuristic of currently occuring prefixes.
        [
          "The ISC License",
          "MIT License",
          "The MIT License (MIT)",
          "(The MIT License)",
          "This software is released under the MIT license:",
          dependency.copyright, // copyright declaration copied to license
          dependency.copyright.split(".")[0], // first sentence of copyright
          dependency.copyright.includes("All rights reserved.")
            ? "All rights reserved." // this sentence if also in copyright
            : ""
        ].forEach(prefix => (license = stripPrefix(license, prefix)));

        // Furthermore, some license texts differ only in whitespace,
        // so for deduplication, we normalize whitespace.
        const normalizedLicense = license.replace(/\s/g, " ");

        var licenseId;
        if (normalizedLicense in licenseTextMapping) {
          licenseId = licenseTextMapping[normalizedLicense];
        } else {
          licenseId = licenseTexts.push(license) - 1;
          licenseTextMapping[normalizedLicense] = licenseId;
        }

        dependencies.push({
          name: dependency.name,
          version: dependency.version,
          repository: dependency.repository,
          copyright: dependency.copyright,
          licenses: dependency.licenses,
          licenseId: licenseId
        });
      });
      const dependencyData = JSON.stringify({
        dependencies: dependencies,
        licenses: licenseTexts
      });
      console.info(
        "Found %d dependencies under %s, adding %d bytes of metadata.",
        dependencies.length,
        [...new Set(dependencies.map(d => d.licenses))].join(", "),
        dependencyData.length
      );
      fs.writeFile("src/data/dependencies.json", dependencyData, err => {
        if (err) {
          console.log(err);
          process.exit(1);
        }
      });
    }
  }
);
