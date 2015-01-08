import json
import re
import subprocess
import tempfile
import os
import codecs

import requests

from exception import KleeRunFailure
from worker_config import WorkerConfig
from mailer.mailgun_mailer import MailgunMailer

from processor.failed_test import FailedTestProcessor
from processor.coverage import CoverageProcessor
from processor.upload import UploadProcessor

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
    DOCKER_MOUNT_DIR = '/tmp/code'
    DOCKER_CODE_FILE = os.path.join(DOCKER_MOUNT_DIR, 'code.c')
    DOCKER_OBJECT_FILE = os.path.join(DOCKER_MOUNT_DIR, 'code.o')
    PROCESSOR_PIPELINE = [UploadProcessor, FailedTestProcessor,
                          CoverageProcessor]

    def __init__(self, task_id, callback_endpoint=None):
        self.task_id = task_id
        self.callback_endpoint = callback_endpoint
        self.mailer = MailgunMailer()

    def __enter__(self):
        self.tempdir = tempfile.mkdtemp(prefix=self.task_id)
        self.temp_code_file = os.path.join(self.tempdir, "code.c")
        subprocess.check_call(["sudo", "chmod", "777", self.tempdir])

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        subprocess.check_call(["sudo", "rm", "-rf", self.tempdir])

    @staticmethod
    def generate_arguments(klee_args):
        result = []

        stdin_enabled = klee_args.get('stdinEnabled')
        if stdin_enabled:
            num_files = klee_args.get('numFiles')
            size_files = klee_args.get('sizeFiles')
            result += ['--sym-files', str(num_files), str(size_files)]

        sym_args = klee_args.get('symArgs')
        min_sym_args, max_sym_args = sym_args.get('range')
        size_sym_args = sym_args.get('size')
        if min_sym_args and max_sym_args and size_sym_args:
            result += ['--sym-args', str(min_sym_args),
                       str(max_sym_args), str(size_sym_args)]

        return result

    @staticmethod
    def create_klee_command(arg_list):
        klee_command = ["klee"]
        if arg_list:
            klee_command += ['--posix-runtime', '-libc=uclibc']

        return klee_command + [WorkerRunner.DOCKER_OBJECT_FILE] + arg_list

    def docker_command(self, env):
        env_vars = []
        if env:
            for key, value in env.items():
                env_vars.extend(['-e', "{}={}".format(key, value)])

        flags = self.docker_flags + env_vars
        return ['sudo', 'docker', 'run'] + flags + ['kleeweb/klee']

    @property
    def docker_flags(self):
        flags = ['-t',
                 '-c={}'.format(worker_config.cpu_share),
                 '-v', '{}:{}'.format(self.tempdir, self.DOCKER_MOUNT_DIR),
                 '-w', self.DOCKER_MOUNT_DIR,
                 '--net="none"']

        # We have to disable cleanup on CircleCI (permissions issues)
        if not os.environ.get("CI"):
            flags += ['--rm=true']

        return flags

    def run_with_docker(self, command, env=None):
        try:
            return subprocess \
                .check_output(self.docker_command(env) + command,
                              universal_newlines=True) \
                .decode('utf-8')
        except subprocess.CalledProcessError as ex:
            message = "Error running {}:\n{}".format(
                " ".join(command), clean_stdout(ex.output))
            raise KleeRunFailure(message)

    def run_llvm(self):
        llvm_command = ['/usr/bin/clang-3.4',
                        '-I', '/src/klee/include', '-emit-llvm', '-c', '-g',
                        self.DOCKER_CODE_FILE, '-o', self.DOCKER_OBJECT_FILE]
        self.run_with_docker(llvm_command)

    @notify_on_entry("Analysing with KLEE")
    def run_klee(self, code, klee_args):
        # Write code out to temporary directory
        with codecs.open(self.temp_code_file, 'w', encoding='utf-8') as f:
            f.write(code)

        # Compile code with LLVM-GCC
        self.run_llvm()

        # Analyse code with KLEE
        klee_output = self.run_with_docker(self.create_klee_command(klee_args))

        # Remove ANSI escape sequences from output
        return clean_stdout(klee_output)

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
            args = WorkerRunner.generate_arguments(klee_args)
            klee_output = self.run_klee(code, args)

            result = {
                'output': klee_output.strip(),
            }

            # Run post-processing pipeline
            for processor_cls in self.PROCESSOR_PIPELINE:
                processor = processor_cls(self)
                result[processor.name] = processor.process(klee_args)

            self.send_notification('job_complete', {
                'result': result
            })

        except KleeRunFailure as ex:
            print "KLEE Run Failed"
            print ex.message

            self.send_notification('job_failed', {'output': ex.message})
