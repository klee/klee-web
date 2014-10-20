import os
import tempfile
import subprocess
import shutil

from celery import Celery

celery = Celery(broker=os.environ["BROKER_URL"], backend="rpc")


@celery.task(name='submit_code', bind=True)
def submit_code(self, code):
    tempdir = tempfile.mkdtemp(prefix=self.request.id)
    try:
        with open(os.path.join(tempdir, "result.c"), 'a+') as f:
            f.write(code)
            f.flush()

            docker_command = ['sudo', 'docker', 'run', '-t', '-v',
                              '{}:/code'.format(tempdir), 'kleeweb/klee']
            llvm_command = ['/src/llvm-gcc4.2-2.9-x86_64-linux/bin/llvm-gcc',
                            '-I', '/src/klee/include', '--emit-llvm', '-c',
                            '-g', '/code/result.c',
                            '-o', '/code/result.o']
            klee_command = ["klee", "/code/result.o"]

            subprocess.check_output(docker_command + llvm_command)

            klee_result = subprocess.check_output(
                docker_command + klee_command)
            return klee_result.strip()
    except subprocess.CalledProcessError as e:
        return "KLEE run failed with: {}".format(e.output)
    finally:
        # Workaround for docker writing files as root, set owner of tmpdir back
        # to current user.
        subprocess.check_call(
            ["sudo", "chown", "-R", "worker:worker", tempdir])
        shutil.rmtree(tempdir)
