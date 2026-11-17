# NOC Monitor Agent

This is the optional remote-host package. It is separate from the NOC Server installer and can be installed on Windows or Linux. The agent uses Push: it makes outbound HTTPS/HTTP requests to the NOC server and does not open a listening port.

Download `noc-monitor-agent-<version>.zip` from the [GitHub Releases](https://github.com/thanhhuyit3020/noc-monitor/releases) page. On the NOC dashboard, add a **Remote agent** host in **Push** mode and copy its token. Use the NOC server's LAN address in the push URL; `127.0.0.1` only works when the agent runs on the NOC server itself.

The NOC Server must be configured to accept LAN connections before a remote agent can report. The default server setup binds to localhost. Install the NOC Server with `-LanAccess` on Windows or `--lan-access` on Ubuntu, then allow TCP 6969 from the trusted LAN in Windows Firewall or UFW. Use HTTPS when traffic crosses an untrusted network.

## Ubuntu

Ubuntu 22.04 or newer provides Python 3.10+. From a source checkout, run:

```bash
sudo bash ./LinuxSetup/Agent/install_linux.sh
```

From the extracted standalone agent ZIP, run `sudo bash ./install_linux.sh` because the package is flattened for distribution. The installer asks for the NOC push URL and host token, installs the agent into `/opt/noc-agent`, sends one test snapshot, and enables the `noc-agent` systemd service. For unattended installation from either layout:

```bash
sudo bash ./install_linux.sh \
  --push-url https://noc.example.com/api/agent/push \
  --token PASTE_HOST_TOKEN_HERE \
  --interval 15
```

The installer writes the protected token file `/etc/noc-agent.env` and installs the included systemd unit:

```bash
sudo systemctl status noc-agent
sudo journalctl -u noc-agent -f
```

## Windows

Install Python 3.10+ for all users. From a source checkout, open PowerShell as Administrator at the repository root and run:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\WindowSetup\Agent\install_windows.ps1
```

From the extracted standalone agent ZIP, run `powershell.exe -ExecutionPolicy Bypass -File .\install_windows.ps1` in the extracted folder.

The installer prompts for the NOC push URL and host token, creates an isolated virtual environment, sends a test sample, and registers a startup task named **NOC Monitor Agent**. Its token file is readable only by SYSTEM and local Administrators. Check the host status on the NOC dashboard and Task Scheduler if it does not report.

Push mode needs outbound access from the monitored host to the NOC server on TCP 6969 (or the configured HTTPS port). Do not open inbound TCP 9108 on the agent host; that port is only used for the optional Pull mode.
