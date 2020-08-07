onmessage = function (e) {
  const { data, transaction } = e.data;

  let sum = 0;
  let stdev = 0;
  let avg = 0;
  let max = 0;
  let min = 0;
  let median = 0;

  const copy = [...data];
  copy.sort((a, b) => a - b);

  max = copy[copy.length - 1];
  min = copy[0];

  // calculation
  for (const item of copy) {
    sum += item;
  }
  avg = sum / copy.length;
  if (copy.length % 2 === 0) {
    // even, we need an extra step to calculate the median
    const idx = copy.length / 2;
    median = (copy[idx - 1] + copy[idx]) / 2.0;
  } else {
    // ezpz
    median = copy[Math.floor(copy.length / 2.0)];
  }

  // standard deviation
  let variance = 0;

  for (const item of copy) {
    const diff = item - avg;
    variance += Math.pow(diff, 2);
  }

  stdev = Math.sqrt(variance / copy.length);

  const result = { min, max, sum, avg, median, stdev };

  postMessage({ result, transaction });
};
