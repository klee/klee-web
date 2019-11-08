# Updating Daily Email Test Reports

Currently, there is one VM provisioned to run a daily end-to-end test for the Klee Web server and send a report via email.

## Update Email Recipients

To update the email recipients open the file `src/klee_web/tests/automated_e2e_tests.py`.

Find the line which assigns a Python list to the `receivers_email` variable.

```bash
receivers_email = ["<add/remove your email>"]
```

Add or delete recipients from this list.

Finally, push the changes to the master branch and provision the testing machine as illustrated in the DEPLOY.md file.

## Update Sender Email and Password

Currently, the sender email is specified on this line:

```bash
sender_email = "klee.tests@gmail.com"
```

`klee.tests@gmail.com` is a Gmail account that was created for the daily automated test report. This account can be replaced, but keep in mind to possibly change security settings with your email account to allow the Python script to log onto the account.

The password is added through the environmental variable `GMAIL_PASSWORD` which is securely stored in the Ansible vault. To update the password, update it in the email account and the Ansible vault.

Open the secrets file with the Ansible vault command (Make sure to have the `.klee_vault_password` file in your home directory. You can acquire this file from the current maintainers of the website:

```bash
ansible-vault edit --vault-password-file=~/.klee_vault_password provisioning/vars/secrets.yml
```

This command will decrypt and open the `secrets.yml` file and any changes to the variables will be saved.

If you simply want to view the password for the Gmail account you can use the `ansible-vault view` command without the risk of accidentally changing variables:

```bash
ansible-vault view --vault-password-file=~/.klee_vault_password provisioning/vars/secrets.yml
```

Finally, provision the testing machine as illustrated in the `DEPLOY.md` file.

## Update Date and Time of Automated Tests

To update the configuration of the cronjob the provisioning has to be updated. The file `provisioning/roles/e2e-tests/tasks/main.yml` holds the provisioning task to install the cronjob. Currently named "Add cronjob for automated tests daily at 2pm", this task can be modified to any typical cronjob setting.

```yml
- name: Add cronjob for automated tests daily at 2pm
  cron:
    name: "Test Klee Web"
    minute: "0"
    hour: "14"
    job: "/src/python_runner.sh /usr/bin/python3 /titb/src/klee_web/tests/automated_e2e_tests.py"
    user: klee
  when: not ci
```

For example, you can change the hour setting to receive the email at a different time of the day. Other options can be explored from the [official Ansible cron documentation](https://docs.ansible.com/ansible/latest/modules/cron_module.html).

Finally, provision the testing machine as illustrated in the `DEPLOY.md` file.

### Debugging the cronjob

If you believe that the cronjob is not starting or starting at the wrong time, you can always ssh into the testing machine and check the crontab. The cronjob is currently assigned by the user `"klee"`. So after establishing an ssh connection to the testing VM run the following commands:

```bash
sudo su klee
crontab -e
```

With the example of the above cronjob configured by Ansible, you should see the following content:

```bash
#Ansible: Test Klee Web
0 14 * * * /src/python_runner.sh /usr/bin/python3 /titb/src/klee_web/tests/automated_e2e_tests.py
```

## Continuous Website Availability Alerts

The test reports are essential to check the functionality of the website. However, they are designed to inform the maintainer of the website only once a day. To get more up-to-date alerts a monitoring service was set up.

**UptimeRobot** is a free monitoring service that issues a HTTP request to the website every 5 minutes and sends an email alert if the site did not respond. It then pings the site every 5 minutes again and sends an email update once the site responds again.

This does not test if the website functionalities are working as expected, but it does check the status of the website overall.

To add or remove yourself from the email list, you need to first obtain the password for the account with:

```bash
ansible-vault view --vault-password-file=~/.klee_vault_password provisioning/vars/secrets.yml
```

Note down the `uptimerobot_password`. Visit [uptimerobot.com](https://uptimerobot.com/) and log in with the email address `klee.tests@gmail.com` and the password you have noted down.

Under `My Settings` you can add or remove Alert Contacts by simply adding the email address for which you want to receive the emails.

Here you also have a dashboard to check the availability of the web server for the last 30 days.
