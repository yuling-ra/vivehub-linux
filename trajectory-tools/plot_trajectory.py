#!/usr/bin/env python3
import csv
import sys

import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.collections import LineCollection
import numpy as np


def load_samples(path):
    with open(path, newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) < 2:
        raise ValueError("CSV needs at least two pose samples")

    timestamp = np.array([int(row["timestamp_ns"]) for row in rows], dtype=np.int64)
    position = np.array(
        [[float(row[axis]) for axis in ("x_m", "y_m", "z_m")] for row in rows]
    )
    serial = rows[0]["serial"]
    return timestamp, position, serial


def colored_path(axis, first, second, time_s, x_label, y_label):
    points = np.column_stack((first, second)).reshape(-1, 1, 2)
    segments = np.concatenate((points[:-1], points[1:]), axis=1)
    collection = LineCollection(segments, cmap="viridis", norm=plt.Normalize(time_s[0], time_s[-1]))
    collection.set_array(time_s[:-1])
    collection.set_linewidth(1.8)
    axis.add_collection(collection)
    axis.scatter(first[0], second[0], color="#157f3d", s=42, zorder=3, label="Start")
    axis.scatter(first[-1], second[-1], color="#c73e1d", s=42, zorder=3, label="End")
    axis.autoscale()
    axis.set_xlabel(x_label)
    axis.set_ylabel(y_label)
    axis.set_aspect("equal", adjustable="box")
    axis.grid(alpha=0.25)
    return collection


def main():
    source = sys.argv[1] if len(sys.argv) > 1 else "trajectory.csv"
    output = sys.argv[2] if len(sys.argv) > 2 else "trajectory.png"
    timestamp, position, serial = load_samples(source)

    time_s = (timestamp - timestamp[0]) / 1_000_000_000
    distance = np.linalg.norm(np.diff(position, axis=0), axis=1)
    cmap = cm.viridis

    figure = plt.figure(figsize=(14, 9), constrained_layout=True)
    grid = figure.add_gridspec(2, 2, height_ratios=(1.15, 0.85))
    axis_3d = figure.add_subplot(grid[0, 0], projection="3d")
    axis_xy = figure.add_subplot(grid[0, 1])
    axis_xz = figure.add_subplot(grid[1, 0])
    axis_speed = figure.add_subplot(grid[1, 1])

    axis_3d.plot(position[:, 0], position[:, 1], position[:, 2], color="#3a6ea5", linewidth=1.2)
    axis_3d.scatter(*position[0], color="#157f3d", s=36, label="Start")
    axis_3d.scatter(*position[-1], color="#c73e1d", s=36, label="End")
    axis_3d.set_xlabel("X (m)")
    axis_3d.set_ylabel("Y (m)")
    axis_3d.set_zlabel("Z (m)")
    axis_3d.set_title("3D Trajectory")
    axis_3d.legend(loc="upper left")

    collection = colored_path(axis_xy, position[:, 0], position[:, 1], time_s, "X (m)", "Y (m)")
    axis_xy.set_title("Top View (X-Y)")
    axis_xy.legend(loc="best")
    colorbar = figure.colorbar(collection, ax=axis_xy, pad=0.02)
    colorbar.set_label("Time (s)")

    colored_path(axis_xz, position[:, 0], position[:, 2], time_s, "X (m)", "Z (m)")
    axis_xz.set_title("Side View (X-Z)")

    axis_speed.plot(np.arange(1, len(position)), distance * 1000, color="#d17a22", linewidth=1.0)
    axis_speed.set_title("Frame-to-Frame Displacement")
    axis_speed.set_xlabel("Sample index")
    axis_speed.set_ylabel("Displacement (mm)")
    axis_speed.grid(alpha=0.25)

    displacement = np.linalg.norm(position[-1] - position[0])
    path_length = distance.sum()
    figure.suptitle(
        "VIVE Ultimate Tracker Trajectory | {} | {:.2f} s | {:.2f} m path | {:.2f} m displacement".format(
            serial, time_s[-1], path_length, displacement
        ),
        fontsize=14,
    )
    figure.savefig(output, dpi=180)
    print("Wrote {}".format(output))


if __name__ == "__main__":
    main()
