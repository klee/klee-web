import os
import pusher

pusher = pusher.Pusher(
    app_id='94725',
    key=os.environ['PUSHER_KEY'],
    secret=os.environ['PUSHER_SECRET']
)


def notify(channel, notification_type, data):
    pusher[channel].trigger(notification_type, {'data': data})
