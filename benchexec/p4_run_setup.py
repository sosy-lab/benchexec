from benchexec.model import Run


class P4SetupHandler(object):
    def __init__(self, benchmark, test_dict):
        self.benchmark = benchmark
        self.test_dict = test_dict

    def update_runsets(self):
        for runSet in self.benchmark.run_sets:
            runset_temp = runSet.runs.copy()
            expected_result = runset_temp[0].expected_results
            properties = runset_temp[0].properties
            runSet.runs = []
            for module_name in self.test_dict:
                for test_name in self.test_dict[module_name]:
                    run = Run(module_name + "." + test_name,
                    "Fake",
                    "",
                    "",
                    runSet,
                    expected_results=expected_result)
                    run.properties = properties
                    runSet.runs.append(run)

