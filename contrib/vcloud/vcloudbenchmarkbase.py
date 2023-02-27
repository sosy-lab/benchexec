# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.benchexec
import benchexec.model
import benchexec.tooladapter
import benchexec.tools
import benchexec.util


class VcloudBenchmarkBase(benchexec.benchexec.BenchExec):
    """
    An extension of BenchExec that supports executing the benchmarks in the
    VerifierCloud (internal project at https://gitlab.com/sosy-lab/software/verifiercloud/).
    """

    def create_argument_parser(self):
        parser = super(VcloudBenchmarkBase, self).create_argument_parser()
        vcloud_args = parser.add_argument_group("Options for using VerifierCloud")
        self.add_vcloud_args(vcloud_args)

        return parser

    def add_vcloud_args(self, vcloud_args):
        vcloud_args.add_argument(
            self.get_param_name("cloudMaster"),
            dest="cloudMaster",
            metavar="HOST",
            help="Sets the master host of the VerifierCloud instance to be used. If this is a HTTP URL, the web interface is used.",
        )

        vcloud_args.add_argument(
            self.get_param_name("cloudPriority"),
            dest="cloudPriority",
            metavar="PRIORITY",
            help="Sets the priority for this benchmark used in the VerifierCloud. Possible values are IDLE, LOW, HIGH, URGENT.",
        )

        vcloud_args.add_argument(
            self.get_param_name("cloudCPUModel"),
            dest="cpu_model",
            type=str,
            default=None,
            metavar="CPU_MODEL",
            help="Only execute runs in the VerifierCloud on CPU models that contain the given string.",
        )

        vcloud_args.add_argument(
            "--justReprocessResults",
            dest="reprocessResults",
            action="store_true",
            help="Do not run the benchmarks. Assume that the benchmarks were already executed in the VerifierCloud and the log files are stored (use --startTime to point the script to the results).",
        )

        vcloud_args.add_argument(
            self.get_param_name("cloudClientHeap"),
            dest="cloudClientHeap",
            metavar="MB",
            default=100,
            type=int,
            help="The heap-size (in MB) used by the VerifierCloud client. A too small heap-size may terminate the client without any results.",
        )

        vcloud_args.add_argument(
            "--zipResultFiles",
            dest="zipResultFiles",
            action="store_true",
            help="Packs all result files on the worker into a zip file before file transfer (add this flag if a large number of result files is generated).",
        )
        vcloud_args.add_argument(
            "--cgroupAccess",
            dest="cgroupAccess",
            action="store_true",
            help="Allows the usage of cgroups inside the execution environment. This is useful e.g. if a tool wants to make use of resource limits for subprocesses it spawns.",
        )
        vcloud_args.add_argument(
            "--tryLessMemory",
            dest="tryLessMemory",
            action="store_true",
            help="Execute runs first with less memory than specified. In case a run fails because of OOM, it is automatically rescheduled but this time with full memory limit.",
        )
        vcloud_args.add_argument(
            self.get_param_name("cloudAdditionalFiles"),
            dest="additional_files",
            metavar="FILE_OR_PATH",
            nargs="*",
            type=str,
            help="Specify files or paths that shall also be transferred and be made available to the run in the cloud.",
        )
        vcloud_args.add_argument(
            "--no-ivy-cache",
            dest="noIvyCache",
            action="store_true",
            help="Prevents ivy from caching the downloaded jar files. This prevents clashes due to concurrent access to the cache.",
        )

    def get_param_name(self, pname):
        return "--v" + pname

    def check_existing_results(self, benchmark):
        if not self.config.reprocessResults:
            super(VcloudBenchmarkBase, self).check_existing_results(benchmark)
