import json
import re
import subprocess
import tempfile
import os
import codecs

import requests

import failing_tests
from exception import KleeRunFailure
from worker_config import WorkerConfig
from mailer.mailgun_mailer import MailgunMailer
from storage.s3_storage import S3Storage


ANSI_ESCAPE_PATTERN = re.compile(r'\x1b[^m]*m')
LXC_MESSAGE_PATTERN = re.compile(r'lxc-start: .*')
worker_config = WorkerConfig()


def clean_stdout(s):
    s = ANSI_ESCAPE_PATTERN.sub('', s)

    # Remove LXC warnings where present (CircleCI)
    s = LXC_MESSAGE_PATTERN.sub('', s)
    return s.strip()


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
        subprocess.check_call(["sudo", "chmod", "777", self.tempdir])

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        subprocess.check_call(["sudo", "rm", "-rf", self.tempdir])

    @staticmethod
    def generate_arguments(klee_args):
        result = []

        num_files = klee_args.get('numFiles')
        size_files = klee_args.get('numFiles')

        if num_files and size_files:
            result += ['--sym-files', str(num_files), str(size_files)]

        min_stdin_args = klee_args.get('minStdinArgs')
        max_stdin_args = klee_args.get('maxStdinArgs')
        size_stdin_args = klee_args.get('sizeStdinArgs')
        if min_stdin_args and max_stdin_args and size_stdin_args:
            result += ['--sym-args', str(min_stdin_args),
                       str(max_stdin_args), str(size_stdin_args)]

        return result

    @staticmethod
    def create_klee_command(arg_list):
        klee_command = ["klee"]
        if arg_list:
            klee_command += ['--posix-runtime', '-libc=uclibc']

        return klee_command + ["/code/result.o"] + arg_list

    @property
    def docker_command(self):
        return ['sudo', 'docker', 'run'] + self.docker_flags + ['kleeweb/klee']

    @property
    def docker_flags(self):
        flags = ['-t',
                 '-c={}'.format(worker_config.cpu_share),
                 '-v', '{}:/code'.format(self.tempdir),
                 '--net="none"']

        # We have to disable cleanup on CircleCI (permissions issues)
        if not os.environ.get("CI"):
            flags += ['--rm=true']

        return flags

    def run_with_docker(self, command):
        try:
            return subprocess \
                .check_output(self.docker_command + command,
                              universal_newlines=True) \
                .decode('utf-8')
        except subprocess.CalledProcessError as ex:
            raise KleeRunFailure(clean_stdout(ex.output))

    @notify_on_entry("Compressing output")
    def compress_output(self, output_tar_filename):
        tar_command = ['tar', '-zcvf', output_tar_filename, 'klee-out-0']
        subprocess.check_output(tar_command, cwd=self.tempdir)

    @notify_on_entry("Uploading result")
    def upload_result(self, result_file_path):
        return self.storage.store_file(result_file_path)

    def run_llvm(self):
        llvm_command = ['/usr/bin/clang-3.4',
                        '-I', '/src/klee/include', '-emit-llvm', '-c', '-g',
                        '/code/result.c',
                        '-o', '/code/result.o']
        self.run_with_docker(llvm_command)

    @notify_on_entry("Analysing with KLEE")
    def run_klee(self, code, klee_args):
        # Write code out to temporary directory
        temp_code_file = os.path.join(self.tempdir, "result.c")
        with codecs.open(temp_code_file, 'w', encoding='utf-8') as f:
            f.write(code)

        # Compile code with LLVM-GCC
        self.run_llvm()

        # Analyse code with KLEE
        klee_output = self.run_with_docker(self.create_klee_command(klee_args))

        # Remove ANSI escape sequences from output
        return clean_stdout(klee_output)

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

    def get_failed_tests(self):
        klee_out_path = os.path.join(self.tempdir, 'klee-out-0')
        return failing_tests.get_failed_tests(self.tempdir, klee_out_path)

    @notify_on_entry("Starting Job")
    def run(self, code, email, klee_args):
        try:
            args = WorkerRunner.generate_arguments(klee_args)
            klee_output = self.run_klee(code, args)
            failed_tests = self.get_failed_tests()

            file_name = 'klee-output-{}.tar.gz'.format(self.task_id)
            compressed_output_path = os.path.join(self.tempdir, file_name)
            self.compress_output(compressed_output_path)
            output_upload_url = self.upload_result(compressed_output_path)

            if email:
                self.send_email(email, output_upload_url)

            self.send_notification('job_complete', {
                'result': {
                    'output': klee_output.strip(),
                    'url': output_upload_url,
                    'failing': failed_tests
                }
            })

        except KleeRunFailure as ex:
            self.send_notification('job_failed', {'output': ex.message})
