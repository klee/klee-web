import os
import pusher

pusher = pusher.Pusher(
    app_id='94725',
    key=os.environ['PUSHER_KEY'],
    secret=os.environ['PUSHER_SECRET']
)


def notify(channel, data):
    pusher[channel].trigger('notification', {'data': data})


def deliver_result(channel, data):
    pusher[channel].trigger('result', {'result': data})
