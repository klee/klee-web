import os

from flask import Flask, request, render_template

app = Flask(__name__)
app.debug = os.environ.get("DEVELOPMENT") is not None


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Do upload to celery
        code = request.form['code']

        
        return request.form['code']
    else:
        return render_template('index.html')

if __name__ == '__main__':
    app.run()
