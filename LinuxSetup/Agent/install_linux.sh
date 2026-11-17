#!/usr/bin/env bash
set -Eeuo pipefail

INSTALL_DIR="/opt/noc-agent"
SERVICE_USER="nocagent"
PUSH_URL="${NOC_PUSH_URL:-}"
TOKEN="${NOC_AGENT_TOKEN:-}"
INTERVAL="${NOC_AGENT_INTERVAL_SEC:-15}"
ORIGINAL_ARGS=("$@")

usage() {
    cat <<'EOF'
Usage: sudo bash install_linux.sh [options]

Options:
  --push-url URL   NOC endpoint ending in /api/agent/push
  --token TOKEN    Agent token copied from the NOC host
  --interval SEC   Push interval, minimum 5 seconds (default: 15)
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --push-url) [[ $# -ge 2 ]] || { echo "--push-url needs a value." >&2; exit 2; }; PUSH_URL="$2"; shift ;;
        --token) [[ $# -ge 2 ]] || { echo "--token needs a value." >&2; exit 2; }; TOKEN="$2"; shift ;;
        --interval) [[ $# -ge 2 ]] || { echo "--interval needs a value." >&2; exit 2; }; INTERVAL="$2"; shift ;;
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
    echo "systemd is required to run the NOC agent as a service." >&2
    exit 1
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
AGENT_SOURCE_DIR="$SCRIPT_DIR"
if [[ ! -f "$AGENT_SOURCE_DIR/run_agent.py" ]]; then
    AGENT_SOURCE_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd -P)/agent"
fi
if [[ ! -f "$AGENT_SOURCE_DIR/run_agent.py" || ! -f "$AGENT_SOURCE_DIR/requirements.txt" ]]; then
    echo "Agent source files were not found." >&2
    exit 1
fi
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-pip python3-venv ca-certificates

if [[ -z "$PUSH_URL" ]]; then
    read -r -p "NOC agent push URL: " PUSH_URL
fi
PUSH_URL="${PUSH_URL%/}"
case "$PUSH_URL" in
    http://*/api/agent/push|https://*/api/agent/push) ;;
    *) echo "Push URL must end in /api/agent/push and use http or https." >&2; exit 1 ;;
esac

if [[ -z "$TOKEN" ]]; then
    read -r -s -p "Agent token: " TOKEN
    printf '\n'
fi
if [[ -z "$TOKEN" || "$TOKEN" == *$'\n'* || "$TOKEN" == *$'\r'* || "$TOKEN" == *[[:space:]]* ]]; then
    echo "Agent token cannot be empty or contain whitespace." >&2
    exit 1
fi
if ! [[ "$INTERVAL" =~ ^[0-9]+$ ]] || (( INTERVAL < 5 )); then
    echo "Interval must be an integer of at least 5 seconds." >&2
    exit 1
fi

if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
    echo "Python 3.10 or newer is required." >&2
    exit 1
fi
if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
    useradd --system --home-dir "$INSTALL_DIR" --create-home --shell /usr/sbin/nologin "$SERVICE_USER"
fi

install -d -o root -g root -m 0755 "$INSTALL_DIR"
install -o root -g root -m 0755 "$AGENT_SOURCE_DIR/run_agent.py" "$INSTALL_DIR/run_agent.py"
install -o root -g root -m 0644 "$AGENT_SOURCE_DIR/requirements.txt" "$INSTALL_DIR/requirements.txt"
if [[ ! -x "$INSTALL_DIR/.venv/bin/python" ]]; then
    python3 -m venv "$INSTALL_DIR/.venv"
fi
PYTHON="$INSTALL_DIR/.venv/bin/python"
"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -r "$INSTALL_DIR/requirements.txt"

umask 077
cat > /etc/noc-agent.env <<EOF
NOC_PUSH_URL=$PUSH_URL
NOC_AGENT_TOKEN=$TOKEN
NOC_AGENT_INTERVAL_SEC=$INTERVAL
EOF
chown root:"$SERVICE_USER" /etc/noc-agent.env
chmod 0640 /etc/noc-agent.env

echo "Sending one test snapshot before enabling the service."
runuser -u "$SERVICE_USER" -- env NOC_PUSH_URL="$PUSH_URL" NOC_AGENT_TOKEN="$TOKEN" NOC_AGENT_INTERVAL_SEC="$INTERVAL" "$PYTHON" "$INSTALL_DIR/run_agent.py" --once

if [[ ! -f "$SCRIPT_DIR/noc-agent.service" ]]; then
    echo "Missing $SCRIPT_DIR/noc-agent.service." >&2
    exit 1
fi
install -o root -g root -m 0644 "$SCRIPT_DIR/noc-agent.service" /etc/systemd/system/noc-agent.service
systemctl daemon-reload
systemctl enable --now noc-agent.service

echo "NOC Agent is running as systemd service noc-agent."
echo "Logs: sudo journalctl -u noc-agent -f"
