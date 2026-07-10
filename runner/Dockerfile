FROM klee/klee:v3.2

USER root
# Make the KLEE home tree readable/traversable by any uid so the container can run
# as the host user (docker run --user), not only as the image's klee user. The
# runner must not assume host uid == klee's uid (see runner.py --user).
RUN mkdir -p /work && chown klee:klee /work && chmod -R o+rX /home/klee

# Preloaded into native ktest replays to neutralise sleep/usleep/nanosleep (see
# entrypoint.py), so replay never spends real time sleeping. World-readable so the
# container running as the host user can load it.
COPY replay_nosleep.c /tmp/replay_nosleep.c
RUN clang -shared -fPIC -o /usr/local/lib/replay_nosleep.so /tmp/replay_nosleep.c \
    && chmod 0644 /usr/local/lib/replay_nosleep.so \
    && rm /tmp/replay_nosleep.c

# Prebuild the replay zygote (ADR-0022): KLEE's own replay-setup objects,
# compiled unmodified from the image's KLEE source, plus our driver. Per job,
# entrypoint.py only compiles the user's source and links it against these.
# The KLEE build dir name is not stable across image rebuilds, so the
# generated-headers include dir is located via config.h rather than hardcoded
# (same reason entrypoint.py globs for libkleeRuntest).
COPY replay_driver.c /tmp/replay_driver.c
RUN mkdir -p /usr/local/lib/klee-replay-zygote \
    && INC=/home/klee/klee_src/include \
    && BINC=$(dirname $(dirname $(dirname $(find /tmp/klee_build* -path '*klee/Config/config.h' | head -1)))) \
    && TOOLS=/home/klee/klee_src/tools/klee-replay \
    && POSIX=/home/klee/klee_src/runtime/POSIX \
    && clang -I$INC -I$BINC -c $TOOLS/file-creator.c  -o /usr/local/lib/klee-replay-zygote/file-creator.o \
    && clang -I$INC -I$BINC -c $TOOLS/klee_init_env.c -o /usr/local/lib/klee-replay-zygote/klee_init_env.o \
    && clang -I$INC -I$BINC -c $TOOLS/fd_init.c       -o /usr/local/lib/klee-replay-zygote/fd_init.o \
    && clang -I$INC -I$BINC -I$POSIX -c /tmp/replay_driver.c -o /usr/local/lib/klee-replay-zygote/replay_driver.o \
    && rm /tmp/replay_driver.c

COPY --chown=klee:klee entrypoint.py /home/klee/entrypoint.py

USER klee
WORKDIR /work
ENTRYPOINT ["python3", "/home/klee/entrypoint.py"]
