#!/usr/bin/env bash

#####
# email.sh
# This script emails a message and files to a user
# It's very flakey, won't handle spaces in filenames
#
# Chris Gadd
# 2021-04-13
#####

SUBJECT="$RD_CONFIG_SUBJECT"
BODY="$RD_CONFIG_BODY"
RECIPIENTS="$RD_CONFIG_RECIPIENTS"
FILES="$RD_CONFIG_FILES"
ZIP="$RD_CONFIG_ZIP"
ERRORIFMISSING="$RD_CONFIG_ERRORIFMISSING"
SERVER=$RD_JOB_SERVERURL

# FILES may contain globs, disable that for now
set -o noglob

# Strip protocol and port from URL
FROM=${RD_JOB_SERVERURL#*//}
FROM=${FROM%:*}
FROM="rundeck@$FROM"

# Convert delimters to spaces
RECIPIENTS=$(echo $RECIPIENTS | sed 's/[,;]/ /g')
FILES=$(echo $FILES | sed 's/[,;]/ /g')

# Files may be globs so get matching files
FILENAMES=""
for FILEPATH in $FILES; do
  set -o noglob
  # Do some basic checks that the files aren't anywhere sensitive
  REALPATH=$(realpath $FILEPATH)
  if [[ "$REALPATH" =~ ^/etc/rundeck/ ]]; then
    echo "Invalid destination: $FILEPATH"
    exit 1
  fi
  set +o noglob
  MOREFILES=$(ls $FILEPATH 2>/dev/null | tr "\n" " ")
  if [[ $? -eq 0 ]]; then
    FILENAMES="${FILENAMES} ${MOREFILES}"
  elif [[ $ERRORIFMISSING == "true" ]]; then
    echo "No files matching $FILEPATH"
    exit 1
  fi
done

# Zip into temp folder
if [[ $ZIP == "true" ]]; then
  ZIPFOLDER=$(mktemp -d)
fi

[[ "${RD_JOB_LOGLEVEL:-}" == "DEBUG" ]] && echo -e "Attaching files:\n $FILENAMES"
ATTACHMENTS=""
if [[ -n $FILENAMES ]]; then
  if [[ $ZIP == "true" ]]; then
    zip --quiet --junk-paths $ZIPFOLDER/attachments.zip $FILENAMES
    ATTACHMENTS="-a $ZIPFOLDER/attachments.zip"
  else
    ATTACHMENTS="-a $(echo $FILENAMES | sed 's/ / -a /g')"
  fi
fi

[[ "${RD_JOB_LOGLEVEL:-}" == "DEBUG" ]] && OPTIONS="$OPTIONS -v"
echo "$BODY" | mailx $OPTIONS -s "$SUBJECT" $ATTACHMENTS -r $FROM $RECIPIENTS

if [[ $ZIP == "true" ]]; then
  rm -rf $ZIPFOLDER
fi
