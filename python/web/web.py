import os

from flask import Flask, request, render_template
from celery import Celery

app = Flask(__name__)
app.debug = os.environ.get("DEVELOPMENT") is not None
app.config.update(
    BROKER_URL=os.environ.get("RABBITMQ_HOST"),
    RESULT_BACKEND=os.environ.get("RABBITMQ_HOST")
)


def make_celery(app):
    celery = Celery(app.import_name, broker=app.config['BROKER_URL'])
    celery.conf.update(app.config)
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    return celery

celery = make_celery(app)


@celery.task
def add_together(a, b):
    return a + b


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        code = request.form['code']
        # Do upload to celery
        task = add_together.apply_async(5, 6)
        task_id = task.task_id

        result = add_together.AsyncResult(task_id).get(timeout=1.0)

        return result
    else:
        return render_template('index.html')

if __name__ == '__main__':
    app.run()
