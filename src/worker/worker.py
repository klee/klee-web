import os
import subprocess
import re

from celery import Celery
from celery.worker.control import Panel
from celery.exceptions import SoftTimeLimitExceeded

from .runner import WorkerRunner
from .worker_config import WorkerConfig


celery = Celery(broker=os.environ['CELERY_BROKER_URL'], backend='rpc')

worker_config = WorkerConfig()


@Panel.register
def get_uptime_stats(state):
    uptime_pattern = re.compile(
        r'up\s+(.*?),\s+([0-9]+) '
        r'users?,\s+load averages?: '
        r'([0-9]+\.[0-9][0-9]),?\s+([0-9]+\.[0-9][0-9])'
        r',?\s+([0-9]+\.[0-9][0-9])')

    uptime_output = subprocess.check_output('uptime')
    uptime_matches = uptime_pattern.search(uptime_output)

    return {
        'uptime': uptime_matches.group(1),
        'users': uptime_matches.group(2),
        'loadavg_1min': uptime_matches.group(3),
        'loadavg_5min': uptime_matches.group(4),
        'loadavg_15min': uptime_matches.group(5),
    }


@celery.task(name='submit_code', bind=True)
def submit_code(self, code, email, klee_args, endpoint):
    # name will hold the name of the current worker
    name = self.request.hostname
    with WorkerRunner(self.request.id, endpoint, worker_name=name) as runner:
        try:
            runner.run(code, email, klee_args)
        except SoftTimeLimitExceeded:
            result = {
                'klee_run': {
                    'output': 'Job exceeded time limit of '
                              '{} seconds'.format(worker_config.timeout)
                }
            }
            runner.send_notification('job_failed', result)
