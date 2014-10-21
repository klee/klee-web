import os

from flask import Flask, request, render_template
from ..worker.worker import submit_code

app = Flask(__name__)
app.debug = os.environ.get("DEVELOPMENT") is not None

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        code = request.form['code']

        # Submit task to queue
        task = submit_code.delay(code)
        task_id = task.task_id
        result = submit_code.AsyncResult(task_id).get(timeout=30.0)

        return render_template('result.html', result=result)
    else:
        return render_template('index.html')

if __name__ == '__main__':
    app.run()
