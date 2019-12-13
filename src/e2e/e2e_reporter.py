"""
This script pings the webpage and runs the JavaScript e2e tests.
An email is sent to inform about the outcomes of these tests.
"""
import os
import smtplib
import ssl

from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


password = os.environ.get('GMAIL_PASSWORD')
sender_email = "klee.tests@gmail.com"
receivers_email = os.environ.get('ALERT_EMAILS').split(",")
DEVELOPMENT = True if os.environ['DEVELOPMENT'] == "1" else False


def add_attachment(filename: str):
    """
    filename: path to the file to be attached.

    Returns part to be attached to the MIMEMultipart object.
    """
    with open(filename, "rb") as attachment:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())

    encoders.encode_base64(part)
    part.add_header(
        "Content-Disposition",
        "attachment; filename=" + filename.split('/')[-1],
    )
    return part


rc = os.system("npm test > /tmp/e2e_report.txt 2>&1")

if (rc != 0):
    status = "FAILED! - "
    msg = "Some or all end-to-end tests failed!"
else:
    status = "Success -"
    msg = "All end-to-end tests ran fine."

port = 465  # For SSL
# Create a secure SSL context
context = ssl.create_default_context()

message = MIMEMultipart()

message["Subject"] = status + "KLEE-Web daily testing report"
message["From"] = sender_email
message["To"] = ', '.join(receivers_email)

body = "Hi,\n\n" + msg + \
       "\n\nThe status return code of the end-to-end tests is: " + \
       str(rc) + \
       "\n\nThe output of all tests are attached in this email." + \
       "\n\nBest,\nKLEE Web\n"

message.attach(MIMEText(body, "plain"))
message.attach(add_attachment("/tmp/e2e_report.txt"))

if not DEVELOPMENT:
    with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receivers_email, message.as_string())
else:
    print('Results have been placed into the home directory')
