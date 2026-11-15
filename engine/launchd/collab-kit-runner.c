/*
 * collab-kit-runner: starts a project's tools/kb/nightly.sh (0.4), or the kit's engine/backend.sh
 * (the 0.5 back end), for launchd, and nothing else.
 * Part of Collab Kit. Built by tools/kb/launchd/install.sh (cc, then an ad-hoc signature).
 *
 * Why it exists. On macOS, a job that launchd starts may not read Google Drive's folder
 * (~/Library/CloudStorage) unless the program it runs has Full Disk Access, and no prompt is shown:
 * the read just fails. macOS has no narrower grant that a person can give a background program for
 * that folder. Without this runner, the program would be /bin/bash, and granting /bin/bash Full Disk
 * Access would grant it to every shell script on the machine. This runner is the program to grant
 * instead: it runs only an absolute path ending in /tools/kb/nightly.sh or /engine/backend.sh,
 * through /bin/bash.
 *
 * It does not exec: it starts bash as a child and waits. macOS attributes a child's file access to
 * the program launchd started (the "responsible" process), which stays this runner only while it is
 * alive; an exec would make the responsible program /bin/bash again.
 */
#include <errno.h>
#include <signal.h>
#include <spawn.h>
#include <stdio.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

extern char **environ;
static pid_t child = 0;

static void forward(int sig) {
    if (child > 0) kill(child, sig);
}

int main(int argc, char **argv) {
    static const char *suffixes[] = {"/tools/kb/nightly.sh", "/engine/backend.sh"};
    size_t n = argc > 1 ? strlen(argv[1]) : 0;
    int allowed = 0;
    for (size_t s = 0; s < sizeof(suffixes) / sizeof(suffixes[0]); s++) {
        size_t k = strlen(suffixes[s]);
        if (n > k && strcmp(argv[1] + n - k, suffixes[s]) == 0) allowed = 1;
    }
    if (argc < 2 || argv[1][0] != '/' || !allowed ||
        strstr(argv[1], "/../") != NULL || strstr(argv[1], "/./") != NULL) {
        fprintf(stderr, "collab-kit-runner: runs only <repository>/tools/kb/nightly.sh or <kit>/engine/backend.sh, "
                        "given as an absolute path\n");
        return 64;
    }
    char *args[argc + 1];
    args[0] = "/bin/bash";
    for (int i = 1; i < argc; i++) args[i] = argv[i];
    args[argc] = NULL;

    signal(SIGTERM, forward);
    signal(SIGINT, forward);
    signal(SIGHUP, forward);
    int rc = posix_spawn(&child, "/bin/bash", NULL, NULL, args, environ);
    if (rc != 0) {
        fprintf(stderr, "collab-kit-runner: cannot start /bin/bash: %s\n", strerror(rc));
        return 127;
    }
    int status = 0;
    while (waitpid(child, &status, 0) < 0) {
        if (errno != EINTR) {
            perror("collab-kit-runner: waitpid");
            return 127;
        }
    }
    if (WIFEXITED(status)) return WEXITSTATUS(status);
    if (WIFSIGNALED(status)) return 128 + WTERMSIG(status);
    return 1;
}
