// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

// Import all parts of zip.js (https://github.com/gildas-lormeau/zip.js)
// and re-export as proper module.

// The imports-loader wraps the file content in (function () { ... }).call(window);
// This is necessary such that zip.js can register itself as it expects,
// and because zip-ext and inflate require zip to be attached to the window object.
// https://github.com/webpack-contrib/imports-loader
require("imports-loader?wrapper=window!./zip.js");
require("imports-loader?wrapper=window!./zip-ext.js");
require("imports-loader?wrapper=window!./inflate.js");
zip.useWebWorkers = false;

module.exports = zip;
