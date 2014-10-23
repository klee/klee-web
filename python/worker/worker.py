import os
import tempfile
import subprocess
import shutil
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from celery import Celery

celery = Celery(broker=os.environ["BROKER_URL"], backend="rpc")


def run_klee(docker_command):
    llvm_command = ['/src/llvm-gcc4.2-2.9-x86_64-linux/bin/llvm-gcc',
                    '-I', '/src/klee/include', '--emit-llvm', '-c', '-g', '/code/result.c',
                    '-o', '/code/result.o']
    klee_command = ["klee", "/code/result.o"]

    subprocess.check_output(docker_command + llvm_command)
    klee_result = subprocess.check_output(docker_command + klee_command)
    return klee_result


def compress_output(docker_command, file_name):
    tar_command = ['tar', '-zcvf', file_name, '/code/klee-out-0']
    subprocess.check_output(docker_command + tar_command)


def upload_result(file_name, tempdir):
    conn = S3Connection()
    bucket = conn.get_bucket('klee-output')

    k = Key(bucket)
    k.key = file_name
    k.set_contents_from_filename("{0}/{1}".format(tempdir, file_name))
    k.set_acl('public-read')

    url = k.generate_url(expires_in=0, query_auth=False)
    return url


@celery.task(name='submit_code', bind=True)
def submit_code(self, code):
    task_id = self.request.id
    tempdir = tempfile.mkdtemp(prefix=task_id)
    try:
        with open(os.path.join(tempdir, "result.c"), 'a+') as f:
            f.write(code)
            f.flush()

            docker_command = ['sudo', 'docker', 'run', '-t', '-v', '{}:/code'.format(tempdir), 'kleeweb/klee']

            file_name = 'klee-output-{}.tar.gz'.format(task_id)

            klee_result = run_klee(docker_command)
            compress_output(docker_command, "/code/{}".format(file_name))
            url = upload_result(file_name, tempdir)

            return klee_result.strip() + url
    except subprocess.CalledProcessError as e:
        return "KLEE run failed with: {}".format(e.output)
    finally:
        # Workaround for docker writing files as root, set owner of tmpdir back to current user.
        subprocess.check_call(["sudo", "chown", "-R", "worker:worker", tempdir])
        shutil.rmtree(tempdir)
