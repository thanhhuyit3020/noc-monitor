# NOC Monitor Agent

This is the optional remote-host package. It is separate from the NOC Server installer and can be installed on Windows or Linux. The agent uses Push: it makes outbound HTTPS/HTTP requests to the NOC server and does not open a listening port.

Download `noc-monitor-agent-<version>.zip` from the [GitHub Releases](https://github.com/thanhhuyit3020/noc-monitor/releases) page. On the NOC dashboard, add a **Remote agent** host in **Push** mode and copy its token. Use the NOC server's LAN address in the push URL; `127.0.0.1` only works when the agent runs on the NOC server itself.

The NOC Server must be configured to accept LAN connections before a remote agent can report. The default server setup binds to localhost. Install the NOC Server with `-LanAccess`, then allow TCP 6969 from the trusted LAN in Windows Firewall. Use HTTPS when traffic crosses an untrusted network.

## Ubuntu

Ubuntu 22.04 or newer provides Python 3.10+. From the extracted agent package:

```bash
sudo apt update
sudo apt install -y python3 python3-venv
python3 -c 'import sys; assert sys.version_info >= (3, 10), "Python 3.10+ required"'
sudo useradd --system --home-dir /opt/noc-agent --create-home --shell /usr/sbin/nologin nocagent
sudo install -o root -g root -m 0644 run_agent.py /opt/noc-agent/run_agent.py
sudo python3 -m venv /opt/noc-agent/.venv
sudo /opt/noc-agent/.venv/bin/pip install -r requirements.txt
sudo install -o root -g root -m 0600 /dev/null /etc/noc-agent.env
sudoedit /etc/noc-agent.env
```

Put these values in `/etc/noc-agent.env`:

```ini
NOC_PUSH_URL=https://noc.example.com/api/agent/push
NOC_AGENT_TOKEN=PASTE_HOST_TOKEN_HERE
NOC_AGENT_INTERVAL_SEC=15
```

Install and start the included systemd unit:

```bash
sudo install -o root -g root -m 0644 noc-agent.service /etc/systemd/system/noc-agent.service
sudo systemctl daemon-reload
sudo systemctl enable --now noc-agent
sudo systemctl status noc-agent
sudo journalctl -u noc-agent -f
```

## Windows

Install Python 3.10+ for all users, extract this package, then open PowerShell as Administrator in the extracted folder. Run:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\install_windows.ps1
```

The installer prompts for the NOC push URL and host token, creates an isolated virtual environment, sends a test sample, and registers a startup task named **NOC Monitor Agent**. Its token file is readable only by SYSTEM and local Administrators. Check the host status on the NOC dashboard and Task Scheduler if it does not report.

Push mode needs outbound access from the monitored host to the NOC server on TCP 6969 (or the configured HTTPS port). Do not open inbound TCP 9108 on the agent host; that port is only used for the optional Pull mode.
