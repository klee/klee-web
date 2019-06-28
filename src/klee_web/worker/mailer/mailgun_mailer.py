import os
import requests

MAILGUN_URL = 'sandboxf39013a9ad7c47f3b621a94023230030.mailgun.org'


class MailgunMailer():
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ['MAILGUN_API_KEY']

    def send_mail(self, recipient, subject, email_body):
        requests.post(
            'https://api.mailgun.net/v2/{}/messages'.format(MAILGUN_URL),
            auth=('api', self.api_key),
            data={
                'from': 'KLEE-Web <postmaster@{}>'.format(MAILGUN_URL),
                'to': recipient,
                'subject': subject,
                'text': email_body
            }
        )
