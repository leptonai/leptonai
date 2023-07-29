#!/bin/bash

set -e

usage() {
    echo "Usage: $0 -r [remote] -d [data] -t [token] -u [users] -p [period]"
    echo "  -r remote: remote address to send requests to"
    echo "  -d data: data to send in the request"
    echo "  -t token: token to use for authentication"
    echo "  -u users: number of users to simulate"
    echo "  -p period: period of time to run the benchmark for"
    echo "  -h|--help: print this message"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            ;;
        -r)
            remote="$2"
            shift
            shift
            ;;
        -d)
            data="$2"
            shift
            shift
            ;;
        -t)
            token="$2"
            shift
            shift
            ;;
        -u)
            users="$2"
            shift
            shift
            ;;
        -p)
            period="$2"
            shift
            shift
            ;;
        *)
            echo "Unknown option '$1'"
            usage
    esac
done

if [[ -z "${remote}" ]]; then
    echo "-r remote is required"
    usage
fi

if [[ -z "${data}" ]]; then
    echo "-d data is required"
    usage
fi

if [[ -z "${token}" ]]; then
    echo "-t token is required"
    usage
fi

if [[ -z "${users}" ]]; then
    users=10
fi

if [[ -z "${period}" ]]; then
    period=1m
fi

if ! hash locust 2>/dev/null; then
    echo "locust is not installed. Installing it with 'pip install locust'"
    pip install locust
fi

client_py=$(mktemp --suffix .py)

cat >"${client_py}" <<EOF
from locust import FastHttpUser, task


class BenchUser(FastHttpUser):
    def _send_request(self):
        self.client.post(
            "", headers={"Authorization": "Bearer " + "${token}"}, json=${data}
        )

    def on_start(self):
        self._send_request()

    @task
    def bench(self):
        self._send_request()
EOF

locust -f "${client_py}" --headless --users "${users}" --spawn-rate "${users}" -H "${remote}" -t "${period}"
