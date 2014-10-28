from worker.worker import celery

import os
import redis


# Returns tasks registered to workers.
def registered_tasks(workers=None):
    i = celery.control.inspect(workers)
    return i.registered()


# Returns currently executing tasks.
def active_tasks(workers=None):
    i = celery.control.inspect(workers)
    return i.active()


def scheduled_tasks(workers=None):
    i = celery.control.inspect(workers)
    return i.scheduled()


# Returns tasks taken off the queue by a worker, waiting to be executed.
def reserved_tasks(workers=None):
    i = celery.control.inspect(workers)
    return i.reserved()


def active_queues(workers=None):
    i = celery.control.inspect(workers)
    return i.active_queues()


def get_workers():
    i = celery.control.inspect()
    return i.registered().keys()


# Returns tasks in redis queue, not given to a worker.
def redis_queue():
    r = redis.StrictRedis(host=os.environ['REDIS_HOST'],
                          port=os.environ['REDIS_PORT'])
    return r.lrange('celery', 0, -1)


def kill_task(task_id):
    celery.control.revoke(task_id, terminate=True, signal='SIGKILL')
