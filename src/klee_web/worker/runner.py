import json
import re
import subprocess
import tempfile
import os
import codecs

import requests

from worker.exceptions import KleeRunFailure
from worker.decorators import notify_on_entry
from worker.worker_config import WorkerConfig

from worker.mailer.mailgun_mailer import MailgunMailer
from worker.mailer.dummy_mailer import DummyMailer

from worker.processor.failed_test import FailedTestProcessor
from worker.processor.coverage import CoverageProcessor
from worker.processor.upload import UploadProcessor
from worker.processor.klee_run import KleeRunProcessor
from worker.processor.stats import StatsProcessor

ANSI_ESCAPE_PATTERN = re.compile(r'\x1b[^m]*m')
LXC_MESSAGE_PATTERN = re.compile(r'lxc-start: .*')
DEVELOPMENT = os.environ.get('DEVELOPMENT') is not None

worker_config = WorkerConfig()


class WorkerRunner():
    CODE_FILE_NAME = 'code.c'
    OBJECT_FILE_NAME = 'code.o'
    DOCKER_MOUNT_DIR = '/tmp/code'
    DOCKER_CODE_FILE = os.path.join(DOCKER_MOUNT_DIR, CODE_FILE_NAME)
    DOCKER_OBJECT_FILE = os.path.join(DOCKER_MOUNT_DIR, OBJECT_FILE_NAME)
    DEFAULT_PROCESSOR_PIPELINE = [KleeRunProcessor, UploadProcessor,
                                  FailedTestProcessor, StatsProcessor,
                                  CoverageProcessor]

    def __init__(self, task_id, callback_endpoint=None, pipeline=None,
                 worker_name=''):
        self.task_id = task_id
        self.callback_endpoint = callback_endpoint
        self.mailer = DummyMailer() if DEVELOPMENT else MailgunMailer()
        self.worker_name = worker_name
        self.pipeline = pipeline or WorkerRunner.DEFAULT_PROCESSOR_PIPELINE

    def __enter__(self):
        self.tempdir = tempfile.mkdtemp(prefix=self.task_id)
        self.temp_code_file = os.path.join(self.tempdir, self.CODE_FILE_NAME)
        subprocess.check_call(['sudo', 'chmod', '777', self.tempdir])

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        subprocess.check_call(['sudo', 'rm', '-rf', self.tempdir])

    def docker_command(self, env):
        env_vars = []
        if env:
            for key, value in env.items():
                env_vars.extend(['-e', '{}={}'.format(key, value)])

        flags = self.docker_flags + env_vars
        return ['sudo', 'docker', 'run'] + flags + ['klee/klee']

    @property
    def docker_flags(self):
        flags = ['-t',
                 '--cpu-shares={}'.format(worker_config.cpu_share),
                 '-v', '{}:{}'.format(self.tempdir, self.DOCKER_MOUNT_DIR),
                 '-w', self.DOCKER_MOUNT_DIR,
                 '--net=none']

        # We have to disable cleanup on CircleCI (permissions issues)
        if not os.environ.get('CI'):
            flags += ['--rm=true']

        return flags

    @staticmethod
    def clean_stdout(s):
        s = ANSI_ESCAPE_PATTERN.sub('', s)

        # Remove LXC warnings where present (CircleCI)
        s = LXC_MESSAGE_PATTERN.sub('', s)
        return s.strip()

    def run_with_docker(self, command, env=None):
        try:
            output = subprocess.check_output(
                self.docker_command(env) + command,
                universal_newlines=True)
            return self.clean_stdout(output)
        except subprocess.CalledProcessError as ex:
            message = 'Error running {}:\n{}'.format(
                ' '.join(command), self.clean_stdout(ex.output))
            raise KleeRunFailure(message)

    def send_notification(self, notification_type, data):
        if self.callback_endpoint:
            payload = {
                'worker_name': self.worker_name,
                'channel': self.task_id,
                'type': notification_type,
                'data': json.dumps(data)
            }
            requests.post(self.callback_endpoint, payload)

    def execute_pipeline(self, code, klee_args):
        # Write code out to temporary directory
        with codecs.open(self.temp_code_file, 'w', encoding='utf-8') as f:
            f.write(code)

        result = {}

        # Run processor pipeline
        for processor_cls in self.pipeline:
            processor = processor_cls(self, klee_args)

            if processor.enabled:
                notify_message = processor.notify_message
                if notify_message:
                    self.send_notification('notification',
                                           {'message': notify_message})
                result[processor.name] = processor.process()

        return result

    @notify_on_entry('Starting Job')
    def run(self, code, email, klee_args):
        try:
            result = self.execute_pipeline(code, klee_args)

            self.send_notification('job_complete', result)

        except KleeRunFailure as ex:
            print('KLEE Run Failed')
            print(str(ex))

            result = {
                'klee_run': {
                    'output': str(ex)
                }
            }
            self.send_notification('job_failed', result)
