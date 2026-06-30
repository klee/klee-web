from klee_web.celery_app import app


def test_at_most_once_does_not_ack_late():
    # Minimal failsafes: a dead worker's job is lost, not redelivered. We deliberately do
    # not set acks_late, so a task is acknowledged on receipt (at-most-once delivery).
    assert not app.conf.task_acks_late
