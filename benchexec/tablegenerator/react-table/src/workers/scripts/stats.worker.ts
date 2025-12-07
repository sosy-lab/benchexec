// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

// COPY OF utils.js, as imports will not work here
/**
 * Function to safely add two numbers in a way that should mitigate errors
 * caused by inaccurate floating point operations in javascript
 * @param {Number|String} a - The base number
 * @param {Number|String} b - The number to add
 *
 * @returns {Number} The result of the addition
 */
const safeAdd = (a: any, b: any) => {
  let aNum = a;
  let bNum = b;

  if (typeof a === "string") {
    aNum = Number(a);
  }
  if (typeof b === "string") {
    bNum = Number(b);
  }

  if (Number.isInteger(aNum) || Number.isInteger(bNum)) {
    return aNum + bNum;
  }

  const aString = a.toString();
  const aLength = aString.length;
  const aDecimalPoint = aString.indexOf(".");
  const bString = b.toString();
  const bLength = bString.length;
  const bDecimalPoint = bString.indexOf(".");

  const length = Math.max(aLength - aDecimalPoint, bLength - bDecimalPoint) - 1;

  return Number((aNum + bNum).toFixed(length));
};

const mathStringMax = (a: any, b: any) => {
  const numA = Number(a);
  const numB = Number(b);
  return numA > numB ? a : b;
};

const mathStringMin = (a: any, b: any) => {
  const numA = Number(a);
  const numB = Number(b);
  return numA < numB ? a : b;
};

/**
 * This function either adds two numbers or increments the number
 * passed in the first parameter if the type is "status".
 * If the second parameter is not a number and the type is not status,
 * the first parameter will be returned
 *
 * @param {Number} a
 * @param {*} b
 * @param {String} type
 */
const maybeAdd = (a: any, b: any, type: any) => {
  if (Number(b)) {
    return safeAdd(a, b);
  }
  if (type === "status") {
    return a + 1;
  }
  return a;
};
const removeRoundOff = (num: any) => {
  const str = num.toString();
  if (str.match(/\..+?0{2,}\d$/)) {
    return Number(str.substr(0, str.length - 1));
  }
  return num;
};

const calculateMean = (values: any, allItems: any) => {
  const numMin = Number(values.min);
  const numMax = Number(values.max);
  if (numMin === -Infinity && numMax === Infinity) {
    values.avg = "NaN";
  } else if (numMin === -Infinity) {
    values.avg = "-Infinity";
  } else if (numMax === Infinity) {
    values.avg = "Infinity";
  } else {
    values.avg = removeRoundOff(values.sum / allItems.length);
  }
};

const calculateMedian = (values: any, allItems: any) => {
  if (allItems.length % 2 === 0) {
    const idx = allItems.length / 2;
    values.median =
      (Number(allItems[idx - 1].column) + Number(allItems[idx].column)) / 2.0;
  } else {
    values.median = allItems[Math.floor(allItems.length / 2.0)].column;
  }
};
const calculateStdev = (
  hasNegInf: any,
  hasPosInf: any,
  variance: any,
  size: any,
) => {
  if (hasNegInf && hasPosInf) {
    return "NaN";
  }
  if (hasNegInf || hasPosInf) {
    return Infinity;
  }
  return Math.sqrt(variance / size);
};

const parsePythonInfinityValues = (data: any) =>
  data.map((item: any) => {
    if (item.columnType === "status" || !item.column.endsWith("Inf")) {
      return item;
    }
    // We have a python Infinity value that we want to transfer to a string
    // that can be interpreted as a JavaScript Infinity value
    item.column = item.column.replace("Inf", "Infinity");
    return item;
  });

// If a bucket contains a NaN value, we can not perform any stat calculation
const shouldSkipBucket = (bucketMeta: any, key: any) => {
  if (bucketMeta[key] && bucketMeta[key].hasNaN) {
    return true;
  }
  return false;
};

/**
 * Function that keeps track of the max inputted decimal length of column values.
 * This is used for conditional formatting in the stats module to determine the maximum
 * amount of padded 0s
 *
 * @typedef UpdateMaxDecimalMetaInfoParam
 * @param {String} columnType - The type of the current column
 * @param {Object} column - The column object
 * @param {Object} bucket - The current stat bucket in context
 *
 * @param {UpdateMaxDecimalMetaInfoParam} param
 */
const updateMaxDecimalMetaInfo = ({ columnType, column, bucket }: any) => {
  if (columnType !== "status") {
    const [, decimal] = column.split(".");
    bucket.meta.maxDecimals = Math.max(
      bucket.meta.maxDecimals,
      decimal?.length ?? 0,
    );
  }
};

/**
 * @typedef  MetaInfo
 *  Additional metainformation to be used for post-processing (like number formatting)
 * @prop {string|null} type - The column type
 * @prop {number} maxDecimals - The maximum amount of decimals across all numbers in the bucket
 *                              used for number formatting
 */

/**
 * @typedef Bucket
 * Statistics to be displayed in the react table are calculated in buckets, each bucket representing one "row" in the
 * statistics table (total, correct, correct true, etc).
 * This object stores all accumulated information about this bucket.
 *
 * @prop {number} sum - The sum of the bucket
 * @prop {number} avg - The average of the bucket
 * @prop {number|string} max - The maximal value of the bucket
 * @prop {number} median - The median value of the bucket
 * @prop {number|string} min - The minimum value of the bucket
 * @prop {number} stdev - The standard deviation of the bucket
 * @prop {number} variance - The variance of the bucket
 * @prop {MetaInfo} [meta] - Meta information of the bucket
 */

onmessage = function (e) {
  const { data, transaction } = e.data;

  // template
  /** @const { Bucket } */
  const defaultObj = {
    sum: 0,
    avg: 0,
    max: "-Infinity",
    median: 0,
    min: "Infinity",
    stdev: 0,
    variance: 0,
  };

  /** @const {MetaInfo} */
  const metaTemplate = {
    type: null,
    maxDecimals: 0,
  };

  // Copy of the template with all values replaced with NaN
  const nanObj = { ...defaultObj };
  for (const objKey of Object.keys(nanObj)) {
    // @ts-expect-error TS(7053): Element implicitly has an 'any' type because expre... Remove this comment to see the full error message
    nanObj[objKey] = "NaN";
  }

  let copy = [...data].filter(
    (i) => i && i.column !== undefined && i.column !== null,
  );
  copy = parsePythonInfinityValues(copy);

  if (copy.length === 0) {
    // No data to perform calculations with
    postResult({ total: undefined }, transaction);
    return;
  }

  const { columnType } = copy[0];
  metaTemplate.type = columnType;

  copy.sort((a, b) => a.column - b.column);

  /** @type {Object.<string, Bucket>} */
  const buckets = {};
  const bucketNaNInfo = {}; // used to store NaN info of buckets

  /** @type {Bucket} */
  let total = { ...defaultObj, items: [], meta: { ...metaTemplate } };

  total.max = copy[copy.length - 1].column;
  total.min = copy[0].column;

  const totalNaNInfo = {
    hasNaN: copy.some((item) => {
      if (item.columnType !== "status" && isNaN(item.column)) {
        return true;
      }
      return false;
    }),
  };

  // Bucket setup with sum and min/max
  for (const item of copy) {
    const key = `${item.categoryType}_${item.resultType}`;
    const totalKey = `${item.categoryType}`;
    const { columnType: type, column, columnTitle: title } = item;
    // @ts-expect-error TS(2339): Property 'title' does not exist on type '{ items: ... Remove this comment to see the full error message
    if (!total.title) {
      // @ts-expect-error TS(2339): Property 'title' does not exist on type '{ items: ... Remove this comment to see the full error message
      total.title = title;
    }
    // @ts-expect-error TS(7053): Element implicitly has an 'any' type because expre... Remove this comment to see the full error message
    const bucket = buckets[key] || {
      ...defaultObj,
      title,
      items: [],
      meta: { ...metaTemplate },
    };

    // @ts-expect-error TS(7053): Element implicitly has an 'any' type because expre... Remove this comment to see the full error message
    const subTotalBucket = buckets[totalKey] || {
      ...defaultObj,
      title,
      items: [],
      meta: { ...metaTemplate },
    };

    const itemIsNaN = type !== "status" && isNaN(column);

    // if one item is NaN we store that info so we can default all
    // calculated values for this bucket to NaN
    if (itemIsNaN) {
      // @ts-expect-error TS(7053): Element implicitly has an 'any' type because expre... Remove this comment to see the full error message
      bucketNaNInfo[key] = { hasNaN: true };
      // @ts-expect-error TS(7053): Element implicitly has an 'any' type because expre... Remove this comment to see the full error message
      bucketNaNInfo[totalKey] = { hasNaN: true };

      // set all values for this bucket to NaN
      // @ts-expect-error TS(7053): Element implicitly has an 'any' type because expre... Remove this comment to see the full error message
      buckets[key] = { ...nanObj, title };
      // @ts-expect-error TS(7053): Element implicitly has an 'any' type because expre... Remove this comment to see the full error message
      buckets[totalKey] = { ...nanObj, title };
      continue;
    }

    // we check if we should skip calculation for these buckets
    const skipBucket = shouldSkipBucket(bucketNaNInfo, key);
    const skipSubTotal = shouldSkipBucket(bucketNaNInfo, totalKey);

    if (!skipBucket) {
      bucket.sum = maybeAdd(bucket.sum, column, type);
      updateMaxDecimalMetaInfo({ columnType, column, bucket });
    }
    if (!skipSubTotal) {
      subTotalBucket.sum = maybeAdd(subTotalBucket.sum, column, type);
      updateMaxDecimalMetaInfo({ columnType, column, bucket: subTotalBucket });
    }
    if (!totalNaNInfo.hasNaN) {
      total.sum = maybeAdd(total.sum, column, type);
      updateMaxDecimalMetaInfo({ columnType, column, bucket: total });
    }

    if (!isNaN(Number(column))) {
      if (!skipBucket) {
        bucket.max = mathStringMax(bucket.max, column);
        bucket.min = mathStringMin(bucket.min, column);
      }
      if (!skipSubTotal) {
        subTotalBucket.max = mathStringMax(subTotalBucket.max, column);
        subTotalBucket.min = mathStringMin(subTotalBucket.min, column);
      }
    }
    if (!skipBucket) {
      try {
        bucket.items.push(item);
      } catch (e) {
        // @ts-expect-error TS(2339): Property 'e' does not exist on type 'Console'.
        console.e({ bucket, bucketMeta: bucketNaNInfo, key });
      }
    }
    if (!skipSubTotal) {
      try {
        subTotalBucket.items.push(item);
      } catch (e) {
        // @ts-expect-error TS(2339): Property 'e' does not exist on type 'Console'.
        console.e({ subTotalBucket, bucketMeta: bucketNaNInfo, totalKey });
      }
    }

    // @ts-expect-error TS(7053): Element implicitly has an 'any' type because expre... Remove this comment to see the full error message
    buckets[key] = bucket;
    // @ts-expect-error TS(7053): Element implicitly has an 'any' type because expre... Remove this comment to see the full error message
    buckets[totalKey] = subTotalBucket;
  }

  for (const [bucket, values] of Object.entries(buckets)) {
    if (shouldSkipBucket(bucketNaNInfo, bucket)) {
      continue;
    }
    // @ts-expect-error TS(2571): Object is of type 'unknown'.
    calculateMean(values, values.items);

    // @ts-expect-error TS(2571): Object is of type 'unknown'.
    calculateMedian(values, values.items);
    // @ts-expect-error TS(7053): Element implicitly has an 'any' type because expre... Remove this comment to see the full error message
    buckets[bucket] = values;
  }
  const totalHasNaN = totalNaNInfo.hasNaN;

  if (totalHasNaN) {
    total = { ...total, ...nanObj };
  } else {
    calculateMean(total, copy);
    calculateMedian(total, copy);
  }

  for (const item of copy) {
    const { column } = item;
    if (isNaN(Number(column))) {
      continue;
    }
    const numCol = Number(column);
    const key = `${item.categoryType}_${item.resultType}`;
    const totalKey = `${item.categoryType}`;
    // @ts-expect-error TS(7053): Element implicitly has an 'any' type because expre... Remove this comment to see the full error message
    const bucket = buckets[key];
    // @ts-expect-error TS(7053): Element implicitly has an 'any' type because expre... Remove this comment to see the full error message
    const subTotalBucket = buckets[totalKey];
    const diffBucket = numCol - bucket.avg;
    const diffSubTotal = numCol - subTotalBucket.avg;
    const diffTotal = numCol - total.avg;
    total.variance += Math.pow(diffTotal, 2);
    bucket.variance += Math.pow(diffBucket, 2);
    subTotalBucket.variance += Math.pow(diffSubTotal, 2);
  }

  const totalHasNegInf = Number(total.min) === -Infinity;
  const totalHasPosInf = Number(total.max) === Infinity;
  // @ts-expect-error TS(2322): Type 'number | "NaN"' is not assignable to type 'n... Remove this comment to see the full error message
  total.stdev = calculateStdev(
    totalHasNegInf,
    totalHasPosInf,
    total.variance,
    copy.length,
  );

  for (const [bucket, values] of Object.entries(buckets)) {
    if (shouldSkipBucket(bucketNaNInfo, bucket)) {
      // @ts-expect-error TS(2769): No overload matches this call.
      for (const [key, val] of Object.entries(values)) {
        // @ts-expect-error TS(2571): Object is of type 'unknown'.
        values[key] = val.toString();
      }
      // @ts-expect-error TS(7053): Element implicitly has an 'any' type because expre... Remove this comment to see the full error message
      buckets[bucket] = values;
      continue;
    }
    // @ts-expect-error TS(2571): Object is of type 'unknown'.
    const valuesHaveNegInf = Number(values.min) === -Infinity;
    const valuesHavePosInf = Number(total.max) === Infinity;
    // @ts-expect-error TS(2571): Object is of type 'unknown'.
    values.stdev = calculateStdev(
      valuesHaveNegInf,
      valuesHavePosInf,
      // @ts-expect-error TS(2571): Object is of type 'unknown'.
      values.variance,
      // @ts-expect-error TS(2571): Object is of type 'unknown'.
      values.items.length,
    );

    // @ts-expect-error TS(2769): No overload matches this call.
    for (const [key, val] of Object.entries(values)) {
      if (key === "meta") {
        continue;
      }
      // @ts-expect-error TS(2571): Object is of type 'unknown'.
      values[key] = val.toString();
    }
    // clearing memory
    // @ts-expect-error TS(2571): Object is of type 'unknown'.
    delete values.items;
    // @ts-expect-error TS(2571): Object is of type 'unknown'.
    delete values.variance;
    // @ts-expect-error TS(7053): Element implicitly has an 'any' type because expre... Remove this comment to see the full error message
    buckets[bucket] = values;
  }

  for (const [key, value] of Object.entries(total)) {
    if (key === "meta") {
      continue;
    }
    // @ts-expect-error TS(7053): Element implicitly has an 'any' type because expre... Remove this comment to see the full error message
    total[key] = value.toString();
  }

  // @ts-expect-error TS(2790): The operand of a 'delete' operator must be optiona... Remove this comment to see the full error message
  delete total.items;
  // @ts-expect-error TS(2790): The operand of a 'delete' operator must be optiona... Remove this comment to see the full error message
  delete total.variance;

  const result = { columnType, total, ...buckets };
  postResult(result, transaction);
};

const postResult = (result: any, transaction: any) => {
  // handling in tests
  // @ts-expect-error TS(7041): The containing arrow function captures the global ... Remove this comment to see the full error message
  if (this.mockedPostMessage) {
    // @ts-expect-error TS(7041): The containing arrow function captures the global ... Remove this comment to see the full error message
    this.mockedPostMessage({ result, transaction });
    return;
  }
  postMessage({ result, transaction });
};
