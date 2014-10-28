from worker.worker import celery


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


def reserved_tasks(workers=None):
    i = celery.control.inspect(workers)
    return i.reserved()


def active_queues(workers=None):
    i = celery.control.inspect(workers)
    return i.active_queues()


def get_workers():
    i = celery.control.inspect()
    return i.registered().keys()
