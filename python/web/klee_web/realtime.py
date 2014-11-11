import os
import pusher

p = pusher.Pusher(
    app_id='94725',
    key=os.environ['PUSHER_KEY'],
    secret=os.environ['PUSHER_SECRET']
)


def notify(channel, notification_type, data):
    try:
        p[channel].trigger(notification_type, {'data': data})
    except Exception as e:
        print e
