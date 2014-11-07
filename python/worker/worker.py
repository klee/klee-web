import os
import subprocess
import re

from celery import Celery

from celery.worker.control import Panel
from celery.exceptions import SoftTimeLimitExceeded

from runner import WorkerRunner

JOB_TIME_LIMIT = 30

celery = Celery(broker=os.environ["CELERY_BROKER_URL"], backend="rpc")


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


@celery.task(name='submit_code', bind=True, soft_time_limit=JOB_TIME_LIMIT)
def submit_code(self, code, email, klee_args, endpoint):
    with WorkerRunner(self.request.id, endpoint) as runner:
        try:
            runner.run(code, email, klee_args)
        except SoftTimeLimitExceeded:
            runner.send_notification(
                'job_failed',
                {
                    'output': "Job exceeded time limit of "
                              "{} seconds".format(JOB_TIME_LIMIT)
                }
            )
