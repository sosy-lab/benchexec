// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

const maybeAdd = (a, b) => {
  if (Number(b)) {
    return a + b;
  }
  return a + 1;
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
    items: [],
  };

  const copy = [...data];
  const buckets = {};
  copy.sort((a, b) => a.column - b.column);

  const total = { ...defaultObj };

  total.max = copy[copy.length - 1].column;
  total.min = copy[0].column;

  // calculation
  for (const item of copy) {
    const key = `${item.categoryType}-${item.resultType}`;
    const totalKey = `${item.categoryType}-total`;
    const bucket = buckets[key] || {
      ...defaultObj,
    };
    const subTotalBucket = buckets[totalKey] || { ...defaultObj };
    bucket.sum = maybeAdd(bucket.sum, item.column);
    bucket.max = Math.max(bucket.max, item.column);
    bucket.min = Math.min(bucket.min, item.column);
    bucket.items.push(item);

    subTotalBucket.sum = maybeAdd(subTotalBucket.sum, item.column);
    subTotalBucket.max = Math.max(subTotalBucket.max, item.column);
    subTotalBucket.min = Math.min(subTotalBucket.min, item.column);
    subTotalBucket.items.push(item);
    total.sum = maybeAdd(total.sum, item.column);
    buckets[key] = bucket;
    buckets[totalKey] = subTotalBucket;
  }
  for (const [bucket, values] of Object.entries(buckets)) {
    values.avg = values.sum / values.items.length;
    if (values.items.length % 2 === 0) {
      const idx = values.items.length / 2;
      values.median =
        (values.items[idx - 1].column + values.items[idx].column) / 2.0;
    } else {
      values.median =
        values.items[Math.floor(values.items.length / 2.0)].column;
    }
    buckets[bucket] = values;
  }
  total.avg = total.sum / copy.length;
  if (copy.length % 2 === 0) {
    // even, we need an extra step to calculate the median
    const idx = copy.length / 2;
    total.median = (copy[idx - 1].column + copy[idx].column) / 2.0;
  } else {
    // ezpz
    total.median = copy[Math.floor(copy.length / 2.0)].column;
  }

  for (const item of copy) {
    const bucket = buckets[`${item.categoryType}-${item.resultType}`];
    const totalKey = `${item.categoryType}-total`;
    const subTotalBucket = buckets[totalKey];
    const diffBucket = item.column - bucket.avg;
    const diffSubTotal = item.column - subTotalBucket.avg;
    const diffTotal = item.column - total.avg;
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

  // handling of tests
  // console.log({
  //   evaluation: !!this.mockedPostMessage,
  //   value: this.mockedPostMessage,
  // });
  if (this.mockedPostMessage) {
    this.mockedPostMessage({ result, transaction });
    return;
  }
  postMessage({ result, transaction });
};
