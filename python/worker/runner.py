import json
import re
import shlex
import subprocess
import tempfile
import os

import requests

from exception import KleeRunFailure
from worker_config import WorkerConfig
from mailer.mailgun_mailer import MailgunMailer
from storage.s3_storage import S3Storage


ANSI_ESCAPE_PATTERN = re.compile(r'\x1b[^m]*m')
worker_config = WorkerConfig()


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
        self.mailer = MailgunMailer()
        self.storage = S3Storage()

    def __enter__(self):
        self.tempdir = tempfile.mkdtemp(prefix=self.task_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        subprocess.check_call(["sudo", "rm", "-rf", self.tempdir])

    @staticmethod
    def create_klee_command(klee_args):
        split_args = shlex.split(klee_args)
        klee_command = ["klee"]
        if split_args:
            klee_command += ['--posix-runtime', '-libc=uclibc']

        return klee_command + ["/code/result.o"] + split_args

    @property
    def docker_command(self):
        return ['sudo', 'docker', 'run', '-t',
                '-c={}'.format(worker_config.cpu_share),
                '-v', '{}:/code'.format(self.tempdir),
                '--net="none"', 'kleeweb/klee']

    def run_with_docker(self, command):
        try:
            return subprocess.check_output(self.docker_command + command)
        except subprocess.CalledProcessError as ex:
            raise KleeRunFailure(ex.output)

    @notify_on_entry("Compressing output")
    def compress_output(self, output_tar_filename):
        tar_command = ['tar', '-zcvf', output_tar_filename, 'klee-out-0']
        subprocess.check_output(tar_command, cwd=self.tempdir)

    @notify_on_entry("Uploading result")
    def upload_result(self, result_file_path):
        return self.storage.store_file(result_file_path)

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
        with open(temp_code_file, 'w') as f:
            f.write(code)

        # Compile code with LLVM-GCC
        self.run_llvm()

        # Analyse code with KLEE
        klee_output = self.run_with_docker(self.create_klee_command(klee_args))

        # Remove ANSI escape sequences from output
        return ANSI_ESCAPE_PATTERN.sub('', klee_output)

    def send_email(self, recipient, output_url):
        email_body = "Your KLEE submission output can be accessed here: {}" \
            .format(output_url)
        self.mailer.send_mail(recipient, "KLEE-Web Run Results", email_body)

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
            compressed_output_path = os.path.join(self.tempdir, file_name)
            self.compress_output(compressed_output_path)
            output_upload_url = self.upload_result(compressed_output_path)

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
