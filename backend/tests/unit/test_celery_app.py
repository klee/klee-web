from klee_web.celery_app import app


def test_at_most_once_does_not_ack_late():
    # Celery acknowledges immediately before execution, so Worker loss after that point
    # does not redeliver the task.
    assert not app.conf.task_acks_late
