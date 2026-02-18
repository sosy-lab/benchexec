// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

// Content of ./scripts/stats.worker.js transformed into a data url to
// deal with Chrome being unable to load WebWorkers when opened using
// the file:// protocol https://stackoverflow.com/questions/21408510/chrome-cant-load-web-worker

import { stats as statsWorkerDataUrl } from "./dataUrls";
require("setimmediate"); // provides setImmediate and clearImmediate

// ===============
// Worker Director Types
// ===============

type WorkerPoolName = "stats";

type DataUrlString = string;

interface WorkerPoolConfig {
  template: DataUrlString;
  poolSize: number;
  name: WorkerPoolName;
}

interface WorkerWrapper {
  worker: Worker;
  busy: boolean;
}

interface WorkerPoolsByName {
  stats: WorkerWrapper[];
}

/** Result returned by a worker. */
type WorkerResult = unknown;

interface WorkerIncomingMessage {
  transaction: number;
  result: WorkerResult;
}

interface WorkerOutgoingMessage<TData> {
  data: TData;
  transaction: number;
}

interface QueueItem<TData> {
  name: WorkerPoolName;
  data: TData;
  callback: (result: WorkerResult) => void;
}

interface EnqueueOptions<TData> {
  name: WorkerPoolName;
  data: TData;
}

const WORKER_POOLS: WorkerPoolConfig[] = [
  {
    template: statsWorkerDataUrl,
    poolSize: 8,
    name: "stats",
  },
];

const queue: Array<QueueItem<unknown>> = [];

// Store that maps callback functions to a worker transaction number
const refTable = new Map<number, (result: WorkerResult) => void>();

let transaction = 1;

const handleWorkerMessage = (
  { data: message }: MessageEvent<WorkerIncomingMessage>,
  worker: WorkerWrapper,
): void => {
  const { transaction: messageTransaction, result } = message;
  const callback = refTable.get(messageTransaction);
  worker.busy = false;

  if (callback) {
    callback(result);
    // clear entry
    refTable.delete(messageTransaction);
  }
};

// Pool population
const workerPool: WorkerPoolsByName = WORKER_POOLS.map(
  ({ template, poolSize, name }) => {
    const pool: WorkerWrapper[] = [];
    for (let i = 0; i < poolSize; i += 1) {
      const worker = new Worker(template);
      const workerObj: WorkerWrapper = { worker, busy: false };
      worker.onmessage = (msg) => handleWorkerMessage(msg, workerObj);

      pool.push(workerObj);
    }
    return { name, pool };
  },
).reduce(
  (acc, { name, pool }) => ({ ...acc, [name]: pool }),
  {} as WorkerPoolsByName,
);

// gets the first idle worker and reserves it for job dispatch
const reserveWorker = (name: WorkerPoolName): WorkerWrapper | null => {
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

const processQueue = (): void => {
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
    const meta: WorkerOutgoingMessage<unknown> = {
      data: item.data,
      transaction: ourTransaction,
    };
    refTable.set(ourTransaction, item.callback);
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
const enqueue = async <TData, TResult = WorkerResult>({
  name,
  data,
}: EnqueueOptions<TData>): Promise<TResult> =>
  new Promise((resolve) => {
    queue.push({ name, data, callback: resolve as (r: WorkerResult) => void });
    setImmediate(processQueue);
  });

export { enqueue };
