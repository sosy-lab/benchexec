// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2007-2021 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

#include <errno.h>
#include <linux/capability.h>
#include <linux/prctl.h>
#include <linux/sched.h>
#include <linux/seccomp.h>
#include <net/if.h>
#include <seccomp.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/mount.h>

// Here we test all the assumptions about the Linux kernel and libc ABI
// (mostly about values of constant macros from headers)
// that are hard-coded in BenchExec's source.
// Because these values are part of the ABI, they are guranteed to stay
// unchanged, but they might have different values on each architecture.
// Unfortunately, there is no way for us to read these values during runtime.
// Testing with https://godbolt.org/z/vdPYWv confirms that these hold
// on 32-bit and 64-bit x86 and ARM platforms
// (with the exception of seccomp.h, which godbolt does not provide).
// Searching for the constant name in the Linux source code is also an option,
// but sometimes ifdefs and architecture-specific headers complicate this.

void test_BenchExec_assumptions() {
  // from container.py
  _Static_assert(SIOCGIFFLAGS == 0x8913, "SIOCGIFFLAGS");
  _Static_assert(SIOCSIFFLAGS == 0x8914, "SIOCSIFFLAGS");
  _Static_assert(IFF_UP == 0x1, "IFF_UP");
  _Static_assert(IFNAMSIZ == 16, "IFNAMSIZ");
  _Static_assert(sizeof(struct ifreq) >= 16 + 14, "struct ifreq");

  // from libc.py
  _Static_assert(sizeof(long) == sizeof(off_t), "Unexpected size of off_t");
  _Static_assert(CLONE_NEWNS == 0x00020000, "CLONE_NEWNS");
  _Static_assert(CLONE_NEWUTS == 0x04000000, "CLONE_NEWUTS");
  _Static_assert(CLONE_NEWIPC == 0x08000000, "CLONE_NEWIPC");
  _Static_assert(CLONE_NEWUSER == 0x10000000, "CLONE_NEWUSER");
  _Static_assert(CLONE_NEWPID == 0x20000000, "CLONE_NEWPID");
  _Static_assert(CLONE_NEWNET == 0x40000000, "CLONE_NEWNET");
  _Static_assert(PROT_NONE == 0, "PROT_NONE");
  _Static_assert(MAP_GROWSDOWN == 0x00100, "MAP_GROWSDOWN");
  _Static_assert(MAP_STACK == 0x20000, "MAP_STACK");
  _Static_assert(MS_RDONLY == 1, "MS_RDONLY");
  _Static_assert(MS_NOSUID == 2, "MS_NOSUID");
  _Static_assert(MS_NODEV == 4, "MS_NODEV");
  _Static_assert(MS_NOEXEC == 8, "MS_NOEXEC");
  _Static_assert(MS_REMOUNT == 32, "MS_REMOUNT");
  _Static_assert(MS_BIND == 4096, "MS_BIND");
  _Static_assert(MS_MOVE == 8192, "MS_MOVE");
  _Static_assert(MS_REC == 16384, "MS_REC");
  _Static_assert(MS_PRIVATE == 262144, "MS_PRIVATE");
  _Static_assert(MNT_DETACH == 2, "MNT_DETACH");
  _Static_assert(_LINUX_CAPABILITY_VERSION_3 == 0x20080522, "LINUX_CAPABILITY_VERSION_3");
  _Static_assert(CAP_SYS_ADMIN == 21, "CAP_SYS_ADMIN");
  _Static_assert(PR_SET_DUMPABLE == 4, "PR_SET_DUMPABLE");
  _Static_assert(PR_GET_SECCOMP == 21, "PR_GET_SECCOMP");
  _Static_assert(PR_SET_SECCOMP == 22, "PR_SET_SECCOMP");

  // from seccomp.py
  _Static_assert(SCMP_ACT_ALLOW == 0x7FFF0000, "SCMP_ACT_ALLOW");
  _Static_assert(SCMP_ACT_ERRNO(ENOSYS) == 0x00050000 | ENOSYS, "SCMP_ACT_ENOSYS");
  _Static_assert(SECCOMP_MODE_FILTER == 2, "SECCOMP_MODE_FILTER");
}
