import json
import re
import shlex
import subprocess
import tempfile
import os

import requests
from boto.s3.connection import S3Connection
from boto.s3.key import Key

from exception import KleeRunFailure


MAILGUN_URL = "sandboxf39013a9ad7c47f3b621a94023230030.mailgun.org"
ANSI_ESCAPE_PATTERN = re.compile(r'\x1b[^m]*m')


def notify_on_entry(msg):
    def decorator(f):
        def wrapper(*args):
            args[0].send_notification('notification', {'message': msg})
            return f(*args)

        return wrapper

    return decorator


class WorkerRunner():
    def __init__(self, task_id, callback_endpoint=None):
        self.task_id = task_id
        self.callback_endpoint = callback_endpoint

    def __enter__(self):
        self.tempdir = tempfile.mkdtemp(prefix=self.task_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        subprocess.check_call(["sudo", "rm", "-rf", self.tempdir])

    @property
    def docker_command(self):
        return ['sudo', 'docker', 'run', '-t',
                '-v', '{}:/code'.format(self.tempdir),
                '--net="none"', 'kleeweb/klee']

    @notify_on_entry("Compressing output")
    def compress_output(self, output_tar_filename):
        tar_command = ['tar', '-zcvf', output_tar_filename, 'klee-out-0']
        subprocess.check_output(tar_command, cwd=self.tempdir)

    @notify_on_entry("Uploading result")
    def upload_result(self, file_name):
        conn = S3Connection(os.environ['AWS_ACCESS_KEY'],
                            os.environ['AWS_SECRET_KEY'])
        bucket = conn.get_bucket('klee-output')

        k = Key(bucket)
        k.key = file_name
        k.set_contents_from_filename(os.path.join(self.tempdir, file_name))
        k.set_acl('public-read')

        url = k.generate_url(expires_in=0, query_auth=False)
        return url

    def run_with_docker(self, command):
        try:
            return subprocess.check_output(self.docker_command + command)
        except subprocess.CalledProcessError as ex:
            raise KleeRunFailure(ex.output)

    @staticmethod
    def create_klee_command(klee_args):
        split_args = shlex.split(klee_args)
        klee_command = ["klee"]
        if split_args:
            klee_command += ['--posix-runtime', '-libc=uclibc']

        return klee_command + ["/code/result.o"] + split_args

    def run_llvm(self):
        llvm_command = ['/src/llvm-gcc4.2-2.9-x86_64-linux/bin/llvm-gcc',
                        '-I', '/src/klee/include', '--emit-llvm', '-c', '-g',
                        '/code/result.c',
                        '-o', '/code/result.o']
        self.run_with_docker(llvm_command)

    @notify_on_entry("Analysing with KLEE")
    def run_klee(self, code, klee_args):
        # Write code out to temporary directory
        temp_code_file = os.path.join(self.tempdir, "result.c")
        with open(temp_code_file, 'a+') as f:
            f.write(code)

        # Compile code with LLVM-GCC
        self.run_llvm()

        # Analyse code with KLEE
        klee_output = self.run_with_docker(self.create_klee_command(klee_args))

        # Remove ANSI escape sequences from output
        return ANSI_ESCAPE_PATTERN.sub('', klee_output)

    @staticmethod
    def send_email(email, output_url):
        requests.post(
            "https://api.mailgun.net/v2/{}/messages".format(MAILGUN_URL),
            auth=("api", os.environ['MAILGUN_API_KEY']),
            data={"from": "Klee <postmaster@{}>".format(MAILGUN_URL),
                  "to": "User <{}>".format(email),
                  "subject": "Klee Submission Output",
                  "text": "Your Klee submission output can be "
                          "accessed here: {}".format(output_url)})

    def send_notification(self, notification_type, data):
        if self.callback_endpoint:
            payload = {
                'channel': self.task_id,
                'type': notification_type,
                'data': json.dumps(data)
            }
            requests.post(self.callback_endpoint, payload)

    @notify_on_entry("Starting Job")
    def run(self, code, email, klee_args):
        try:
            klee_output = self.run_klee(code, klee_args)

            file_name = 'klee-output-{}.tar.gz'.format(self.task_id)
            self.compress_output(os.path.join(self.tempdir, file_name))

            output_upload_url = self.upload_result(file_name)
            if email:
                self.send_email(email, output_upload_url)

            self.send_notification('job_complete', {
                'result': {
                    'output': klee_output.strip(),
                    'url': output_upload_url
                }
            })

        except KleeRunFailure as ex:
            self.send_notification('job_failed', {'output': ex.message})
