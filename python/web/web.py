import os

from flask import Flask, request, render_template
from ..worker.worker import submit_code
app = Flask(__name__)

app.debug = os.environ.get("DEVELOPMENT") is not None


def submit_task(code):
    task = submit_code.delay(code)
    task_id = task.task_id
    result = submit_code.AsyncResult(task_id).get(timeout=30.0)
    return render_template('result.html', result=result)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        f = request.files['file']
        if f:
            code = f.read()
            f.close()
        else:
            code = request.form['code']

        return submit_task(code)
    else:
        return render_template('index.html')

if __name__ == '__main__':
    app.run()
