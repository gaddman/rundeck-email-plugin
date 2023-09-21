This adds a workflow and node step to send email. Tested on Linux with RPM install and Python3.10.

## Installation
- Clone: `git clone https://github.com/gaddman/rundeck-email-plugin`
- Edit `email-plugin.py`, replacing `SMTP_SERVER_ADDRESS` with a valid SMTP server address.
- Zip folder: From the parent folder run `zip -r rundeck-email-plugin.zip rundeck-email-plugin -x "rundeck-email-plugin/.git*" "rundeck-email-plugin/README.md"`
- Copy to Rundeck: `cp rundeck-email-plugin.zip /var/lib/rundeck/libext/`