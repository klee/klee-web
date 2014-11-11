from worker.worker import celery
from klee_web.models import Task

import os
import redis
import json
import datetime


# Returns tasks registered to workers.
def registered_tasks(workers=None):
    i = celery.control.inspect(workers)
    return i.registered()


# Returns currently executing tasks.
def active_tasks(workers=None):
    i = celery.control.inspect(workers)
    return populate_task_data(i.active())


def scheduled_tasks(workers=None):
    i = celery.control.inspect(workers)
    return i.scheduled()


def active_queues(workers=None):
    i = celery.control.inspect(workers)
    return i.active_queues()


def get_workers():
    i = celery.control.inspect()
    return i.registered().keys()


# Returns tasks taken off the queue by a worker, waiting to be executed.
def reserved_tasks(workers=None):
    i = celery.control.inspect(workers)
    return i.reserved()


# Returns tasks in redis queue, not given to a worker.
def redis_queue():
    r = redis.StrictRedis(host=os.environ['REDIS_HOST'],
                          port=os.environ['REDIS_PORT'])
    return r.lrange('celery', 0, -1)


# Returns tasks in redis queue and reserved by worker.
def all_waiting_tasks():
    return populate_task_data(reserved_tasks()) +\
        map(get_task_from_redis, redis_queue())


def done_tasks():
    tasks = Task.objects.filter(completed_at__isnull=False).values()
    return map(add_completion_info, tasks)


def populate_task_data(tasks):
    all_tasks = []
    for mach in tasks:
        for t in tasks[mach]:
            task = {
                'id': t['id'],
                'mach': mach
            }
            get_db_attrs(task)
            all_tasks.append(task)
    return all_tasks


def get_db_attrs(task):
    db_task = Task.objects.filter(task_id=task['id']).first()
    if db_task:
        task['ip_address'] = db_task.ip_address
        task['created_at'] = db_task.created_at

        time = datetime.datetime.now() - db_task.created_at
        running_time = divmod(time.days * 86400 + time.seconds, 60)
        task['running_time'] = running_time


def get_task_from_redis(w):
    w = json.loads(w)
    task = {
        'mach': 'Pending',
        'id': w['properties']['correlation_id']
    }
    get_db_attrs(task)
    return task


def add_completion_info(task):
    time = task['completed_at'] - task['created_at']
    running_time = divmod(time.days * 86400 + time.seconds, 60)
    task['running_time'] = running_time
    task['mach'] = 'Not applicable'
    return task
