from klee_web.celery_app import app
from klee_web.models import MAX_TIME_CEILING


def test_acks_late_so_a_dead_worker_redelivers():
    assert app.conf.task_acks_late is True


def test_rejects_on_worker_lost_so_the_task_requeues():
    assert app.conf.task_reject_on_worker_lost is True


def test_visibility_timeout_is_twice_the_max_time_ceiling():
    assert app.conf.broker_transport_options["visibility_timeout"] == MAX_TIME_CEILING * 2
