/* SPDX-License-Identifier: Apache-2.0
 *
 * BenchExec is a framework for reliable benchmarking.
 * This file is part of BenchExec.
 * Copyright (C) Dirk Beyer. All rights reserved.
 */
const path = require("path");

module.exports = {
  webpack: function override(config, webpackEnv) {
    const isEnvDevelopment = webpackEnv === "development";

    // main configuration of output files:
    // two bundles, one for our code, one for dependencies
    config.output.filename = "bundle.min.js";
    config.output.chunkFilename = "[name].min.js";
    config.optimization.runtimeChunk = false;
    config.optimization.splitChunks = {
      chunks: "all",
      cacheGroups: {
        vendors: {
          chunks: "all",
          name: "vendors",
          test: /(node_modules|src\/data\/dependencies\.json|src\/vendor)/,
        },
      },
    };

    // same for CSS files
    const cssConfig = config.plugins.find(
      (p) => p.constructor.name === "MiniCssExtractPlugin",
    );
    if (cssConfig) {
      cssConfig.options.filename = "bundle.min.css";
      cssConfig.options.chunkFilename = "[name].min.css";
    }

    // Don't extract license comments, we bundle them separately
    config.optimization.minimizer.find(
      (m) => m.constructor.name === "TerserPlugin",
    ).options.extractComments = false;

    // Make vendor bundle change less often even if our own code changes.
    config.optimization.occurrenceOrder = false;

    // For consistency with previous configs
    delete config.output.jsonpFunction;

    // Enable ignore option of eslint config (which is the one that has eslintPath)
    // to honour our exclusions
    const isEslintConfig = (e) => e.options.eslintPath;
    const eslintOptions = config.module.rules
      .find((r) => r.use && r.use.some(isEslintConfig))
      .use.find(isEslintConfig).options;
    eslintOptions.ignore = true;

    if (isEnvDevelopment) {
      // Make @data resolve to our dummy data
      const dataPath = process.env.DATA || "src/data/data.json";
      config.resolve.alias["@data"] = path.resolve(__dirname, dataPath);
    }

    return config;
  },

  jest: function (config) {
    // In tests we want to skip loading the libraries from src/vendor/,
    // so we insert a pattern in the transform key that lets Jest replace
    // those files with dummy values when imported.
    // We cannot set this key in package.json because it needs to be the first.
    const fileTransformScript = Object.values(config.transform).find((e) =>
      e.endsWith("fileTransform.js"),
    );
    config.transform = {
      "^(.*[\\\\/])?src[\\\\/]vendor[\\\\/].*$": fileTransformScript,
      ...config.transform,
    };

    return config;
  },
};
