# VIVE Trajectory Tools

These tools connect to the VIVE Hub `tracker_server`, capture VIVE Ultimate
Tracker poses, resample a recording to a fixed output rate, and render it as a
PNG trajectory plot.

The VIVE Hub release binary is deliberately not in this repository. Download
and unpack a VIVE Hub release separately, then point `VIVEHUB_DIR` at that
directory when it is not located beside this repository.

Install the plotting dependencies when they are not already available:

```sh
python3 -m pip install -r requirements.txt
```

```text
VIVE Ultimate Tracker -> VIVE Hub -> VUT SDK -> raw CSV -> fixed-rate CSV -> PNG
```

## Setup

Install the tracker USB permission rule once from the unpacked VIVE Hub:

```sh
cd /path/to/VIVEHub-Linux
sudo ./install-udev.sh
```

Reconnect the dongle afterwards. Build the recorder with an explicit Hub path:

```sh
cd trajectory-tools
make VIVEHUB_DIR=/path/to/VIVEHub-Linux
```

## Workflow

Run VIVE Hub, pair the Tracker, complete map setup, and wait for the tracker
status to be `Ready`. Then, from this directory:

```sh
export VIVEHUB_DIR=/path/to/VIVEHub-Linux
./vive.sh doctor
./vive.sh capture session_01 60 200
```

`capture` writes these files under `data/`:

- `session_01_raw.csv`: original Tracker pose stream, approximately 120 Hz.
- `session_01_200hz_interpolated.csv`: regular 200 Hz interpolation.
- `session_01_200hz.png`: 3D, top, side, and frame-displacement plots.

The Tracker does not provide native 200 Hz poses. The 200 Hz output contains
linear position interpolation and quaternion SLERP interpolation; preserve the
raw CSV when you need original measurements.

## Commands

```sh
./vive.sh start
./vive.sh doctor
./vive.sh test
./vive.sh record raw.csv 60
./vive.sh resample raw.csv output_200hz.csv 200
./vive.sh visualize output_200hz.csv output.png
./test_pipeline.sh
```

`test` runs HTC's SDK demo for about 10 seconds and requires the Hub to be
running. `test_pipeline.sh` is offline and uses synthetic input, so it can run
without the tracker or VIVE Hub installed.
