#!/usr/bin/env bash
set -Eeuo pipefail

INSTALL_DIR="/opt/noc-monitor"
SERVICE_USER="nocmonitor"
LAN_ACCESS=0
ORIGINAL_ARGS=("$@")

usage() {
    cat <<'EOF'
Usage: sudo bash install_linux.sh [--lan-access]

Installs NOC Monitor into /opt/noc-monitor and registers the noc-monitor
systemd service on Ubuntu/Debian.
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --lan-access) LAN_ACCESS=1 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
    shift
done

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
    exec sudo -E bash "$0" "${ORIGINAL_ARGS[@]}"
fi

if ! command -v apt-get >/dev/null 2>&1; then
    echo "This installer requires Ubuntu/Debian with apt-get." >&2
    exit 1
fi
if ! command -v systemctl >/dev/null 2>&1; then
    echo "systemd is required to run NOC Monitor as a service." >&2
    exit 1
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
SOURCE_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd -P)"
if [[ ! -f "$SOURCE_ROOT/requirements.txt" ]]; then
    echo "Run this installer from a complete NOC Monitor source checkout." >&2
    exit 1
fi

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-pip python3-venv ca-certificates

if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
    echo "Python 3.10 or newer is required." >&2
    exit 1
fi

if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
    useradd --system --home-dir "$INSTALL_DIR" --create-home --shell /usr/sbin/nologin "$SERVICE_USER"
fi

mkdir -p "$INSTALL_DIR"
if [[ "$SOURCE_ROOT" != "$INSTALL_DIR" ]]; then
    tar \
        --exclude='./.git' \
        --exclude='./.venv' \
        --exclude='./data' \
        --exclude='./LinuxSetup' \
        --exclude='*.pyc' \
        --exclude='./__pycache__' \
        -C "$SOURCE_ROOT" -cf - . | tar -C "$INSTALL_DIR" -xf -
fi

if [[ ! -x "$INSTALL_DIR/.venv/bin/python" ]]; then
    python3 -m venv "$INSTALL_DIR/.venv"
fi
PYTHON="$INSTALL_DIR/.venv/bin/python"
"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -r "$INSTALL_DIR/requirements.txt"

install -d -o "$SERVICE_USER" -g "$SERVICE_USER" -m 0750 "$INSTALL_DIR/data"
chown -R "$SERVICE_USER":"$SERVICE_USER" "$INSTALL_DIR/data"
cat > /etc/noc-monitor.env <<EOF
NOC_HOST=$(if [[ $LAN_ACCESS -eq 1 ]]; then echo 0.0.0.0; else echo 127.0.0.1; fi)
NOC_PORT=6969
NOC_DATA_DIR=$INSTALL_DIR/data
EOF
chown root:"$SERVICE_USER" /etc/noc-monitor.env
chmod 0640 /etc/noc-monitor.env

if [[ ! -f "$SCRIPT_DIR/noc-monitor.service" ]]; then
    echo "Missing $SCRIPT_DIR/noc-monitor.service." >&2
    exit 1
fi
install -o root -g root -m 0644 "$SCRIPT_DIR/noc-monitor.service" /etc/systemd/system/noc-monitor.service

echo "Create or verify the Global Admin account."
runuser -u "$SERVICE_USER" -- env NOC_DATA_DIR="$INSTALL_DIR/data" "$PYTHON" -m noc.auth_cli bootstrap

systemctl daemon-reload
systemctl enable --now noc-monitor.service

for attempt in {1..30}; do
    if "$PYTHON" - <<'PY'
from urllib.request import urlopen

with urlopen("http://127.0.0.1:6969/api/health", timeout=2) as response:
    raise SystemExit(0 if response.status == 200 else 1)
PY
    then
        echo "NOC Monitor is running at http://127.0.0.1:6969/"
        if [[ $LAN_ACCESS -eq 1 ]]; then
            echo "LAN access is enabled on 0.0.0.0:6969. Restrict TCP 6969 with your firewall."
        fi
        echo "Logs: sudo journalctl -u noc-monitor -f"
        exit 0
    fi
    sleep 1
done

echo "NOC Monitor did not become healthy. Check: sudo journalctl -u noc-monitor -n 100 --no-pager" >&2
exit 1
