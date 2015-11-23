# BenchExec: Executing Benchmarks as Separate User

Both `benchexec` and `runexec` optionally support executing the tool under a different user account
than the benchmarking framework itself.
Compared to running everything under the same user, this prevents the benchmarked processes
from intervening with the benchmarking framework,
especially if the [cgroup setup](INSTALL.md#setting-up-cgroups) is such that the user
as which the benchmarks are executed has no permission to change the cgroup hierarchy.

If requested to do so, BenchExec uses `sudo` to execute the tool under a separate user.
This means that `sudo` needs to be installed and the necessary permissions need to be given
to the user who wants to start the benchmarks.
Note that while the setup for this needs root privileges once,
the actual benchmarking can still be done without root access.

In more detail, the user who wants to start the benchmarks needs to be given the permission
to execute arbitrary commands as the target user without the need to enter his password.
To grant this permission after creating an appropriate target user account,
run `visudo` with root privileges and add the following line to the opened file:

    %benchexec ALL=(benchmarks) NOPASSWD: ALL

This gives all users that are part of the group `benchexec` the permission to run arbitrary commands
as the user `benchmarks`. Of course you can adjust this as necessary.

To check if your sudo setup was successful, run the following command
with `<USER>` replaced with the target user (as which the benchmarks should actually be executed):

    sudo --non-interactive -u <USER> -- kill -0 0 && echo Successful

Afterwards, you should be able to successfully execute BenchExec,
for example with:

    runexec --user <USER> id

You can specify numeric user ids for `<USER>` by prefixing them with `#` (e.g., `#1000`).

Note that in the case of parallel benchmarks,
executing all of them under the same separate user account
would still allow the tool(s) to interfere with each other
(for example, by inadvertently issuing the command `killall`).
Thus `benchexec` allows to specify the parameter `--user` multiple times,
and in case of parallel runs (with parameter `-N`) ensures that
each parallel run executes under its own user account.
Of course this needs a setup with additional user accounts and the appropriate permissions.