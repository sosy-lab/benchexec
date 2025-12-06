// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

// Content of ./scripts/stats.worker.js transformed into a data url to
// deal with Chrome being unable to load WebWorkers when opened using
// the file:// protocol https://stackoverflow.com/questions/21408510/chrome-cant-load-web-worker

// @ts-expect-error TS(2307): Cannot find module './dataUrls' or its correspondi... Remove this comment to see the full error message
import { stats as statsWorkerDataUrl } from "./dataUrls";
require("setimmediate"); // provides setImmediate and clearImmediate

const WORKER_POOLS = [
  {
    template: statsWorkerDataUrl,
    poolSize: 8,
    name: "stats",
  },
];

const queue: any = [];

// Store that maps callback functions to a worker transaction number
const refTable = {};

let transaction = 1;

// @ts-expect-error TS(7031): Binding element 'message' implicitly has an 'any' ... Remove this comment to see the full error message
const handleWorkerMessage = ({ data: message }, worker: any) => {
  const { transaction, result } = message;
  // @ts-expect-error TS(7053): Element implicitly has an 'any' type because expre... Remove this comment to see the full error message
  const callback = refTable[transaction];
  worker.busy = false;
  callback(result);
  // clear entry
  // @ts-expect-error TS(7053): Element implicitly has an 'any' type because expre... Remove this comment to see the full error message
  delete refTable[transaction];
};

// Pool population
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

// gets the first idle worker and reserves it for job dispatch
const reserveWorker = (name: any) => {
  // @ts-expect-error TS(7053): Element implicitly has an 'any' type because expre... Remove this comment to see the full error message
  const worker = workerPool[name].filter((w: any) => !w.busy)[0];
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
      // pushes the function back onto the stack for
      // execution on next cycle of the event loop
      setImmediate(processQueue);
      return;
    }
    const ourTransaction = transaction;
    transaction += 1;
    const meta = {
      data: item.data,
      transaction: ourTransaction,
    };
    // @ts-expect-error TS(7053): Element implicitly has an 'any' type because expre... Remove this comment to see the full error message
    refTable[ourTransaction] = item.callback;
    reservedWorker.worker.postMessage(meta);
    setImmediate(processQueue);
  }
};

/**
 * Registers a new job request and wraps it in a promise that resolves
 * on completion of dispatched job.
 *
 * @param {object} options
 */
const enqueue = async ({ name, data }: any) =>
  new Promise((resolve) => {
    queue.push({ name, data, callback: resolve });
    setImmediate(processQueue);
  });

export { enqueue };
