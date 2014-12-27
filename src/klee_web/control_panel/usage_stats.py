import datetime

from django.db.models import Min

from frontend.models import Task


def last_seven_days():
    base = datetime.date.today()
    date_list = [base - datetime.timedelta(days=x) for x in range(6, -1, -1)]
    days = map(lambda y: y.strftime('%a'), date_list[:5])
    days.extend(['Yesterday', 'Today'])
    jobs = map(jobs_per_day, date_list)

    return days, jobs


def jobs_per_day(day):
    return Task.objects.filter(
        created_at__range=(day, day + datetime.timedelta(days=1)),
        completed_at__isnull=False).count()


def avg_job_duration():
    completed_tasks = Task.objects.filter(completed_at__isnull=False).values()
    duration = datetime.timedelta(seconds=0)
    for job in completed_tasks:
        duration += job['completed_at'] - job['created_at']

    seconds = duration.total_seconds()

    num_completed_tasks = len(completed_tasks)
    if num_completed_tasks > 0:
        return round(seconds / num_completed_tasks, 2)
    else:
        return 0


def avg_jobs_per_day():
    first_day = Task.objects.all() \
        .aggregate(Min('created_at'))['created_at__min']

    if first_day:
        job_count = Task.objects.all().count()
        total_days = (datetime.datetime.now() - first_day).days + 1

        return job_count / total_days
    else:
        return 0
