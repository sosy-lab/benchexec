import threading
import os
import logging
import subprocess
import errno
import resource
import time

from benchexec import tooladapter
from benchexec.intel_cpu_energy import EnergyMeasurement
from benchexec import resources
import benchexec.util as util
import benchexec.systeminfo as systeminfo
from benchexec.p4runexecutor import P4RunExecutor


STOPPED_BY_INTERRUPT = False

def init(config, benchmark):

    benchmark.tool_version = benchmark.tool.version(benchmark.executable)
    tool_locator = tooladapter.create_tool_locator(config)
    benchmark.executable = benchmark.tool.executable(tool_locator)
    print("Init")

def get_system_info():
    return systeminfo.SystemInfo()

def execute_run(self):
    print("Execute run")

def execute_benchmark(benchmark, output_handler):
    
    run_sets_executed = 0
    logging.debug("I will use %s threads.", benchmark.num_of_threads)

    if (
        benchmark.requirements.cpu_model
        or benchmark.requirements.cpu_cores != benchmark.rlimits.cpu_cores
        or benchmark.requirements.memory != benchmark.rlimits.memory
    ):
        logging.warning(
            "Ignoring specified resource requirements in local-execution mode, "
            "only resource limits are used."
        )

    for runSet in benchmark.run_sets:

        if STOPPED_BY_INTERRUPT:
            break

        if not runSet.should_be_executed():
            output_handler.output_for_skipping_run_set(runSet)

        elif not runSet.runs:
            output_handler.output_for_skipping_run_set(
                runSet, "because it has no files"
            )
        else:
            run_sets_executed += 1
            #Get time before runSet
            energy_measurement = EnergyMeasurement.create_if_supported()
            ruBefore = resource.getrusage(resource.RUSAGE_CHILDREN)
            walltime_before = time.monotonic()
            if energy_measurement:
                energy_measurement.start()

            output_handler.output_before_run_set(runSet)


            #TODO Add so one can run multiple inputs
            args = None
            for run in runSet.runs:
                args = run.cmdline() 
                       

            #This is executed before every run(Probably here we set the setup script)
            def fn_before_run():
                print("Doing Setup")

            #This is executed after each run(Probably here we run the teardown script)
            def fn_after_run():
                print("Doing Teardown")

            executor = P4RunExecutor()

            executor._run_execution(args)

            # get times after runSet
            walltime_after = time.monotonic()
            energy = energy_measurement.stop() if energy_measurement else None
            usedWallTime = walltime_after - walltime_before
            ruAfter = resource.getrusage(resource.RUSAGE_CHILDREN)
            usedCpuTime = (ruAfter.ru_utime + ruAfter.ru_stime) - (
                ruBefore.ru_utime + ruBefore.ru_stime
            )


    output_handler.output_after_benchmark(STOPPED_BY_INTERRUPT)
    return 0

