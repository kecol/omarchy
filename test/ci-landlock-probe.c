#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/landlock.h>
#include <stdio.h>
#include <string.h>
#include <sys/prctl.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <unistd.h>

#if !defined(SYS_landlock_create_ruleset) || !defined(SYS_landlock_add_rule) || !defined(SYS_landlock_restrict_self)
#error "Landlock syscall definitions are required; do not guess syscall numbers"
#endif

static int report(const char *context, const char *stage, long abi, int error) {
  printf("context=%s stage=%s abi=%ld errno=%d result=fail\n", context, stage, abi, error);
  return 1;
}

static int check_file(int directory, const char *path, const char *expected) {
  int fd = openat(directory, path, O_RDONLY | O_NONBLOCK | O_CLOEXEC | O_NOFOLLOW);
  if (fd < 0) return -1;
  struct stat status;
  if (fstat(fd, &status) < 0) {
    int error = errno;
    close(fd);
    errno = error;
    return -1;
  }
  if (!S_ISREG(status.st_mode)) {
    close(fd);
    errno = EINVAL;
    return -1;
  }
  char data[32];
  ssize_t length = read(fd, data, sizeof(data));
  int error = errno;
  close(fd);
  if (length < 0) {
    errno = error;
    return -1;
  }
  if ((size_t) length != strlen(expected) || memcmp(data, expected, (size_t) length) != 0) {
    errno = EIO;
    return -1;
  }
  return 0;
}

int main(int argc, char **argv) {
  setbuf(stdout, NULL);
  if (argc != 4 || (strcmp(argv[1], "runner") != 0 && strcmp(argv[1], "container") != 0)) {
    fprintf(stderr, "Usage: probe runner|container ALLOWED_DIRECTORY OUTSIDE_SYNTHETIC_FILE\n");
    return 2;
  }
  const char *context = argv[1];
  int seccomp_mode = prctl(PR_GET_SECCOMP, 0, 0, 0, 0);
  printf("context=%s inherited_seccomp_mode=%d\n", context, seccomp_mode);
  long abi = syscall(SYS_landlock_create_ruleset, NULL, 0, LANDLOCK_CREATE_RULESET_VERSION);
  if (abi < 1) return report(context, "abi", abi, errno);
  printf("context=%s stage=abi abi=%ld result=available\n", context, abi);

  int allowed = open(argv[2], O_PATH | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
  if (allowed < 0) return report(context, "fixture-directory", abi, errno);
  if (check_file(allowed, "inside", "inside\n") < 0) return report(context, "baseline-inside", abi, errno);
  if (check_file(AT_FDCWD, argv[3], "outside\n") < 0) return report(context, "baseline-outside", abi, errno);

  struct landlock_ruleset_attr ruleset = {
    .handled_access_fs = LANDLOCK_ACCESS_FS_READ_FILE | LANDLOCK_ACCESS_FS_READ_DIR
  };
  /* The original eight-byte filesystem ABI works without newer optional fields. */
  int ruleset_fd = syscall(SYS_landlock_create_ruleset, &ruleset, sizeof(ruleset.handled_access_fs), 0);
  if (ruleset_fd < 0) return report(context, "create-ruleset", abi, errno);
  struct landlock_path_beneath_attr rule = {
    .allowed_access = ruleset.handled_access_fs,
    .parent_fd = allowed
  };
  if (syscall(SYS_landlock_add_rule, ruleset_fd, LANDLOCK_RULE_PATH_BENEATH, &rule, 0) < 0)
    return report(context, "add-rule", abi, errno);
  /* Only this disposable process is restricted; no parent/global setting changes. */
  if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) < 0) return report(context, "no-new-privileges", abi, errno);
  if (syscall(SYS_landlock_restrict_self, ruleset_fd, 0) < 0)
    return report(context, "restrict-self", abi, errno);
  close(ruleset_fd);

  if (check_file(allowed, "inside", "inside\n") < 0) return report(context, "allowed-read", abi, errno);
  int outside = open(argv[3], O_RDONLY | O_NONBLOCK | O_CLOEXEC | O_NOFOLLOW);
  int denied_error = errno;
  if (outside >= 0) {
    close(outside);
    return report(context, "outside-not-denied", abi, 0);
  }
  if (denied_error != EACCES) return report(context, "outside-error", abi, denied_error);
  close(allowed);
  printf("context=%s stage=enforcement abi=%ld inside=allowed outside=EACCES result=pass\n", context, abi);
  return 0;
}
