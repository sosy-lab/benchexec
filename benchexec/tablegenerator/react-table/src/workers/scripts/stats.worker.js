// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

const maybeAdd = (a, b, type) => {
  if (Number(b)) {
    return a + Number(b);
  }
  if (type === "status") {
    return a + 1;
  }
  return a;
};

const calculateMedian = (values, allItems) => {
  const numMin = Number(values.min);
  const numMax = Number(values.max);
  if (numMin === -Infinity && numMax === Infinity) {
    values.median = "NaN";
  } else if (numMin === -Infinity) {
    values.median = "-Infinity";
  } else if (numMax === Infinity) {
    values.median = "Infinity";
  } else {
    if (allItems.length % 2 === 0) {
      const idx = allItems.length / 2;
      values.median =
        (Number(allItems[idx - 1].column) + Number(allItems[idx].column)) / 2.0;
    } else {
      values.median = Number(
        allItems[Math.floor(allItems.length / 2.0)].column,
      );
    }
  }
};

const parsePythonInfinityValues = (data) =>
  data.map((item) => {
    if (item.columnType === "status" || !item.column.endsWith("Inf")) {
      return item;
    }
    // We have a python Infinity value that we want to transfer to a string
    // that can be interpreted as a JavaScript Infinity value
    item.column = item.column.replace("Inf", "Infinity");
    return item;
  });

const shouldSkipBucket = (bucketMeta, key) => {
  if (bucketMeta[key] && bucketMeta[key].hasNaN) {
    return true;
  }
  return false;
};

onmessage = function (e) {
  const { data, transaction } = e.data;

  const defaultObj = {
    sum: 0,
    avg: 0,
    max: 0,
    median: 0,
    min: Infinity,
    stdev: 0,
    variance: 0,
  };

  const nanObj = { ...defaultObj };
  for (const objKey of Object.keys(nanObj)) {
    nanObj[objKey] = "NaN";
  }

  let copy = [...data].filter(
    (i) => i && i.column !== undefined && i.column !== null,
  );
  copy = parsePythonInfinityValues(copy);

  if (copy.length === 0) {
    postResult({ total: undefined }, transaction);
    return;
  }

  copy.sort((a, b) => a.column - b.column);

  const buckets = {};
  const bucketMeta = {}; // used to store various properties of buckets

  let total = { ...defaultObj, items: [] };

  total.max = copy[copy.length - 1].column;
  total.min = copy[0].column;

  const totalMeta = {
    hasNaN: copy.some((item) => {
      if (item.columnType !== "status" && isNaN(item.column)) {
        return true;
      }
      return false;
    }),
    hasPosInf: total.max === Infinity,
    hasNegInf: total.min === -Infinity,
  };

  // Bucket setup with sum and min/max
  for (const item of copy) {
    const key = `${item.categoryType}-${item.resultType}`;
    const totalKey = `${item.categoryType}-total`;
    const { columnType: type, column, columnTitle: title } = item;
    const bucket = buckets[key] || {
      ...defaultObj,
      title,
      items: [],
    };

    const subTotalBucket = buckets[totalKey] || {
      ...defaultObj,
      title,
      items: [],
    };

    const itemIsNaN = type !== "status" && isNaN(column);

    // if one item is NaN we store that info so we can default all
    // calculated values for this bucket to NaN
    if (itemIsNaN) {
      bucketMeta[key] = { hasNaN: true };
      bucketMeta[totalKey] = { hasNaN: true };

      // set all values for this bucket to NaN
      buckets[key] = { ...nanObj, title };
      buckets[totalKey] = { ...nanObj, title };
      continue;
    }

    // we check if we should skip calculation for these buckets
    const skipBucket = shouldSkipBucket(bucketMeta, key);
    const skipSubTotal = shouldSkipBucket(bucketMeta, totalKey);

    if (!skipBucket) {
      bucket.sum = maybeAdd(bucket.sum, column, type);
    }
    if (!skipSubTotal) {
      subTotalBucket.sum = maybeAdd(subTotalBucket.sum, column, type);
    }
    if (!totalMeta.hasNaN) {
      total.sum = maybeAdd(total.sum, column, type);
    }

    if (!isNaN(Number(column))) {
      const numCol = Number(column);
      if (!skipBucket) {
        bucket.max = Math.max(bucket.max, numCol);
        bucket.min = Math.min(bucket.min, numCol);
      }
      if (!skipSubTotal) {
        subTotalBucket.max = Math.max(subTotalBucket.max, numCol);
        subTotalBucket.min = Math.min(subTotalBucket.min, numCol);
      }
    }
    if (!skipBucket) {
      try {
        bucket.items.push(item);
      } catch (e) {
        console.e({ bucket, bucketMeta, key });
      }
    }
    if (!skipSubTotal) {
      try {
        subTotalBucket.items.push(item);
      } catch (e) {
        console.e({ subTotalBucket, bucketMeta, totalKey });
      }
    }

    buckets[key] = bucket;
    buckets[totalKey] = subTotalBucket;
  }

  for (const [bucket, values] of Object.entries(buckets)) {
    if (shouldSkipBucket(bucketMeta, bucket)) {
      continue;
    }
    values.avg = values.sum / values.items.length;

    calculateMedian(values, values.items);
    buckets[bucket] = values;
  }
  const totalHasNaN = totalMeta.hasNaN;

  if (totalHasNaN) {
    total = { ...nanObj };
  } else {
    total.avg = total.sum / copy.length;
    calculateMedian(total, copy);
  }

  for (const item of copy) {
    const { column } = item;
    if (isNaN(Number(column))) {
      continue;
    }
    const numCol = Number(column);
    const key = `${item.categoryType}-${item.resultType}`;
    const totalKey = `${item.categoryType}-total`;
    const bucket = buckets[key];
    const subTotalBucket = buckets[totalKey];
    const diffBucket = numCol - bucket.avg;
    const diffSubTotal = numCol - subTotalBucket.avg;
    const diffTotal = numCol - total.avg;
    total.variance += Math.pow(diffTotal, 2);
    bucket.variance += Math.pow(diffBucket, 2);
    subTotalBucket.variance += Math.pow(diffSubTotal, 2);
  }

  total.stdev = Math.sqrt(total.variance / copy.length);

  for (const [bucket, values] of Object.entries(buckets)) {
    if (shouldSkipBucket(bucketMeta, bucket)) {
      for (const [key, val] of Object.entries(values)) {
        values[key] = val.toString();
      }
      buckets[bucket] = values;
      continue;
    }
    values.stdev = Math.sqrt(values.variance / values.items.length);

    for (const [key, val] of Object.entries(values)) {
      values[key] = val.toString();
    }
    // clearing memory
    delete values.items;
    delete values.variance;
    buckets[bucket] = values;
  }

  for (const [key, value] of Object.entries(total)) {
    total[key] = value.toString();
  }

  delete total.items;
  delete total.variance;

  const result = { total, ...buckets };

  // handling in tests
  postResult(result, transaction);
};

const postResult = (result, transaction) => {
  // handling in tests
  if (this.mockedPostMessage) {
    this.mockedPostMessage({ result, transaction });
    return;
  }
  postMessage({ result, transaction });
};
