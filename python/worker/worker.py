import os
import tempfile
import subprocess
import shutil
import shlex
import re
import json

import requests

from boto.s3.connection import S3Connection
from boto.s3.key import Key
from celery import Celery

celery = Celery(broker=os.environ["CELERY_BROKER_URL"], backend="rpc")

from celery.worker.control import Panel


@Panel.register
def get_uptime_stats(state):
    uptime_pattern = re.compile(
        r"up\s+(.*?),\s+([0-9]+) "
        r"users?,\s+load averages?: "
        r"([0-9]+\.[0-9][0-9]),?\s+([0-9]+\.[0-9][0-9])"
        r",?\s+([0-9]+\.[0-9][0-9])")

    uptime_output = subprocess.check_output("uptime")
    uptime_matches = uptime_pattern.search(uptime_output)

    return {
        'uptime': uptime_matches.group(1),
        'users': uptime_matches.group(2),
        'loadavg_1min': uptime_matches.group(3),
        'loadavg_5min': uptime_matches.group(4),
        'loadavg_15min': uptime_matches.group(5),
    }


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
    def __init__(self, task_id, callback_endpoint):
        self.task_id = task_id
        self.callback_endpoint = callback_endpoint

    def __enter__(self):
        self.tempdir = tempfile.mkdtemp(prefix=self.task_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        subprocess.check_call(["sudo", "chown", "-R",
                               "worker:worker", self.tempdir])
        shutil.rmtree(self.tempdir)

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

    @notify_on_entry("Analysing with KLEE")
    def run_klee(self, klee_args):
        llvm_command = ['/src/llvm-gcc4.2-2.9-x86_64-linux/bin/llvm-gcc',
                        '-I', '/src/klee/include', '--emit-llvm', '-c', '-g',
                        '/code/result.c',
                        '-o', '/code/result.o']

        split_args = shlex.split(klee_args)
        klee_command = ["klee"]
        if split_args:
            klee_command += ['--posix-runtime']
        klee_command += ["/code/result.o"] + shlex.split(klee_args)

        subprocess.check_output(self.docker_command + llvm_command)
        klee_output = subprocess.check_output(
            self.docker_command + klee_command)

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

    def send_notification(self, type, data):
        payload = {
            'channel': self.task_id,
            'type': type,
            'data': json.dumps(data)
        }

        requests.post(self.callback_endpoint, payload)

    @notify_on_entry("Starting Job")
    def run(self, code, email, klee_args):
        try:
            with open(os.path.join(self.tempdir, "result.c"), 'a+') as f:
                f.write(code)
                f.flush()

                klee_output = self.run_klee(klee_args)

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

        except subprocess.CalledProcessError as ex:
            self.send_notification('job_failed',
                                   {'output': ex.output})


@celery.task(name='submit_code', bind=True)
def submit_code(self, code, email, klee_args, endpoint):
    with WorkerRunner(self.request.id, endpoint) as runner:
        runner.run(code, email, klee_args)
