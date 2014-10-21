import os
from celery import Celery

celery = Celery(broker=os.environ["BROKER_URL"], backend="rpc")

@celery.task(name='submit_code')
def submit_code(code):
    return 'Done something with:\n{}'.format(code)