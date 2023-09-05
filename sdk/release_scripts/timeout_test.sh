#!/bin/bash

echo "## Generating a common prefix for this round of test..."
COMMON_NAME=$(python -c 'import uuid; print(uuid.uuid4().hex)' | tr -dc 'a-zA-Z' | head -c 6)
echo "Done"
echo

SCRIPT_PATH=$(realpath "$0")
SCRIPT_FOLDER=$(dirname "$SCRIPT_PATH")
LEPTON_TEST_FOLDER=$SCRIPT_FOLDER/../leptonai/tests
lep photon create -n "${COMMON_NAME}" -m "${LEPTON_TEST_FOLDER}/shell/shell.py"
lep photon push -n "${COMMON_NAME}"
echo "## Running a photon..."
lep photon run -n "${COMMON_NAME}" -dn "${COMMON_NAME}" --no-traffic-timeout 600

echo "## Start time:"
date

# Wait for status to be "Running"
command="lep deployment list | grep ${COMMON_NAME} | grep Running"
RETRY=0
while ! eval "$command" > /dev/null; do
    echo "Deployment is not up yet. Sleep for 5 seconds."
    RETRY=$((RETRY+1))
    if [ $RETRY -ge 100 ]; then
        echo "Too many retries and the deployment is still not up."
        echo "I am going to give up."
        break
    fi
    sleep 5
done
# Now, wait for status to be "Not Ready"
command="lep deployment list | grep ${COMMON_NAME} | grep 'Not Ready'"
RETRY=0
while ! eval "$command" > /dev/null; do
    echo "Deployment is not down yet. Sleep for 5 seconds."
    RETRY=$((RETRY+1))
    if [ $RETRY -ge 100 ]; then
        echo "Too many retries and the deployment is still not down."
        echo "I am going to give up."
        break
    fi
    sleep 5
done
echo "## End time:"
date
echo "## Final status"
lep dep status -n "${COMMON_NAME}"

echo "## Deleting the photon..."
lep dep remove -n "${COMMON_NAME}"
lep photon remove -n "${COMMON_NAME}"