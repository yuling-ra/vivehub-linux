#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

python3 - "$TMP_DIR/raw.csv" <<'PY'
import csv
import sys

fields = [
    "timestamp_ns", "device_id", "serial", "state", "x_m", "y_m", "z_m",
    "qx", "qy", "qz", "qw", "vx_mps", "vy_mps", "vz_mps", "wx_radps",
    "wy_radps", "wz_radps", "flags",
]
rows = [
    [0, 1, "TEST", 2, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
    [10_000_000, 1, "TEST", 2, 1, 0, 0, 0, 0, 0.70710678, 0.70710678, 0, 0, 0, 0, 0, 0, 0],
    [20_000_000, 1, "TEST", 2, 2, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0],
]
with open(sys.argv[1], "w", newline="") as handle:
    writer = csv.writer(handle)
    writer.writerow(fields)
    writer.writerows(rows)
PY

python3 "$ROOT/resample_trajectory.py" "$TMP_DIR/raw.csv" "$TMP_DIR/resampled.csv" 200
python3 "$ROOT/plot_trajectory.py" "$TMP_DIR/resampled.csv" "$TMP_DIR/trajectory.png"

python3 - "$TMP_DIR/resampled.csv" <<'PY'
import csv
import sys

with open(sys.argv[1], newline="") as handle:
    timestamps = [int(row["timestamp_ns"]) for row in csv.DictReader(handle)]

assert len(timestamps) == 5, "unexpected sample count"
assert all(b - a == 5_000_000 for a, b in zip(timestamps, timestamps[1:])), "output is not 200 Hz"
print("Pipeline test passed: {} samples at 200 Hz".format(len(timestamps)))
PY

[[ -s "$TMP_DIR/trajectory.png" ]]
