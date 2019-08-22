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


WEBPAGE = os.environ.get('MAIN_WEBPAGE')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')
password = os.environ.get('GMAIL_PASSWORD')
sender_email = "klee.tests@gmail.com"
receivers_email = ["denis.gavrielov18@ic.ac.uk"]


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


e2e = "sudo docker run --rm -e WEBPAGE=" + WEBPAGE + \
      " -e ADMIN_PASSWORD=" + ADMIN_PASSWORD + \
      " --network $(sudo docker network ls | grep bridge | sed -n '2 p' " + \
      "| awk '{print $2}') -v /titb/src/klee_web/tests/js_tests/" + \
      "test_files/:/titb/src/klee_web/tests/js_tests/test_files/ " + \
      "e2e_test_js 2> ~/e2e_report_stderr.txt > ~/e2e_report_stdout.txt"
exit_code_e2e = os.system(e2e)

if (exit_code_e2e):
    status = "FAILED! - "
    msg = "Some or all end-to-end tests failed!"
else:
    status = "Success -"
    msg = "All end-to-end tests ran fine."

port = 465  # For SSL
# Create a secure SSL context
context = ssl.create_default_context()

message = MIMEMultipart("alternative")

message["Subject"] = status + "KLEE testing report"
message["From"] = sender_email
message["To"] = ', '.join(receivers_email)

body = "Hi,\n\n" + msg + \
       " Please note that all the tests are running from a VM within the" + \
       " same cloud network as the web server." + \
       "\n\nThe status return code of the end-to-end tests is: " + \
       str(exit_code_e2e) + \
       "\n\nThe output of all tests are attached in this email." + \
       "\n\nBest,\nKLEE Web"

home = os.path.expanduser('~')
message.attach(MIMEText(body, "plain"))
message.attach(add_attachment(home + "/e2e_report_stdout.txt"))
message.attach(add_attachment(home + "/e2e_report_stderr.txt"))

if os.environ.get('DEVELOPMENT') is None:
    with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receivers_email, message.as_string())
else:
    print('Results have been placed into the home directory')
