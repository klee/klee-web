import os
from validate_email import validate_email
from flask import Flask, request, render_template, flash
from ..worker.worker import submit_code
app = Flask(__name__)

app.debug = os.environ.get("DEVELOPMENT") is not None
app.secret_key = os.environ['FLASK_SECRET_KEY']


def submit_task(code, email):
    task = submit_code.delay(code, email)
    task_id = task.task_id
    result = submit_code.AsyncResult(task_id).get(timeout=30.0)
    return render_template('result.html', result=result)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        f = request.files['file']
        email = request.form['email']
        if email and not validate_email(email, verify=True):
            flash("Invalid email address")
            return render_template("index.html")
        if f:
            code = f.read()
            f.close()
        else:
            code = request.form['code']

        return submit_task(code, email)
    else:
        return render_template('index.html')

if __name__ == '__main__':
    app.run()
