#!/usr/bin/env bash
set -xue

if ! [[ "$0" =~ scripts/tests.unused.sh ]]; then
    echo "must be run from repository root"
    exit 255
fi

# cargo install cargo-udeps --locked
# https://github.com/est31/cargo-udeps
cargo install cargo-udeps --locked
cargo +nightly udeps

echo "ALL SUCCESS!"
