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

  const copy = [...data];
  const buckets = {};
  copy.sort((a, b) => a.column - b.column);

  const total = { ...defaultObj, items: [] };

  total.max = copy[copy.length - 1].column;
  total.min = copy[0].column;

  // calculation
  for (const item of copy) {
    const key = `${item.categoryType}-${item.resultType}`;
    const totalKey = `${item.categoryType}-total`;
    const bucket = buckets[key] || {
      ...defaultObj,
      items: [],
    };
    const { columnType: type, column } = item;

    const subTotalBucket = buckets[totalKey] || {
      ...defaultObj,
      items: [],
    };

    bucket.sum = maybeAdd(bucket.sum, column, type);
    subTotalBucket.sum = maybeAdd(subTotalBucket.sum, column, type);

    if (!isNaN(Number(column))) {
      const numCol = Number(column);
      bucket.max = Math.max(bucket.max, numCol);
      bucket.min = Math.min(bucket.min, numCol);
      subTotalBucket.max = Math.max(subTotalBucket.max, numCol);
      subTotalBucket.min = Math.min(subTotalBucket.min, numCol);
    } else {
    }

    total.sum = maybeAdd(total.sum, column, type);

    bucket.items.push(item);
    subTotalBucket.items.push(item);

    buckets[key] = bucket;
    buckets[totalKey] = subTotalBucket;
  }

  for (const [bucket, values] of Object.entries(buckets)) {
    values.avg = values.sum / values.items.length;

    if (values.items.length % 2 === 0) {
      const idx = values.items.length / 2;
      values.median =
        (Number(values.items[idx - 1].column) +
          Number(values.items[idx].column)) /
        2.0;
    } else {
      values.median = Number(
        values.items[Math.floor(values.items.length / 2.0)].column,
      );
    }
    buckets[bucket] = values;
  }
  total.avg = total.sum / copy.length;
  if (copy.length % 2 === 0) {
    // even, we need an extra step to calculate the median
    const idx = copy.length / 2;
    total.median =
      (Number(copy[idx - 1].column) + Number(copy[idx].column)) / 2.0;
  } else {
    // ezpz
    total.median = Number(copy[Math.floor(copy.length / 2.0)].column);
  }

  for (const item of copy) {
    const { column } = item;
    if (isNaN(Number(column))) {
      continue;
    }
    const numCol = Number(column);
    const bucket = buckets[`${item.categoryType}-${item.resultType}`];
    const totalKey = `${item.categoryType}-total`;
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
    values.stdev = Math.sqrt(values.variance / values.items.length);
    // clearing memory
    delete values.items;
    delete values.variance;
    buckets[bucket] = values;
  }

  delete total.items;
  delete total.variance;

  const result = { total, ...buckets };

  // handling in tests
  if (this.mockedPostMessage) {
    this.mockedPostMessage({ result, transaction });
    return;
  }
  postMessage({ result, transaction });
};
