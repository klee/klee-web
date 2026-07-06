/* Preloaded (LD_PRELOAD) into native ktest replays only, see entrypoint.py.
 *
 * KLEE models sleep away during symbolic execution, so replay should too. Per-path
 * output is about what a path printed, not timing, and without this a program that
 * sleeps per iteration (the maze demo) spends real seconds sleeping per replay for no
 * benefit, burning the whole replay budget. Returning 0 is the success return of a
 * completed sleep, so control flow and output are unchanged. */
#include <time.h>
#include <unistd.h>

unsigned int sleep(unsigned int seconds) {
    (void)seconds;
    return 0;
}

int usleep(useconds_t usec) {
    (void)usec;
    return 0;
}

int nanosleep(const struct timespec *req, struct timespec *rem) {
    (void)req;
    (void)rem;
    return 0;
}
