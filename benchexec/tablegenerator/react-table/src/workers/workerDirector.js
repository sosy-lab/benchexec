// Content of ./scripts/stats.worker.js transformed into a data url to
// deal with Chrome being unable to load WebWorkers when opened using
// the file:// protocol https://stackoverflow.com/questions/21408510/chrome-cant-load-web-worker
const statsWorkerDataUrl =
  "data:text/plain;base64,b25tZXNzYWdlID0gZnVuY3Rpb24gKGUpIHsKICBjb25zdCB7IGRhdGEsIHRyYW5zYWN0aW9uIH0gPSBlLmRhdGE7CgogIGxldCBzdW0gPSAwOwogIGxldCBzdGRldiA9IDA7CiAgbGV0IGF2ZyA9IDA7CiAgbGV0IG1heCA9IDA7CiAgbGV0IG1pbiA9IDA7CiAgbGV0IG1lZGlhbiA9IDA7CgogIGNvbnN0IGNvcHkgPSBbLi4uZGF0YV07CiAgY29weS5zb3J0KChhLCBiKSA9PiBhIC0gYik7CgogIG1heCA9IGNvcHlbY29weS5sZW5ndGggLSAxXTsKICBtaW4gPSBjb3B5WzBdOwoKICAvLyBjYWxjdWxhdGlvbgogIGZvciAoY29uc3QgaXRlbSBvZiBjb3B5KSB7CiAgICBzdW0gKz0gaXRlbTsKICB9CiAgYXZnID0gc3VtIC8gY29weS5sZW5ndGg7CiAgaWYgKGNvcHkubGVuZ3RoICUgMiA9PT0gMCkgewogICAgLy8gZXZlbiwgd2UgbmVlZCBhbiBleHRyYSBzdGVwIHRvIGNhbGN1bGF0ZSB0aGUgbWVkaWFuCiAgICBjb25zdCBpZHggPSBjb3B5Lmxlbmd0aCAvIDI7CiAgICBtZWRpYW4gPSAoY29weVtpZHggLSAxXSArIGNvcHlbaWR4XSkgLyAyLjA7CiAgfSBlbHNlIHsKICAgIC8vIGV6cHoKICAgIG1lZGlhbiA9IGNvcHlbTWF0aC5mbG9vcihjb3B5Lmxlbmd0aCAvIDIuMCldOwogIH0KCiAgLy8gc3RhbmRhcmQgZGV2aWF0aW9uCiAgbGV0IHZhcmlhbmNlID0gMDsKCiAgZm9yIChjb25zdCBpdGVtIG9mIGNvcHkpIHsKICAgIGNvbnN0IGRpZmYgPSBpdGVtIC0gYXZnOwogICAgdmFyaWFuY2UgKz0gTWF0aC5wb3coZGlmZiwgMik7CiAgfQoKICBzdGRldiA9IE1hdGguc3FydCh2YXJpYW5jZSAvIGNvcHkubGVuZ3RoKTsKCiAgY29uc3QgcmVzdWx0ID0geyBtaW4sIG1heCwgc3VtLCBhdmcsIG1lZGlhbiwgc3RkZXYgfTsKCiAgcG9zdE1lc3NhZ2UoeyByZXN1bHQsIHRyYW5zYWN0aW9uIH0pOwp9Owo=";

const WORKER_POOLS = [
  {
    template: statsWorkerDataUrl,
    poolSize: 8,
    name: "stats",
  },
];

const queue = [];

const refTable = {};

let transaction = 1;

const handleWorkerMessage = ({ data: message }, worker) => {
  const { transaction, result } = message;
  const callback = refTable[transaction];
  worker.busy = false;
  callback(result);
  // clear entry
  delete refTable[transaction];
};

const workerPool = WORKER_POOLS.map(({ template, poolSize, name }) => {
  const pool = [];
  for (let i = 0; i < poolSize; i += 1) {
    const worker = new Worker(template);
    const workerObj = { worker, busy: false };
    worker.onmessage = (msg) => handleWorkerMessage(msg, workerObj);

    pool.push(workerObj);
  }
  return { name, pool };
}).reduce((acc, { name, pool }) => ({ ...acc, [name]: pool }), {});

const reserveWorker = (name) => {
  const worker = workerPool[name].filter((w) => !w.busy)[0];
  if (worker) {
    if (worker.busy) {
      return null;
    }
    worker.busy = true;
    return worker;
  }
  return null;
};

const processQueue = () => {
  const item = queue.shift();
  if (item) {
    const reservedWorker = reserveWorker(item.name);
    if (!reservedWorker) {
      queue.unshift(item);
      setImmediate(processQueue);
      return;
    }
    const ourTransaction = transaction;
    transaction += 1;
    const meta = {
      data: item.data,
      transaction: ourTransaction,
    };
    refTable[ourTransaction] = item.callback;
    reservedWorker.worker.postMessage(meta);
    setImmediate(processQueue);
  }
};

const enqueue = async ({ name, data }) =>
  new Promise((resolve) => {
    queue.push({ name, data, callback: resolve });
    setImmediate(processQueue);
  });

export { enqueue };
