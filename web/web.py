import os
from flask import Flask

app = Flask(__name__)
app.debug = os.environ.get("DEVELOPMENT") is not None


@app.route('/')
def hello_world():
    return 'Hello Testing world'


if __name__ == '__main__':
    app.run()
