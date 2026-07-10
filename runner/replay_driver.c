/* Fork-per-ktest replay driver (ADR-0022).
 *
 * Replays every test case KLEE generated against the user's natively
 * compiled program to capture per-path output. entrypoint.py compiles the
 * user source with -Dmain=__user_main and links it with this file, KLEE's
 * own replay-setup objects (file-creator.o, klee_init_env.o, fd_init.o,
 * prebuilt in the image from /home/klee/klee_src/tools/klee-replay/), and
 * libkleeBasic for the ktest reader. Invoked as: replay.out <klee-out-dir>.
 *
 * Linking once and forking per test removes the per-test process creation
 * and dynamic linking that made replay an order of magnitude slower under a
 * syscall-intercepting sandbox. The POSIX setup (klee_init_env +
 * replay_create_files) runs per fork, so symbolic stdin, files and argv
 * replay exactly as under klee-replay. The klee_* stubs mirror
 * tools/klee-replay/klee-replay.c and, where that file lacks them,
 * runtime/Runtest/intrinsics.c.
 */
#define _GNU_SOURCE
#define _LARGEFILE64_SOURCE
#define _FILE_OFFSET_BITS 64
#include "fd.h"
#include "klee/ADT/KTest.h"

#include <dirent.h>
#include <errno.h>
#include <limits.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <sys/wait.h>

extern exe_file_system_t __exe_fs; /* fd_init.o */
extern char replay_dir[];          /* file-creator.o */
extern char **environ;             /* libc */

void klee_init_env(int *argcPtr, char ***argvPtr);   /* klee_init_env.o */
void replay_create_files(exe_file_system_t *exe_fs); /* file-creator.o */

/* The user's main, renamed via -Dmain=__user_main at compile time.
 * Unprototyped on purpose so any of the three legal main signatures links. */
int __user_main();

/* One in-order ktest reader shared by klee_init_env and the user program
 * (klee-replay.c's `input`/`obj_index`, renamed). The shared counter is what
 * makes mixed klee_make_symbolic + POSIX-input programs replay correctly:
 * KLEE records the POSIX objects first and the program's own after, and
 * consumption must follow that order. */
static KTest *g_input;
static unsigned g_obj;

static void emit_error(const char *msg) {
    fprintf(stderr, "REPLAY: ERROR: %s\n", msg);
    exit(1);
}

/* Faithful to klee-replay.c: in-order consumption, size check, NO name
 * check. libkleeRuntest's name-checking variant is why mixed programs
 * replay empty under the old klee-replay path. The size check doubles as a
 * canary for object-order desync. */
void klee_make_symbolic(void *addr, size_t nbytes, const char *name) {
    if (g_obj >= g_input->numObjects)
        emit_error("ran out of appropriate inputs");
    KTestObject *o = &g_input->objects[g_obj];
    if (o->numBytes != nbytes) {
        fprintf(stderr,
                "REPLAY: ERROR: make_symbolic mismatch on %s: %u bytes in "
                "test file, %zu in code\n",
                name, o->numBytes, nbytes);
        exit(1);
    }
    memcpy(addr, o->bytes, nbytes);
    g_obj++;
}

/* klee-replay.c semantics; consumes one object, mirroring KLEE's own
 * runtime/Intrinsic/klee_range.c. */
int klee_range(int start, int end, const char *name) {
    int r;
    if (start >= end)
        emit_error("klee_range: invalid range");
    if (start + 1 == end)
        return start;
    klee_make_symbolic(&r, sizeof r, name);
    if (r < start || r >= end)
        emit_error("klee_range: invalid result");
    return r;
}

/* intrinsics.c semantics; consumes one object. */
uintptr_t klee_choose(uintptr_t n) {
    uintptr_t x;
    klee_make_symbolic(&x, sizeof x, "klee_choose");
    if (x >= n)
        emit_error("klee_choose failure");
    return x;
}

/* Mirror of runtime/Intrinsic/klee_int.c. Absent from libkleeRuntest, so
 * this makes programs using klee_int replayable at all. */
int klee_int(const char *name) {
    int x;
    klee_make_symbolic(&x, sizeof x, name);
    return x;
}

/* Verbatim from intrinsics.c: klee_get_value* never create ktest objects
 * (handled inside the KLEE engine), so at replay the argument already is
 * the concrete answer. */
#define KLEE_GET_VALUE_STUB(suffix, type)                                      \
    type klee_get_value##suffix(type x) { return x; }
KLEE_GET_VALUE_STUB(f, float)
KLEE_GET_VALUE_STUB(d, double)
KLEE_GET_VALUE_STUB(l, long)
KLEE_GET_VALUE_STUB(ll, long long)
KLEE_GET_VALUE_STUB(_i32, int32_t)
KLEE_GET_VALUE_STUB(_i64, int64_t)
#undef KLEE_GET_VALUE_STUB

void klee_silent_exit(int status) { exit(status); }
unsigned klee_is_replay(void) { return 1; }
void klee_abort(void) { abort(); }

void klee_report_error(const char *file, int line, const char *message,
                       const char *suffix) {
    (void)file;
    (void)line;
    (void)suffix;
    emit_error(message);
}

/* klee-replay.c behavior: note the violation, keep the output. */
unsigned klee_assume(uintptr_t x) {
    if (!x)
        fputs("REPLAY: klee_assume(0)!\n", stderr);
    return 0;
}

void klee_warning(char *name) {
    fprintf(stderr, "REPLAY: klee_warning: %s\n", name);
}

void klee_warning_once(char *name) {
    fprintf(stderr, "REPLAY: klee_warning_once: %s\n", name);
}

unsigned klee_is_symbolic(uintptr_t x) {
    (void)x;
    return 0;
}
void klee_prefer_cex(void *buffer, uintptr_t condition) {
    (void)buffer;
    (void)condition;
}
void klee_posix_prefer_cex(void *buffer, uintptr_t condition) {
    (void)buffer;
    (void)condition;
}
void klee_mark_global(void *object) { (void)object; }
void klee_print_expr(const char *msg, ...) { (void)msg; }
void klee_set_forking(unsigned enable) { (void)enable; }
void klee_open_merge(void) {}
void klee_close_merge(void) {}
int klee_get_errno(void) { return errno; }

int __fputc_unlocked(int c, FILE *f) { return fputc_unlocked(c, f); }
int __fgetc_unlocked(FILE *f) { return fgetc_unlocked(f); }

/* file-creator.c expects these two from klee-replay.c. process_status runs
 * in the helper that feeds a piped or tty stdin; _exit so the helper never
 * flushes its copy of the capture stream. */
int keep_temps = 0;
void process_status(int status, time_t elapsed, const char *pfx) {
    (void)elapsed;
    (void)pfx;
    if (WIFEXITED(status))
        _exit(WEXITSTATUS(status));
    _exit(WIFSIGNALED(status) ? 128 + WTERMSIG(status) : 0);
}

/* Per-test wall-clock limit. Guarded because alarm(0) would mean no timeout
 * at all, the opposite of the intent. */
static int replay_timeout(void) {
    const char *t = getenv("KLEE_REPLAY_TIMEOUT");
    int v = t ? atoi(t) : 10;
    return v > 0 ? v : 10;
}

/* "<stem>.ktest" -> "<stem><suffix>". */
static void stem_path(char *dst, size_t cap, const char *ktest,
                      const char *suffix) {
    size_t n = strlen(ktest) - 6;
    snprintf(dst, cap, "%.*s%s", (int)n, ktest, suffix);
}

/* Replays one test case; runs in a forked child and never returns.
 * Capture stdout FIRST: replay_create_files may dup2 a modeled file over
 * fd 1 (--sym-stdout) and that redirect must win, exactly as under
 * klee-replay; a child dying during setup then leaves an empty .part
 * rather than no file. */
static void run_one_test(const char *ktest, const char *binpath) {
    char part[PATH_MAX];
    stem_path(part, sizeof part, ktest, ".stdout.part");
    if (!freopen(part, "w", stdout))
        _exit(111);
    alarm(replay_timeout());

    g_input = kTest_fromFile(ktest);
    if (!g_input)
        emit_error("could not read ktest file");
    g_obj = 0;

    /* Hand klee_init_env the recorded command line so it can re-parse the
     * --sym-* options, as klee-replay.c's main loop does. argv[0] becomes
     * the replay binary path, matching klee-replay. */
    int argc;
    char **argv;
    char *min_argv[2];
    if (g_input->numArgs > 0) {
        argc = (int)g_input->numArgs;
        argv = g_input->args;
        argv[0] = (char *)binpath;
    } else {
        min_argv[0] = (char *)binpath;
        min_argv[1] = NULL;
        argc = 1;
        argv = min_argv;
    }

    klee_init_env(&argc, &argv);
    replay_create_files(&__exe_fs);
    if (chdir(replay_dir) != 0) {
        /* Only programs opening symbolic files would notice; keep going. */
    }

    /* exit(), not _exit(): a returning main must run atexit handlers and
     * flush stdio, exactly as an exec'd program would. Safe in the fork:
     * the batch parent holds no buffered stdout of its own. */
    exit(__user_main(argc, argv, environ));
}

/* Cancel/timeout teardown. timeout(1) signals only the batch parent, so
 * amplify one TERM into a SIGKILL of the whole process group; unfinished
 * children die mid-write and their .part files are never promoted. */
static void on_term(int sig) {
    (void)sig;
    kill(0, SIGKILL);
}

/* Promotion runs only after wait() has reaped the child, so the file is
 * final. Promote regardless of exit status: a crashed or alarm-killed
 * replay's captured output is still that path's real output (same
 * semantics as the mv in the previous xargs replay). */
static void promote(const char *ktest) {
    char part[PATH_MAX], final_path[PATH_MAX];
    stem_path(part, sizeof part, ktest, ".stdout.part");
    stem_path(final_path, sizeof final_path, ktest, ".stdout");
    rename(part, final_path);
}

/* Wait for any child, promote its test's output. Nonzero when no children
 * remain. */
static int reap_one(pid_t *pids, char **ktests, int n) {
    int status;
    pid_t done = wait(&status);
    if (done <= 0)
        return -1;
    for (int i = 0; i < n; i++) {
        if (pids[i] == done) {
            promote(ktests[i]);
            pids[i] = 0;
            break;
        }
    }
    return 0;
}

static int cmp_path(const void *a, const void *b) {
    return strcmp(*(char *const *)a, *(char *const *)b);
}

/* All *.ktest paths under dir, sorted by name so the earliest tests replay
 * first when a budget kill ends the batch early. Taking the directory
 * instead of a file list keeps a path explosion clear of the kernel's argv
 * size limit. */
static int collect_ktests(const char *dir, char ***out) {
    DIR *d = opendir(dir);
    if (!d) {
        perror("REPLAY: opendir");
        return -1;
    }
    char **list = NULL;
    int n = 0, cap = 0;
    struct dirent *e;
    while ((e = readdir(d)) != NULL) {
        size_t len = strlen(e->d_name);
        if (len <= 6 || strcmp(e->d_name + len - 6, ".ktest") != 0)
            continue;
        if (n == cap) {
            cap = cap ? cap * 2 : 64;
            list = realloc(list, (size_t)cap * sizeof *list);
            if (!list)
                emit_error("out of memory");
        }
        char *p = malloc(strlen(dir) + 1 + len + 1);
        if (!p)
            emit_error("out of memory");
        sprintf(p, "%s/%s", dir, e->d_name);
        list[n++] = p;
    }
    closedir(d);
    if (n > 0)
        qsort(list, (size_t)n, sizeof *list, cmp_path);
    *out = list;
    return n;
}

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <klee-output-dir>\n", argv[0]);
        return 2;
    }
    signal(SIGTERM, on_term);
    signal(SIGINT, on_term);

    char **ktests = NULL;
    int n = collect_ktests(argv[1], &ktests);
    if (n <= 0)
        return n < 0 ? 1 : 0;

    long maxpar = sysconf(_SC_NPROCESSORS_ONLN);
    if (maxpar < 1)
        maxpar = 1;

    pid_t *pids = calloc((size_t)n, sizeof *pids);
    if (!pids)
        emit_error("out of memory");

    long active = 0;
    for (int i = 0; i < n; i++) {
        pid_t pid = fork();
        if (pid < 0) {
            perror("REPLAY: fork");
            continue;
        }
        if (pid == 0)
            run_one_test(ktests[i], argv[0]);
        pids[i] = pid;
        active++;
        while (active >= maxpar) {
            if (reap_one(pids, ktests, n) != 0)
                break;
            active--;
        }
    }
    while (active > 0) {
        if (reap_one(pids, ktests, n) != 0)
            break;
        active--;
    }
    return 0;
}
