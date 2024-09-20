<!--
This file is part of BenchExec, a framework for reliable benchmarking:
https://github.com/sosy-lab/benchexec

SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>

SPDX-License-Identifier: Apache-2.0
-->

# BenchExec: Containerized Environments

This document explains the complications of using BenchExec inside
containerized environments (such as Docker or Podman) and shows how you can
create your own interactive Docker image (or adapt existing ones) to use
BenchExec within it. We focus mainly on the (nowadays standard) cgroups v2,
a brief guideline for the (outdated) cgroups v1 is provided
[below](#cgroups-v1).

There is a difference between executing only BenchExec inside a
(non-interactive) container and a fully interactive one which contains
multiple processes, with the former being significantly simpler. Both are
discussed here.

Note: It is possible to use BenchExec inside other container environments, e.g.
Docker, but we strongly recommend to use [Podman](https://podman.io/)
(compatible with Docker), as it provides "rootless" containers, i.e. its
containers are started as a regular user without sudo (just like BenchExec
containers). However, as the setup is largely the same, we provide it for
either case. In case you do want to use Docker, please also consider following
the (easy to implement) [security recommendations](#securing-docker-execution).


## Non-interactive Setups

In case you intend to only execute one BenchExec process and nothing else, the
setup is quite simple. It is sufficient to execute the BenchExec process as
entry point in a container with all required dependencies installed. For
example, if BenchExec is installed in a container with tag `my-container`, you
can simply execute
```
podman run --security-opt unmask=/sys/fs/cgroup --cgroups=split \
  --security-opt unmask=/proc/* \
  --security-opt seccomp=unconfined \
  -t my-container <arguments>
```
or
```
docker run --privileged --cap-drop=all -t my-container benchexec <arguments>
```
If you want BenchExec to use `fuse-overlayfs` in the container,
also specify `--device /dev/fuse`.

## BenchExec in Interactive Containers

Next follows a step-by-step guide to create a Docker / Podman image with
BenchExec (assuming cgroups v2). Some further background and reasoning is
provided later. Summarized, the main reason why BenchExec needs a "custom"
setup for containers is due to how cgroups work in combination with containers;
we need to "manually" set up a separate cgroup for BenchExec.

While this setup should work on most recent system, we cannot guarantee this,
since there simply are too many variables. In some cases, you may need to
slightly adapt some parts.

### Creating the Image

First, create the file `init.sh` with the following content:
```sh
#!/bin/sh
set -eu

# Create new sub-cgroups
# Note: While "init" can be renamed, the name "benchexec" is important
mkdir -p /sys/fs/cgroup/init /sys/fs/cgroup/benchexec
# Move the init process to that cgroup
echo $$ > /sys/fs/cgroup/init/cgroup.procs

# Enable controllers in subtrees for benchexec to use
for controller in $(cat /sys/fs/cgroup/cgroup.controllers); do
  echo "+$controller" > /sys/fs/cgroup/cgroup.subtree_control
  echo "+$controller" > /sys/fs/cgroup/benchexec/cgroup.subtree_control
done

# ... or whatever your init process should be
exec "$@"
```
and set it executable (`chmod +x init.sh`).

Now, pack this script into your Docker image and set it as entry point. If you
are working with a standard Docker image, create a file `Dockerfile`
```dockerfile
FROM debian:bookworm-slim
# Or whichever base image you are using

# Install all dependencies of your tool and BenchExec
# Example:
# RUN apt-get update && apt-get -y install \
#     python3-minimal \
#   && rm -rf /var/lib/apt/lists/*

# Install BenchExec with any method (apt install, pip install, or just copy the .whl)
# Examples:
# RUN pip install benchexec
# RUN wget https://github.com/sosy-lab/benchexec/releases/download/<current release>.whl -O /opt/benchexec.whl

# Copy the created script
COPY init.sh /init.sh

# Set init.sh as the entrypoint -- It is important to use brackets here
ENTRYPOINT [ "/init.sh" ]
# Set the default process to run
CMD [ "bash" ]
```
If you already have a Dockerfile, you only need to install BenchExec into it
and add the last few commands (i.e. copy `init.sh` and set the entrypoint).

With this finished, execute `podman build -t <tag> .` (or
`docker build -t <tag> .` when using Docker) in the directory where the
Dockerfile is located to build the container.

### Executing BenchExec in the Container

Start the image with
```
podman run --security-opt unmask=/sys/fs/cgroup --cgroups=split \
  --security-opt unmask=/proc/* \
  --security-opt seccomp=unconfined \
  -it <tag>
```
or
```
docker run --privileged --cap-drop=all -it <tag>
```
<!--
In principle, `--security-opt systempaths=unconfined --security-opt seccomp=unconfined`
should also be sufficient as Docker arguments,
but then mounting within the container still fails.
-->

> **IMPORTANT**: The `--privileged` argument gives the Docker container *full
> root access* to the host, so make sure to include the `--cap-drop=all` flag,
> use this command only with trusted images, and configure your Docker
> container such that everything in it is executed under a different user
> account, not as root (more details [below](#securing-docker-execution)).
> BenchExec is not designed to run as root and does not provide any safety
> guarantees regarding its container under these circumstances.

With this, you should be able to execute, for example, `runexec echo`
inside the Docker container. (In case you opted for the `.whl` install, you
need to execute
`PYTHONPATH=/opt/benchexec.whl python3 -m benchexec.runexecutor <program>`
instead.)

In case you want to modify this setup, please consider the
[background information below](#background-and-technical-details).

### Securing Docker Execution

When running under Docker, the user which executes the commands by default has
`UID` 0, i.e. has the permissions of `root` on the host system. For example, if
you mount a folder into the container, the processes started in the container
have *full write access* to these files, no matter what their permissions are.
As such, a small mistake in, e.g., an evaluation script that deletes temporary
files, could easily wreak havoc on your system. Using Podman directly mitigates
this issue, as the Podman container runs with the permissions of the current
user, not `root`, and thus cannot mess with system files (in particular, the
`root` user in a Podman container is mapped to your current user).

To significantly increase security of your Docker execution, add
```dockerfile
# Create non-root user and set it as default
RUN useradd -ms /bin/bash user
WORKDIR /home/user
USER user
```
at the end of your Dockerfile. Note: This is still worse than using Podman
(e.g. privilege escalation within the container leads to obtaining root
permissions on the host) but drastically reduces the chance for accidental
problems.


## Cgroups v1

With cgroups v1, use the following command line to start your container
```
podman run -v /sys/fs/cgroup:/sys/fs/cgroup:rw \
  --security-opt unmask=/sys/fs/cgroup --cgroups=split \
  --security-opt unmask=/proc/* \
  --security-opt seccomp=unconfined \
  -it <tag>
```
or
```
docker run -v /sys/fs/cgroup:/sys/fs/cgroup:rw --privileged --cap-drop=all -it <tag>
```
Note that this will not work with cgroups v2.

The special setup for interactive containers is not necessary in this case,
since cgroup v1 is designed differently. However, be advised that in either
case, the container unavoidably has access to the root cgroup of your entire
system, and, in case of Docker, full write access to this cgroup. Thus,
following the [security advice](#securing-docker-execution) is especially
recommended here.


## Background and Technical Details

Just like BenchExec, tools like Docker and Podman make heavy use of cgroups to
isolate processes. Thus, in order to get them working nicely together, some
additional tricks are required, especially in an interactive container (e.g.
one with a shell, where multiple commands can be executed).

BenchExec needs a dedicated cgroup together with enabled controllers to cleanly
isolate and precisely measure each tool execution. On a standard system,
cgroups are usually managed by systemd, from which BenchExec can automatically
obtain such a cgroup. In contrast, in an interactive container, the init
process usually is just a shell, which is placed in the "root" cgroup of
the container, without dedicated cgroup management. Thus, the cgroup needs to
be managed manually.

One might assume that BenchExec should be able to do this on its own.
Unfortunately, due to the "no internal processes" rule (see the
[cgroup documentation](https://www.man7.org/linux/man-pages/man7/cgroups.7.html)
for more information) any (non-root) cgroup can *either* contain processes *or*
delegate controllers to a child group. Thus, the shell in the root cgroup of
the container (which is not the root cgroup of the overall system) prevents
child cgroups with controllers being created. So, we need to move the init
process (and thus all subsequent ones) into a separate cgroup, which is the
purpose of the `init.sh` script. Only then can we create a separate, empty
cgroup dedicated to BenchExec.

Note that this also is the reason why non-interactive setups do not need this.
There, BenchExec is the sole root process, so it can use the root cgroup of the
container.


### Adaptation

There are many ways to achieve the required setup and users familiar with
Docker may choose to adapt the above procedure. There are a few peculiarities
to be aware of.

As explained above, the goal is to give BenchExec its own cgroup to use. So,
you need to start BenchExec processes inside an otherwise empty cgroup (with
appropriate controllers available). If that is not the case, BenchExec will
check if the cgroup `/benchexec` exists (and is empty) and try to use that as a
fallback. The `init.sh` above takes the latter approach. In case you want to do
a different setup, you need to manually create an appropriate cgroup hierarchy
inside the container, i.e., one where BenchExec has its own separate cgroup.

In any case, the cgroup which BenchExec then uses should have as many
controllers enabled and delegated to sub-cgroups as possible, for example like
this:
```bash
mkdir -p /sys/fs/cgroup/benchexec
for controller in $(cat /sys/fs/cgroup/cgroup.controllers); do
  echo "+$controller" > /sys/fs/cgroup/cgroup.subtree_control
done
for controller in $(cat /sys/fs/cgroup/benchexec/cgroup.controllers); do
  echo "+$controller" > /sys/fs/cgroup/benchexec/cgroup.subtree_control
done
```

For this, you should be aware of the implications of the "no internal
process"-rule. Effectively, this means that there cannot be any processes in
the root cgroup of the container (which, notably, is *not* the root cgroup of
the system). So, for the provided `init.sh` to work, it needs to be directly
executed (with `ENTRYPOINT [ "/init.sh" ]`). In particular, using, for example,
`ENTRYPOINT "/init.sh"` would not work, since this creates a shell that then
runs `init.sh` as a sub-process, meaning that the root cgroup would not be
empty when we try to enable subtree control.

In case you run into `Device or resource busy` errors, the problem likely is
that you want to enable subtree control in a non-empty cgroup or, vice versa,
move a process to cgroup with enabled subtree control, both of which is
prohibited for cgroups by design. For debugging, it is useful to inspect the
`cgroup.procs` and `cgroup.subtree_control` of the cgroup in question. Here,
note that calls like `cat` do also create a separate process.

