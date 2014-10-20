import os

from flask import Flask, request, render_template
from celery import Celery

app = Flask(__name__)
app.debug = os.environ.get("DEVELOPMENT") is not None
app.config.update(
    BROKER_URL=os.environ.get("RABBITMQ_HOST"),
    CELERY_RESULT_BACKEND='amqp'
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


@celery.task
def submit_code(code):
    return 'Done something with:\n{}'.format(code)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        code = request.form['code']

        # Submit task to queue
        task = submit_code.delay(code)
        task_id = task.task_id
        result = submit_code.AsyncResult(task_id).get(timeout=1.0)

        return render_template('result.html', result=result)
    else:
        return render_template('index.html')

if __name__ == '__main__':
    app.run()
