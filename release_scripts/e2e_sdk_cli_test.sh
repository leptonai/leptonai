#!/bin/bash

################################################################################
# Scripts that you should run to check that most of the components work from the
# CLI perspective, when you cut a release.
#
# Run the command without any arguments. You will need to have access to at least
# one workspace.
# - If you want to test interactive login, do not set LEPTON_RELEASE_CREDENTIALS,
#   otherwise set it to a credential string.
# - If you want the script to pause when an error happens, set PAUSE to true.
################################################################################
PAUSE=false
CURL="curl --max-time 10"

################################################################################
# Utility functions
################################################################################
is_port_occupied() {
  (echo >/dev/tcp/localhost/"$1") &>/dev/null
  return $?
}

find_empty_port() {
    local port
    for port in {49152..65535}; do
        if is_port_occupied "$port"; then
            continue
        fi
        echo "$port"
        return
    done
    echo "This should not happen: all ports are taken."
    exit 1
}

echo "################################################################################"
echo "# Logging out and Logging in."
echo "################################################################################"

TOTAL_ERRORS=0

# First, log out of any existing workspace.
echo "Logging out of any existing workspace..."
if lep logout; then
    echo "Done"
else
    echo "lep logout failed. This should not happen."
    exit 1
fi

# Log in to a workspace.
echo "Logging in..."
if [ -n "${LEPTON_RELEASE_CREDENTIALS}" ]; then
    lep login -c "$LEPTON_RELEASE_CREDENTIALS"
else
    lep login
fi
echo "Trying to see if thing are working..."
if lep ws status | grep "build time" > /dev/null; then
    echo "Verified that workspace login worked."
else
    echo "lep ws status failed. This should not happen."
    if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
fi
echo

echo "Obtaining token and workspace id..."
LEPTON_WS_TOKEN=$(lep workspace token)
LEPTON_WS_URL=$(lep workspace url)
echo "Done"
echo

echo "Obtaining lepton sdk test folder..."
SCRIPT_PATH=$(realpath "$0")
SCRIPT_FOLDER=$(dirname "$SCRIPT_PATH")
LEPTON_TEST_FOLDER=$SCRIPT_FOLDER/../leptonai/tests
echo "Path for lepton test folder: $LEPTON_TEST_FOLDER"
echo "Done"
echo

echo "################################################################################"
echo "# Basic tests: photon, create, push, run"
echo "################################################################################"

echo "## Generating a common prefix for this round of test..."
COMMON_NAME=$(python -c 'import uuid; print(uuid.uuid4().hex)' | tr -dc 'a-zA-Z' | head -c 6)
echo "Done"
echo

echo "## Testing creating a local photon..."
command="lep photon create -n ${COMMON_NAME} -m $LEPTON_TEST_FOLDER/shell/shell.py"
if eval "$command"; then
    echo "Done"
else
    echo "Failed. This should not happen. Reproduce with: $command"
    if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
fi
echo

echo "## Testing running photon locally..."
PORT=$(find_empty_port)
echo "Using port $PORT"
lep photon run -n "${COMMON_NAME}" --local -p "$PORT" &>/dev/null &
PID=$!
# sleep just so the photon has time to start up
echo "Done"
echo "sleep for 5 seconds to make sure the photon is up..."
sleep 5
echo

echo "## Testing calling the local photon..."
if ${CURL} -f -s -X "POST" "http://localhost:$PORT/run" -d '{"query": "echo yes"}' -H 'Content-Type: application/json' | grep "yes" > /dev/null; then
    echo "Done"
else
    echo "Local photon failed. This should not happen."
    kill $PID
    if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
fi
echo

echo "## Cleaning the local photon run..."
kill $PID
echo "Done"
echo

echo "## Testing pushing photon to remote..."
command="lep photon push -n ${COMMON_NAME}"
if eval "$command"; then
    echo "Done"
else
    echo "Failed. This should not happen. Reproduce with: $command"
    if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
fi
echo

echo "## Testing if the photon is pushed by listing remote photons..."
command="lep photon list --pattern ${COMMON_NAME} | grep ${COMMON_NAME}"
if eval "$command" > /dev/null; then
    echo "Done"
else
    echo "Failed. This should not happen. Reproduce with: $command"
    if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
fi
echo

echo "## Testing running a photon..."
command="lep photon run -n ${COMMON_NAME} -dn ${COMMON_NAME}"
if eval "$command" > /dev/null; then
    echo "Done"
else
    echo "Failed. This should not happen. Reproduce with: $command"
    if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
fi
echo

echo "## Testing running a photon with the same name: this should be caught by apiserver..."
command="lep photon run -n ${COMMON_NAME} -dn ${COMMON_NAME}"
if eval "$command" > /dev/null; then
    echo "Expected command to fail but it passed. This should not happen. Reproduce with: $command"
    if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
else
    echo "Done"
fi
echo

echo "## Testing running a photon with a different name..."
command="lep photon run -n ${COMMON_NAME} -dn ${COMMON_NAME}-1"
if eval "$command" > /dev/null ; then
    echo "Done"
else
    echo "Failed. This should not happen. Reproduce with: $command"
    if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
fi
echo

echo "## Testing deleting the extra deployment"
command="lep dep remove -n ${COMMON_NAME}-1"
if eval "$command"; then
    echo "Done"
else
    echo "Failed. This should not happen. Reproduce with: $command"
    if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
fi
echo

echo "Basic tests finished. Errors so far = ${TOTAL_ERRORS}"
echo

echo "################################################################################"
echo "# deployment"
echo "################################################################################"
echo "## Testing listing deployments..."
command="lep deployment list | grep ${COMMON_NAME}"
if eval "$command" > /dev/null; then
    echo "Done"
else
    echo "Failed. This should not happen. Reproduce with: $command"
    if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
fi
echo

echo "## Waiting for the deployment to be up..."
command="lep deployment list | grep ${COMMON_NAME} | grep Ready"
RETRY=0
while ! eval "$command" > /dev/null; do
    echo "Deployment is not up yet. Sleep for 5 seconds."
    RETRY=$((RETRY+1))
    if [ $RETRY -ge 100 ]; then
        echo "Too many retries and the deployment is still not up."
        echo "I am going to give up."
        if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
        break
    fi
    sleep 5
done
echo "Done"
echo
# sleep for 15 seconds to make sure the deployment is up
sleep 15
echo

echo "## Testing deployment status..."
command="lep deployment status -n ${COMMON_NAME} | grep ${COMMON_NAME}"
if eval "$command" > /dev/null; then
    echo "Done"
else
    echo "lep deployment status failed. This should not happen. Reproduce with: $command"
    if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
fi
echo

echo "## Testing deployment log content..."
command="lep deployment log -n ${COMMON_NAME}"
if ! timeout --help > /dev/null; then
    echo "Cannot find timeout, skipping test."
else
    if eval timeout 10 "$command" | grep "Uvicorn running on" > /dev/null; then
        echo "Done"
    else
        echo "lep deployment log failed. Did not find expected log content, or log api is too slow. This should not happen. Reproduce with: $command"
        if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
    fi
fi
echo

echo "## Testing calling the deployment..."
command="${CURL} -f -s -X 'POST' ${LEPTON_WS_URL}/run \
              -H 'Content-Type: application/json' \
              -H 'accept: application/json' \
              -H 'X-Lepton-Deployment: ${COMMON_NAME}' \
              -H 'Authorization: Bearer ${LEPTON_WS_TOKEN}' \
              -d '{\"query\": \"echo yes\"}'"
if eval "$command" | grep "yes" > /dev/null; then
    echo "Done"
else
    echo "Deployment returned content did not contain expected output. This should not happen. Reproduce with: $command"
    if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
fi
echo

echo "Deployment tests finished. Errors so far = ${TOTAL_ERRORS}"
echo

echo "################################################################################"
echo "# Environment variables and Secrets"
echo "################################################################################"

echo "## Testing creating secrets..."
SECRET_NAME=${COMMON_NAME}SECRET
command="lep secret create -n ${SECRET_NAME} -v \"world\""
if eval "$command"; then
    echo "Done"
else
    echo "lep secret create failed. This should not happen. Reproduce with: $command"
    if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
fi
echo

echo "## Testing listing secrets..."
command="lep secret list | grep ${SECRET_NAME}"
if eval "$command" > /dev/null; then
    echo "Done"
else
    echo "lep secret list failed. This should not happen. Reproduce with: $command"
    if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
fi
echo

echo "## Testing creating a deployment with env variables and secrets..."
command="lep photon run -n ${COMMON_NAME} -dn ${COMMON_NAME}-with-env -e \"HELLOENV=world\" -s ${SECRET_NAME} -s RENAMEDSECRET=${SECRET_NAME}"
if eval "$command"; then
    echo "Done"
else
    echo "lep photon run failed. This should not happen. Reproduce with: $command"
    if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
fi
echo

echo "## Waiting for the deployment to be up..."
command="lep deployment list | grep ${COMMON_NAME}-with-env | grep Ready"
RETRY=0
while ! eval "$command" > /dev/null; do
    echo "Deployment is not up yet. Sleep for 5 seconds."
    RETRY=$((RETRY+1))
    if [ $RETRY -ge 100 ]; then
        echo "Too many retries and the deployment is still not up."
        echo "I am going to give up."
        if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
        break
    fi
    sleep 5
done
# sleep for 15 seconds to make sure the deployment is up
sleep 15
echo

echo "## Testing if the deployment contains the correct env variables and secrets..."
command="${CURL} -f -s -X 'POST' ${LEPTON_WS_URL}/run \
              -H 'Content-Type: application/json' \
              -H 'accept: application/json' \
              -H 'X-Lepton-Deployment: ${COMMON_NAME}-with-env' \
              -H 'Authorization: Bearer ${LEPTON_WS_TOKEN}' \
              -d '{\"query\": \"env | grep HELLOENV \"}'"

if eval "$command" | grep "world" > /dev/null; then
    echo "Env variable is correct."
else
    echo "Did not contain expected env var. Reproduce with: $command"
    if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
fi
command="${CURL} -f -s -X 'POST' ${LEPTON_WS_URL}/run \
              -H 'Content-Type: application/json' \
              -H 'accept: application/json' \
              -H 'X-Lepton-Deployment: ${COMMON_NAME}-with-env' \
              -H 'Authorization: Bearer ${LEPTON_WS_TOKEN}' \
              -d '{\"query\": \"env | grep ${SECRET_NAME} \"}'"
if eval "$command" | grep "world" > /dev/null; then
    echo "Secret value is correct."
else
    echo "Did not contain expected secret. Reproduce with: $command"
    if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
fi
command="${CURL} -f -s -X 'POST' ${LEPTON_WS_URL}/run \
              -H 'Content-Type: application/json' \
              -H 'accept: application/json' \
              -H 'X-Lepton-Deployment: ${COMMON_NAME}-with-env' \
              -H 'Authorization: Bearer ${LEPTON_WS_TOKEN}' \
              -d '{\"query\": \"env | grep RENAMEDSECRET \"}'"
if eval "$command" | grep "world" > /dev/null; then
    echo "Renamed secret value is correct."
else
    echo "Did not contain expected renamed secret. Reproduce with: $command"
    if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
fi
echo

echo "## Testing deleting deployment with env variables and secrets..."
command="lep dep remove -n ${COMMON_NAME}-with-env"
if eval "$command"; then
    echo "Done"
else
    echo "lep dep remove failed. This should not happen. Reproduce with: $command"
    if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
fi
echo

echo "## Testing deleting secrets..."
command="lep secret remove -n ${COMMON_NAME}"
if eval "$command"; then
    echo "Done"
else
    echo "lep secret remove failed. This should not happen. Reproduce with: $command"
fi
echo

echo "Env and secret tests finished. Errors so far = ${TOTAL_ERRORS}"
echo

echo "################################################################################"
echo "# Deployment manipulation: update replicas and authentication tokens"
echo "################################################################################"
echo "Testing updating the deployment replicas to 2..."
command="lep dep update -n ${COMMON_NAME} --min-replicas 2"
if eval "$command"; then
    echo "Done"
else
    echo "update to 2 replicas. This should not happen. Reproduce with: $command"
    if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
fi
echo

# Verify if things are actually correct
command="lep dep status -n ${COMMON_NAME}"
if eval "$command" | grep "out of 2 replicas ready" > /dev/null; then
    echo "Replicas are correct."
else
    echo "Replicas are not correct. Reproduce with: $command"
    if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
fi
# scale back to 1 replica
echo "Testing reducing the deployment replicas to 1..."
command="lep dep update -n ${COMMON_NAME} --min-replicas 1"
if eval "$command"; then
    echo "Done"
else
    echo "reduce to 1 replica. This should not happen. Reproduce with: $command"
    if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
fi
echo
# Verify if things are actually correct. Will sleep for 10 seconds for replicas to wind down.
sleep 10
command="lep dep status -n ${COMMON_NAME}"
if eval "$command" | grep "out of 1 replicas ready" > /dev/null; then
    echo "Replicas are correct."
else
    echo "Replicas are not correct. Reproduce with: $command"
    if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
fi
echo

echo "Testing updating the deployment to public..."
command="lep dep update -n ${COMMON_NAME} --public"
if eval "$command"; then
    echo "Done"
else
    echo "lep dep update failed. This should not happen. Reproduce with: $command"
    if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
fi
command="lep dep status -n ${COMMON_NAME}"
if eval "$command" | grep "Is Public:" | grep "Yes" > /dev/null; then
    echo "Authentication tokens are correct."
else
    echo "Authentication tokens are not correct. Reproduce with: $command"
    if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
fi
echo "Testing updating the deployment to private..."
command="lep dep update -n ${COMMON_NAME} --no-public"
if eval "$command"; then
    echo "Done"
else
    echo "lep dep update failed. This should not happen. Reproduce with: $command"
    if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
fi
command="lep dep status -n ${COMMON_NAME}"
if eval "$command" | grep "Is Public:" | grep "No" > /dev/null; then
    echo "Authentication tokens are correct."
else
    echo "Authentication tokens are not correct. Reproduce with: $command"
    if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
fi

echo "Testing updating the deployment with additional tokens..."
command="lep dep update -n ${COMMON_NAME} --tokens ncc1701"
if eval "$command"; then
    echo "Done"
else
    echo "lep dep update failed. This should not happen. Reproduce with: $command"
    if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
fi
command="lep dep status -n ${COMMON_NAME} --show-tokens"
if eval "$command" | grep "ncc1701" > /dev/null; then
    echo "Authentication tokens are correct."
else
    echo "Authentication tokens are not correct. Reproduce with: $command"
    if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
fi
echo

echo "Deployment manipulation tests finished. Errors so far = ${TOTAL_ERRORS}"
echo

echo "################################################################################"
echo "# Storage"
echo "################################################################################"

echo "## Testing creating a deployment with storage..."
command="lep photon run -n ${COMMON_NAME} -dn ${COMMON_NAME}-with-storage --mount /:/mnt/leptonstore"
if eval "$command" > /dev/null; then
    echo "Done"
else
    echo "lep photon run failed. This should not happen. Reproduce with: $command"
    if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
fi
echo

echo "## Waiting for the deployment to be up..."
command="lep deployment list | grep ${COMMON_NAME}-with-storage | grep Ready"
RETRY=0
while ! eval "$command" > /dev/null; do
    echo "Deployment is not up yet. Sleep for 5 seconds."
    RETRY=$((RETRY+1))
    if [ $RETRY -ge 100 ]; then
        echo "Too many retries and the deployment is still not up."
        echo "I am going to give up."
        if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
        break
    fi
    sleep 5
done
# Sometimes, it takes a bit longer time to have the photon running in a stable
# fashion... before we actually look into it, sleep for 15 seconds to make sure
# things are working.
sleep 15
echo "Done"
echo

echo "## Testing if the deployment contains the correct storage..."
command="${CURL} -f -s -X 'POST' ${LEPTON_WS_URL}/run \
              -H 'Content-Type: application/json' \
              -H 'accept: application/json' \
              -H 'X-Lepton-Deployment: ${COMMON_NAME}-with-storage' \
              -H 'Authorization: Bearer ${LEPTON_WS_TOKEN}' \
              -d '{\"query\": \"touch /mnt/leptonstore/${COMMON_NAME}.txt\"}'"
echo "Creating ${COMMON_NAME}.txt..."
if eval "$command" > /dev/null; then
    echo "Create file done"
else
    echo "Create file failed. This should not happen. Reproduce with: $command"
    if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
fi
echo "Checking file..."
sleep 15 # wait for consistency
command="${CURL} -f -s -X 'POST' ${LEPTON_WS_URL}/run \
              -H 'Content-Type: application/json' \
              -H 'accept: application/json' \
              -H 'X-Lepton-Deployment: ${COMMON_NAME}-with-storage' \
              -H 'Authorization: Bearer ${LEPTON_WS_TOKEN}' \
              -d '{\"query\": \"ls /mnt/leptonstore/${COMMON_NAME}.txt\"}'"
if eval "$command" | grep "${COMMON_NAME}.txt" > /dev/null; then
    echo "File exists."
else
    echo "File does not exist. This should not happen. Reproduce with: $command"
    if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
fi

command="${CURL} -f -s -X 'POST' ${LEPTON_WS_URL}/run \
              -H 'Content-Type: application/json' \
              -H 'accept: application/json' \
              -H 'X-Lepton-Deployment: ${COMMON_NAME}-with-storage' \
              -H 'Authorization: Bearer ${LEPTON_WS_TOKEN}' \
              -d '{\"query\": \"rm /mnt/leptonstore/${COMMON_NAME}.txt\"}'"
if eval "$command" > /dev/null; then
    echo "Delete file done"
else
    echo "Delete file failed. This should not happen. Reproduce with: $command"
    if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
fi
echo "Done"
echo

echo "## Testing deleting deployment with storage..."
command="lep dep remove -n ${COMMON_NAME}-with-storage"
if eval "$command"; then
    echo "Done"
else
    echo "lep dep remove failed. This should not happen. Reproduce with: $command"
    if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
fi
echo

echo "Storage tests finished. Errors so far = ${TOTAL_ERRORS}"
echo

echo "################################################################################"
echo "# Metrics"
echo "################################################################################"

echo "## Calling the deployment for 2 minutes to generate metrics..."
command="${CURL} -f -s -X 'POST' ${LEPTON_WS_URL}/run \
              -H 'Content-Type: application/json' \
              -H 'accept: application/json' \
              -H 'X-Lepton-Deployment: ${COMMON_NAME}' \
              -H 'Authorization: Bearer ${LEPTON_WS_TOKEN}' \
              -d '{\"query\": \"sleep 1\"}'"
END_TIME=$((SECONDS+120))
CALL_COUNT=0
while [ $SECONDS -lt $END_TIME ]; do
    eval "$command" > /dev/null
    # print a dot for each call but not newline
    echo -n "."
    CALL_COUNT=$((CALL_COUNT+1))
done
echo "2 mins calling done. Total calls: $CALL_COUNT"
echo

echo "## Testing getting qps..."
command="lep deployment qps -n ${COMMON_NAME} | grep \"QPS of ${COMMON_NAME}\""
if eval "$command" > /dev/null; then
    echo "Done"
else
    echo "lep deployment qps failed. This should not happen. Reproduce with: $command"
    if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
fi

echo "## Testing getting latency..."
command="lep deployment latency -n ${COMMON_NAME} | grep \"Latency (ms) of ${COMMON_NAME}\""
if eval "$command" > /dev/null; then
    echo "Done"
else
    echo "lep deployment latency failed. This should not happen. Reproduce with: $command"
    if ${PAUSE}; then read -n 1 -s -r -p "Press any key to continue..."; fi; TOTAL_ERRORS=$((TOTAL_ERRORS+1))
fi
echo "Note that the above work do not verify actual qps and latency values."
echo


echo "################################################################################"
echo "# Cleanups"
echo "################################################################################"
echo "If you encounter any error above, some of the cleanups may not succeed, but we will still run the whole cleanup script to make sure everything is cleaned up."
echo

echo "## Testing deleting deployments"
command="lep dep remove -n ${COMMON_NAME}"
if eval "$command"; then
    echo "${COMMON_NAME} Done"
else
    echo "Failed. This should not happen. Reproduce with: $command"
fi
echo

echo "## Testing deleting remote photons..."
command="lep photon remove -n ${COMMON_NAME} --all"
if eval "$command"; then
    echo "Done"
else
    echo "lep photon remove failed. This should not happen. Reproduce with: $command"
fi
echo

echo "## Testing deleting all local photons..."
command="lep photon remove -n ${COMMON_NAME} --local --all"
if eval "$command"; then
    echo "Done"
else
    echo "lep photon remove failed. This should not happen. Reproduce with: $command"
fi
echo

echo "All tests finished. Errors so far = ${TOTAL_ERRORS}"
echo

exit $TOTAL_ERRORS
