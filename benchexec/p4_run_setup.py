from benchexec.model import Run


class P4SetupHandler(object):
    def __init__(self, benchmark, test_dict):
        self.benchmark = benchmark
        self.test_dict = test_dict

    def update_runsets(self):
        for runSet in self.benchmark.run_sets:
            runSet.runs = []
            for module_name in self.test_dict:
                for test_name in self.test_dict[module_name]:
                    run = Run(module_name + "." + test_name,
                    "Fake",
                    None,
                    None,
                    runSet)
                    runSet.runs.append(run)

