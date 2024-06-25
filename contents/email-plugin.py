#!/usr/bin/env python

#####
# email.py
# This script emails a message and files to a user
#
# Chris Gadd
# 2021-11-12
#####

import mimetypes
import os
import pathlib
import re
import smtplib
import sys
import tempfile
import zipfile

from email.message import EmailMessage

# Read Rundeck info from environment variables
subject = os.environ["RD_CONFIG_SUBJECT"]
body = os.environ.get("RD_CONFIG_BODY")
metadata = os.environ.get("RD_CONFIG_METADATA") == "true"
format = os.environ["RD_CONFIG_FORMAT"]
recipients = os.environ["RD_CONFIG_RECIPIENTS"]
files = os.environ.get("RD_CONFIG_FILES")
zip = os.environ.get("RD_CONFIG_ZIP") == "true"
errorifmissing = os.environ.get("RD_CONFIG_ERRORIFMISSING") == "true"
smtp_server = os.environ["RD_CONFIG_SMTP_SERVER"]
serverUrl = os.environ["RD_JOB_SERVERURL"]
user = os.environ["RD_JOB_USERNAME"]
jobName = os.environ["RD_JOB_NAME"]
jobGroup = os.environ.get("RD_JOB_GROUP", "-")
jobProject = os.environ["RD_JOB_PROJECT"]
jobUrl = os.environ["RD_JOB_URL"]
execId = os.environ["RD_JOB_EXECID"]
verbose = os.environ["RD_JOB_LOGLEVEL"] == "DEBUG"

# Sender email address is already in a config file but not AFAIK available to plugins as an environment variable.
configFile = "/etc/rundeck/rundeck-config.properties"
pattern = r"grails\.mail\.default\.from\s*=\s*(.*)"
with open (configFile, 'r') as file:
  content = file.read()
  match = re.search(pattern, content)
if match:
  sender = match.group(1).strip()
else:
  sys.exit("Unable to determine sender address.")

# Convert delimited recipient and file string to list
recipients = re.split('[,; ]', recipients)
raw_files = []
if files:
  raw_files = re.split('[,; ]', files)

# Files may be globs (wildcards) or directories so get matching files
attachments = []
for file in raw_files:
  if pathlib.Path(file).is_dir():
    for dir_item in pathlib.Path(file).iterdir():
      if not dir_item.is_dir():
        attachments.append(dir_item)
  else:
    dir = pathlib.Path(file).parent
    filename = pathlib.Path(file).name
    matched_files = list(pathlib.Path(dir).glob(filename))
    if not matched_files and errorifmissing:
      sys.exit(f"No files found matching {file}")
    attachments.extend(matched_files)

if metadata:
  # append execution metadata to body
  if format == "Plaintext":
    body += f"""

---
Execution details
- Job: {jobProject}/{jobGroup}/{jobName}
- User: {user}
- Execution output: {jobUrl}

This email was sent by the Rundeck system at {serverUrl}.
"""
  else:
    body += f"""
<br>
<hr>
<h3>Execution details</h3>
<ul>
<li><em>Job:</em> {jobProject}/{jobGroup}/{jobName}</li>
<li><em>User:</em> {user}</li>
<li><em>Execution output:</em> <a href="{jobUrl}">#{execId}</a></li>
</ul>
<br>
<p>This email was sent by the <a href="{serverUrl}">Rundeck system</a>.</p>
"""

if format == "Plaintext":
  mime_format = "plain"
elif format == "Monospace":
  mime_format = "html"
  body = "<pre>" + body + "</pre>"
else:
  mime_format = "html"

message = EmailMessage()
message["From"] = sender
message["To"] = ", ".join(recipients)
message["Subject"] = subject
message.set_content(body, subtype=mime_format)

if files:
  if zip:
    zip_directory = tempfile.TemporaryDirectory()
    zip_path = pathlib.PurePath(zip_directory.name, "attachments.zip")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
      for file in attachments:
        if verbose:
          print(f"Zipping file: {file}")
        zip_file.write(file, arcname=file.name)
    attachments = [zip_path]
  for file in attachments:
    filename = file.name
    if verbose:
      print(f"Attaching file: {filename}")
    # Guess the content type based on the file's extension.  Encoding
    # will be ignored, although we should check for simple things like
    # gzip'd or compressed files.
    ctype, encoding = mimetypes.guess_type(filename)
    if ctype is None or encoding is not None:
      # No guess could be made, or the file is encoded (compressed), so
      # use a generic bag-of-bits type.
      ctype = 'application/octet-stream'
    maintype, subtype = ctype.split('/', 1)
    with open(file, "rb") as f:
      message.add_attachment(f.read(),
        maintype=maintype,
        subtype=subtype,
        filename=filename
      )

with smtplib.SMTP(smtp_server) as s:
  try:
    s.send_message(message)
  except smtplib.SMTPSenderRefused as e:
    if e.smtp_code == 552:
      sys.exit("ERROR: Attachment exceeds maximum of 10MB, unable to send.")
    else:
      sys.exit(e)
