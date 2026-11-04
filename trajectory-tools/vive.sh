#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HUB_DIR="${VIVEHUB_DIR:-$ROOT/../../VIVEHub-Linux}"
DATA_DIR="$ROOT/data"
CAPTURE="$ROOT/vut_capture"

usage() {
    cat <<'EOF'
Usage:
  ./vive.sh start
  ./vive.sh doctor
  ./vive.sh test
  ./vive.sh record OUTPUT.csv SECONDS
  ./vive.sh resample INPUT.csv OUTPUT.csv [HZ]
  ./vive.sh visualize INPUT.csv [OUTPUT.png]
  ./vive.sh capture NAME SECONDS [HZ]

Commands:
  start      Open the VIVE Hub desktop application.
  doctor     Check the dongle, udev rule, VIVE Hub socket, and recorder build.
  test       Read tracker poses for about 10 seconds through HTC's SDK demo.
  record     Save raw valid poses while VIVE Hub is running and the tracker is Ready.
  resample   Create uniformly spaced interpolated trajectory data (default 200 Hz).
  visualize  Render 3D, top, side, and frame displacement plots to PNG.
  capture    Record raw data, resample it, and render its PNG in data/.
EOF
}

require_hub() {
    if [[ ! -x "$HUB_DIR/run-vivehub.sh" ]]; then
        echo "VIVE Hub not found: $HUB_DIR" >&2
        exit 1
    fi
}

build_capture() {
    make -C "$ROOT" >/dev/null
}

case "${1:-}" in
    start)
        require_hub
        exec "$HUB_DIR/run-vivehub.sh"
        ;;
    doctor)
        require_hub
        echo "VIVE Hub: $HUB_DIR"
        if lsusb -d 0bb4:0350 >/dev/null 2>&1; then
            echo "Dongle: detected"
        else
            echo "Dongle: not detected" >&2
        fi
        if [[ -f /etc/udev/rules.d/70-vive-tracker.rules ]]; then
            echo "udev rule: installed"
        else
            echo "udev rule: missing (run sudo $HUB_DIR/install-udev.sh)" >&2
        fi
        if [[ -S /tmp/vut.sock ]]; then
            echo "VUT socket: available"
        else
            echo "VUT socket: unavailable (start VIVE Hub first)" >&2
        fi
        build_capture
        echo "Recorder: built"
        ;;
    test)
        require_hub
        make -C "$HUB_DIR/sdk/examples"
        exec "$HUB_DIR/sdk/examples/vut_demo"
        ;;
    record)
        [[ $# -eq 3 ]] || { usage; exit 2; }
        build_capture
        exec "$CAPTURE" "$2" "$3"
        ;;
    resample)
        [[ $# -ge 3 && $# -le 4 ]] || { usage; exit 2; }
        python3 "$ROOT/resample_trajectory.py" "$2" "$3" "${4:-200}"
        ;;
    visualize)
        [[ $# -ge 2 && $# -le 3 ]] || { usage; exit 2; }
        python3 "$ROOT/plot_trajectory.py" "$2" "${3:-${2%.csv}.png}"
        ;;
    capture)
        [[ $# -ge 3 && $# -le 4 ]] || { usage; exit 2; }
        mkdir -p "$DATA_DIR"
        name="$2"
        seconds="$3"
        rate="${4:-200}"
        raw="$DATA_DIR/${name}_raw.csv"
        resampled="$DATA_DIR/${name}_${rate}hz_interpolated.csv"
        image="$DATA_DIR/${name}_${rate}hz.png"
        build_capture
        "$CAPTURE" "$raw" "$seconds"
        python3 "$ROOT/resample_trajectory.py" "$raw" "$resampled" "$rate"
        python3 "$ROOT/plot_trajectory.py" "$resampled" "$image"
        echo "Raw: $raw"
        echo "Resampled: $resampled"
        echo "Plot: $image"
        ;;
    *)
        usage
        exit 2
        ;;
esac
