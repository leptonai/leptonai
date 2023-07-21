#!/usr/bin/env bash
set -xue

if ! [[ "$0" =~ scripts/build.release.sh ]]; then
    echo "must be run from repository root"
    exit 255
fi

# "--bin" can be specified multiple times for each directory in "bin/*" or workspaces
cargo build \
--release \
--bin machine-rs

./target/release/machine-rs --help
./target/release/machine-rs aws default-spec --help
./target/release/machine-rs aws apply --help
./target/release/machine-rs aws delete --help
