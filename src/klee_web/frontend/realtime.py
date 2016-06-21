import os
import pusher

pusher = pusher.Pusher(
    app_id='94725',
    key=os.environ['PUSHER_KEY'],
    secret=os.environ['PUSHER_SECRET']
)


def send_notification(channel, notification_type, data):
    pusher.trigger(channel, notification_type, {'data': data})
