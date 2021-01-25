import subprocess



class P4RunExecutor:
    def __init__(self):
        self.name = "Hello"
    
    def _run_execution(
        self,
        args,
        # stdin,
        # stdout,
        # stderr,
        # env,
        # cwd,
        # temp_dir,
        # parent_setup_fn,
        # child_setup_fn,
        # parent_cleanup_fn,
    ):

        result = subprocess.run(args)

        print("Result of process", result)