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

/**
 * Data item sent to the stats worker.
 * (Derived from what stats.worker.js reads: categoryType, resultType, column, columnType, columnTitle)
 */
type StatsWorkerItem = {
  categoryType: string;
  resultType: string;
  column: number | string;
  columnType: string;
  columnTitle: string;
};

type StatsBucketMeta = {
  type: string | null;
  maxDecimals: number;
};

/**
 * Note: stats.worker.js stringifies almost everything before posting back.
 * So the numeric stats arrive as strings ("NaN", "Infinity", "42.0", ...).
 */
type StatsBucket = Partial<{
  title: string;
  sum: string;
  avg: string;
  max: string;
  median: string;
  min: string;
  stdev: string;
  meta: StatsBucketMeta;
}>;

type StatsWorkerResult =
  | {
      columnType: string;
      total: StatsBucket | undefined;
      [bucketKey: string]: unknown; // narrowed below via access patterns
    }
  | Record<string, unknown>;

/**
 * Map pool name -> (data shape, result shape).
 */
type WorkerJobMap = {
  stats: {
    data: StatsWorkerItem[];
    result: StatsWorkerResult &
      Record<string, StatsBucket | string | undefined>;
  };
};

type WorkerPoolName = keyof WorkerJobMap;

type DataUrlString = string;

interface WorkerPoolConfig<N extends WorkerPoolName = WorkerPoolName> {
  template: DataUrlString;
  poolSize: number;
  name: N;
}

interface WorkerWrapper {
  worker: Worker;
  busy: boolean;
}

type WorkerPoolsByName = {
  [N in WorkerPoolName]: WorkerWrapper[];
};

type WorkerIncomingMessage<N extends WorkerPoolName> = {
  transaction: number;
  result: WorkerJobMap[N]["result"];
};

type WorkerOutgoingMessage<N extends WorkerPoolName> = {
  data: WorkerJobMap[N]["data"];
  transaction: number;
};

type QueueItem<N extends WorkerPoolName> = {
  name: N;
  data: WorkerJobMap[N]["data"];
  callback: (result: WorkerJobMap[N]["result"]) => void;
};

type EnqueueOptions<N extends WorkerPoolName> = {
  name: N;
  data: WorkerJobMap[N]["data"];
};

const WORKER_POOLS: WorkerPoolConfig[] = [
  {
    template: statsWorkerDataUrl,
    poolSize: 8,
    name: "stats",
  },
];

const queue: Array<QueueItem<WorkerPoolName>> = [];

// Store that maps callback functions to a worker transaction number
const refTable = new Map<number, (result: unknown) => void>();

let transaction = 1;

const handleWorkerMessage = <N extends WorkerPoolName>(
  { data: message }: MessageEvent<WorkerIncomingMessage<N>>,
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
const workerPool: WorkerPoolsByName = Object.fromEntries(
  WORKER_POOLS.map(({ template, poolSize, name }) => {
    const pool: WorkerWrapper[] = [];
    for (let i = 0; i < poolSize; i += 1) {
      const worker = new Worker(template);
      const workerObj: WorkerWrapper = { worker, busy: false };
      worker.onmessage = (msg) => handleWorkerMessage(msg, workerObj);

      pool.push(workerObj);
    }
    return [name, pool] as const;
  }),
) as WorkerPoolsByName;
// NOTE (JS->TS): Object.fromEntries expresses "build an object from key/value pairs" directly,
// avoids the repeated object spreads of a reduce-based implementation, and is typically
// more readable and efficient.

// gets the first idle worker and reserves it for job dispatch
const reserveWorker = (name: WorkerPoolName): WorkerWrapper | null => {
  const worker = workerPool[name].find((w) => !w.busy);
  // NOTE (JS->TS): find() communicates intent ("first matching worker") and avoids allocating
  // an intermediate array like filter(...)[0].
  if (!worker) {
    return null;
  }
  worker.busy = true;
  return worker;
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
    const meta: WorkerOutgoingMessage<typeof item.name> = {
      data: item.data,
      transaction: ourTransaction,
    };
    refTable.set(ourTransaction, item.callback as (result: unknown) => void);
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
const enqueue = async <N extends WorkerPoolName>({
  name,
  data,
}: EnqueueOptions<N>): Promise<WorkerJobMap[N]["result"]> =>
  new Promise((resolve) => {
    queue.push({ name, data, callback: resolve });
    setImmediate(processQueue);
  });

export { enqueue };
