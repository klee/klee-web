import itertools
from copy import deepcopy
import os
import json
import datetime

import redis

from worker.worker import celery
from frontend.models import Task


def get_workers():
    i = celery.control.inspect()
    return i.registered().keys()


# Returns tasks registered to workers.
def registered_tasks(workers=None):
    i = celery.control.inspect(workers)
    tasks = i.registered() or {}
    return remove_killed_tasks(tasks)


# Returns currently executing tasks.
def active_tasks(workers=None):
    i = celery.control.inspect(workers)
    tasks = i.active() or {}
    return populate_task_data(remove_killed_tasks(tasks))


def scheduled_tasks(workers=None):
    i = celery.control.inspect(workers)
    tasks = i.scheduled() or {}
    return remove_killed_tasks(tasks)


def active_queues(workers=None):
    i = celery.control.inspect(workers)
    return i.active_queues()


# Returns tasks taken off the queue by a worker, waiting to be executed.
def reserved_tasks(workers=None):
    i = celery.control.inspect(workers)
    tasks = i.reserved() or {}
    return remove_killed_tasks(tasks)


# Returns tasks in redis queue, not given to a worker.
def redis_queue():
    r = redis.StrictRedis(host=os.environ['REDIS_HOST'],
                          port=os.environ['REDIS_PORT'])
    return r.lrange('celery', 0, -1)


# Returns tasks in redis queue and reserved by worker.
def waiting_tasks():
    l = map(get_task_from_redis, redis_queue())
    return populate_task_data(reserved_tasks()) + l


def revoked_tasks(workers=None):
    i = celery.control.inspect(workers)
    return i.revoked()


def done_tasks():
    tasks = Task.objects.filter(completed_at__isnull=False).values()
    return map(populate_completed_task, tasks)


def populate_task_data(tasks):
    all_tasks = []
    for t in tasks:
        task = {
            'id': t['id'],
            'mach': t['mach']
        }
        all_tasks.append(get_db_attrs(task))
    return all_tasks


def get_db_attrs(task):
    db_task = Task.objects.filter(task_id=task['id']).first()
    populated_task = deepcopy(task)
    if db_task:
        populated_task['ip_address'] = db_task.ip_address
        populated_task['created_at'] = db_task.created_at

        time = datetime.datetime.now() - db_task.created_at
        running_time = divmod(time.days * 86400 + time.seconds, 60)
        populated_task['running_time'] = running_time

    return populated_task


def get_task_from_redis(w):
    w = json.loads(w)
    task = {
        'mach': 'Pending',
        'id': w['properties']['correlation_id']
    }

    return get_db_attrs(task)


def populate_completed_task(db_task):
    task = {
        'mach': db_task['worker_name'],
        'id': db_task['task_id'],
        'ip_address': db_task['ip_address'],
        'created_at': db_task['created_at']
    }

    time = db_task['completed_at'] - db_task['created_at']
    running_time = divmod(time.days * 86400 + time.seconds, 60)
    task['running_time'] = running_time
    return task


def kill_task(task_id):
    Task.objects.filter(task_id=task_id).delete()
    celery.control.revoke(task_id, terminate=True, signal='SIGKILL')


def remove_killed_tasks(tasks, workers=None):
    revoked = revoked_tasks(workers).values()
    set_revoked = set(itertools.chain.from_iterable(revoked))

    def is_revoked(task):
        return not task['id'] in set_revoked

    for mach, ts in tasks.items():
        for t in ts:
            t['mach'] = mach

    all_tasks = [filter(is_revoked, v) for (k, v) in tasks.items()]
    return itertools.chain.from_iterable(all_tasks)
