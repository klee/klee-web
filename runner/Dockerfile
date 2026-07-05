FROM klee/klee:v3.2

USER root
# Make the KLEE home tree readable/traversable by any uid so the container can run
# as the host user (docker run --user), not only as the image's klee user. The
# runner must not assume host uid == klee's uid (see runner.py --user).
RUN mkdir -p /work && chown klee:klee /work && chmod -R o+rX /home/klee

COPY --chown=klee:klee entrypoint.py /home/klee/entrypoint.py

USER klee
WORKDIR /work
ENTRYPOINT ["python3", "/home/klee/entrypoint.py"]
