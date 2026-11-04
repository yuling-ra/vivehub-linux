#!/usr/bin/env python3
"""Resample a VUT capture to a uniform output rate.

VUT pose callbacks can arrive in short batches, so their per-event timestamps
are not evenly spaced. This tool keeps the capture's total duration and treats
the raw samples as uniformly spaced observations before interpolation.
"""

import csv
import sys

import numpy as np


VECTOR_COLUMNS = (
    "x_m", "y_m", "z_m", "vx_mps", "vy_mps", "vz_mps",
    "wx_radps", "wy_radps", "wz_radps",
)


def slerp(q0, q1, fraction):
    dot = float(np.clip(np.dot(q0, q1), -1.0, 1.0))
    if dot < 0.0:
        q1 = -q1
        dot = -dot
    if dot > 0.9995:
        result = q0 + fraction * (q1 - q0)
        return result / np.linalg.norm(result)
    theta = np.arccos(dot)
    sin_theta = np.sin(theta)
    return (
        np.sin((1.0 - fraction) * theta) / sin_theta * q0
        + np.sin(fraction * theta) / sin_theta * q1
    )


def main():
    if len(sys.argv) != 4:
        print("Usage: resample_trajectory.py INPUT.csv OUTPUT.csv HZ", file=sys.stderr)
        return 2

    source, destination, rate_text = sys.argv[1:]
    try:
        rate_hz = float(rate_text)
    except ValueError:
        print("HZ must be a positive number", file=sys.stderr)
        return 2
    if rate_hz <= 0:
        print("HZ must be a positive number", file=sys.stderr)
        return 2

    with open(source, newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = handle.seek(0) or next(csv.reader(handle))
    if len(rows) < 2:
        print("Input needs at least two samples", file=sys.stderr)
        return 1

    raw_timestamp = np.array([int(row["timestamp_ns"]) for row in rows], dtype=np.int64)
    duration_s = (raw_timestamp[-1] - raw_timestamp[0]) / 1_000_000_000
    if duration_s <= 0:
        print("Input timestamps do not span a positive duration", file=sys.stderr)
        return 1

    raw_t = np.linspace(0.0, duration_s, num=len(rows))
    count = int(np.floor(duration_s * rate_hz)) + 1
    output_t = np.arange(count) / rate_hz
    output_t[-1] = min(output_t[-1], duration_s)

    values = {column: np.array([float(row[column]) for row in rows]) for column in VECTOR_COLUMNS}
    quaternions = np.array(
        [[float(row[column]) for column in ("qx", "qy", "qz", "qw")] for row in rows]
    )
    quaternions /= np.linalg.norm(quaternions, axis=1)[:, None]

    with open(destination, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for target_t in output_t:
            right = min(np.searchsorted(raw_t, target_t, side="right"), len(rows) - 1)
            left = max(right - 1, 0)
            span = raw_t[right] - raw_t[left]
            fraction = 0.0 if span == 0 else (target_t - raw_t[left]) / span
            quaternion = slerp(quaternions[left], quaternions[right], fraction)
            nearest = rows[left if fraction < 0.5 else right].copy()
            nearest["timestamp_ns"] = str(raw_timestamp[0] + round(target_t * 1_000_000_000))
            for column, samples in values.items():
                nearest[column] = "{:.9g}".format(np.interp(target_t, raw_t, samples))
            for column, value in zip(("qx", "qy", "qz", "qw"), quaternion):
                nearest[column] = "{:.9g}".format(value)
            writer.writerow(nearest)

    print("Wrote {} interpolated samples at {} Hz to {}".format(count, rate_hz, destination))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
