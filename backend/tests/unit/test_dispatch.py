from uuid import uuid4

from klee_web.jobs.dispatch import CeleryDispatcher
from klee_web.models import JobRequest, KleeFlags

SOURCE = "int main() { return 0; }"


async def test_celery_dispatcher_enqueues_job_with_a_per_task_hard_time_limit(monkeypatch):
    from klee_web import celery_app

    captured: dict[str, object] = {}

    def fake_apply_async(args=None, kwargs=None, **options):
        captured["args"] = args
        captured["options"] = options

    monkeypatch.setattr(celery_app.run_klee_job, "apply_async", fake_apply_async)

    job_id = uuid4()
    request = JobRequest(source=SOURCE, flags=KleeFlags(max_time=60))
    await CeleryDispatcher().dispatch(job_id, request)

    assert captured["args"] == (str(job_id), request.model_dump(mode="json"))
    options = captured["options"]
    assert isinstance(options, dict)
    # The supervisor's hard limit sits above the job budget so its own timers fire first.
    assert options["time_limit"] > 60
