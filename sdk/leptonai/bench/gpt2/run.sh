#!/bin/bash

set -e

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 [port]"
    exit 1
fi

host="localhost"
port=$1

echo "host=${host} port=${port}"

server_log="./server.log"

echo "starting server..."
lep photon run -n gpt2 -m hf:gpt2 -p "${port}" >"${server_log}" 2>&1 &
server_pid=$!
echo "server pid: ${server_pid}"

function cleanup {
  echo "shutting down server"
  kill ${server_pid}
}
trap cleanup EXIT

echo "waiting for server becoming ready ..."
tail -f ${server_log} | while read -r LOGLINE
do
    if [[ "${LOGLINE}" == *"running"* ]]; then
	echo "server is now ready"
	pkill -P $$ tail
    fi
    if [[ "${LOGLINE}" == *"ERROR"* ]]; then
	echo "failed to launch server: ${LOGLINE}" && exit 1
    fi
done

echo "start sending requests"
locust -f client.py --headless --users 10 --spawn-rate 1 -H "http://${host}:${port}" -t 1m
echo "done"

echo "server log:"
cat ${server_log}
echo "finished"
