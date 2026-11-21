# NOC Monitor v1.0.2

NOC Monitor là phần mềm giám sát tập trung viết bằng Python. NOC Server chạy dashboard/API trên cổng 6969, thu thập dữ liệu bằng Agent, SNMP, ICMP, TCP và HTTP.

## 1. Mô hình triển khai

~~~text
Máy quản trị -> http://IP-NOC-SERVER:6969
NOC Server -> Dashboard/API, SQLite, Agent Push, SNMP/Ping/TCP/HTTP
Máy được giám sát -> NOC Agent -> NOC Server
~~~

Có hai thành phần cài riêng:

- NOC Server: chạy dashboard trên Windows hoặc Ubuntu.
- NOC Agent: cài trên từng máy Windows/Linux cần lấy CPU, RAM, disk, network và thông tin hệ điều hành.

Agent chỉ tạo kết nối đi tới NOC Server, không mở cổng inbound.

## 2. Chuẩn bị

NOC Server cần Windows Server/Windows 11 64-bit hoặc Ubuntu 22.04+, Git và Internet trong lúc cài packages.

- Windows Server: Python 3.13 x64 và Python Launcher py.exe.
- Ubuntu Server: Python 3.10+, python3-venv và quyền sudo.
- Agent Windows: Python 3.10+.
- Agent Ubuntu: Python 3.10+ và systemd.
- Agent phải kết nối được tới NOC Server bằng TCP 6969 hoặc cổng HTTPS.

## 3. Clone source

Mở PowerShell trên Windows hoặc Terminal trên Ubuntu:

~~~bash
git clone https://github.com/thanhhuyit3020/noc-monitor.git
cd noc-monitor
git status
~~~

Bạn phải thấy các thư mục LinuxSetup, WindowSetup, agent và noc.

## 4. Cài NOC Server trên Windows

Mở PowerShell bằng Administrator, đi tới thư mục source:

~~~powershell
cd E:\Codex\Monitor
~~~

Nếu clone ở vị trí khác, thay đường dẫn trên bằng đường dẫn thật.

Chạy bộ cài:

~~~powershell
powershell.exe -ExecutionPolicy Bypass -File .\WindowSetup\Server\setup.ps1
~~~

Bộ cài kiểm tra Python 3.13, tạo .venv, cài packages, hỏi tạo Global Admin, tạo Scheduled Task NOC Monitor và chạy server trên 127.0.0.1:6969. Global Admin là tài khoản đăng nhập dashboard, không phải tài khoản Windows.

Nếu Agent hoặc máy quản trị ở máy khác, chạy lại với LAN access:

~~~powershell
powershell.exe -ExecutionPolicy Bypass -File .\WindowSetup\Server\setup.ps1 -LanAccess
~~~

Mở firewall cho subnet nội bộ:

~~~powershell
New-NetFirewallRule -DisplayName "NOC Monitor LAN" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 6969 -RemoteAddress LocalSubnet -Profile Domain,Private
~~~

Lấy IP bằng ipconfig, sau đó mở http://IP-NOC-SERVER:6969/login.

Kiểm tra:

~~~powershell
Get-ScheduledTask -TaskName "NOC Monitor"
Start-ScheduledTask -TaskName "NOC Monitor"
Test-NetConnection 127.0.0.1 -Port 6969
Invoke-WebRequest http://127.0.0.1:6969/api/health
~~~

Log nằm tại data\noc-server.out.log và data\noc-server.err.log.

## 5. Cài NOC Server trên Ubuntu

Clone source:

~~~bash
git clone https://github.com/thanhhuyit3020/noc-monitor.git
cd noc-monitor
~~~

Chỉ cho localhost truy cập:

~~~bash
sudo bash ./LinuxSetup/Server/install_linux.sh
~~~

Cho Agent và máy quản trị trong LAN truy cập:

~~~bash
sudo bash ./LinuxSetup/Server/install_linux.sh --lan-access
~~~

Bộ cài cài ứng dụng vào /opt/noc-monitor, tạo service account nocmonitor, virtualenv, Global Admin và systemd service noc-monitor.

Kiểm tra:

~~~bash
hostname -I
sudo systemctl status noc-monitor --no-pager
sudo systemctl is-enabled noc-monitor
sudo ss -ltnp | grep ':6969'
curl http://127.0.0.1:6969/api/health
sudo journalctl -u noc-monitor -n 100 --no-pager
~~~

Mở dashboard tại http://IP-NOC-SERVER:6969/login. Nếu UFW đang bật, chỉ cho subnet tin cậy:

~~~bash
sudo ufw allow from 192.168.1.0/24 to any port 6969 proto tcp
sudo ufw status
~~~

Thay 192.168.1.0/24 bằng subnet thật. Các file chính là /opt/noc-monitor, /opt/noc-monitor/data, /etc/noc-monitor.env và /etc/systemd/system/noc-monitor.service.

## 6. Tạo host Agent trên dashboard

1. Đăng nhập dashboard.
2. Vào Configuration hoặc Add host.
3. Chọn Remote agent và chế độ Push.
4. Đặt tên host, chọn sensor rồi lưu.
5. Sao chép Agent token.

Push URL khi Agent nằm trên máy khác:

~~~text
http://192.168.1.10:6969/api/agent/push
~~~

Không dùng 127.0.0.1 cho Agent từ xa.

## 7. Cài Agent trên Ubuntu/Linux

### Từ source

~~~bash
git clone https://github.com/thanhhuyit3020/noc-monitor.git
cd noc-monitor
sudo bash ./LinuxSetup/Agent/install_linux.sh
~~~

### Từ ZIP Agent

Tải noc-monitor-agent-1.0.2.zip từ GitHub Releases, giải nén rồi chạy:

~~~bash
sudo bash ./install_linux.sh \
  --push-url http://192.168.1.10:6969/api/agent/push \
  --token YOUR_AGENT_TOKEN \
  --interval 15
~~~

Agent được cài vào /opt/noc-agent và chạy bằng service noc-agent.

~~~bash
sudo systemctl status noc-agent --no-pager
sudo systemctl is-enabled noc-agent
sudo journalctl -u noc-agent -n 100 --no-pager
~~~

## 8. Cài Agent trên Windows

1. Tải noc-monitor-agent-1.0.2.zip từ GitHub Releases.
2. Giải nén, ví dụ vào C:\NOC-Agent.
3. Cài Python 3.10+ cho all users.
4. Mở PowerShell Administrator và chạy:

~~~powershell
cd C:\NOC-Agent
powershell.exe -ExecutionPolicy Bypass -File .\install_windows.ps1
~~~

Nhập Push URL và Agent token. Installer tạo C:\ProgramData\NOC-Agent, virtualenv, gửi snapshot kiểm tra và tạo Scheduled Task NOC Monitor Agent.

~~~powershell
Get-ScheduledTask -TaskName "NOC Monitor Agent"
Start-ScheduledTask -TaskName "NOC Monitor Agent"
Test-NetConnection 192.168.1.10 -Port 6969
~~~

## 9. Giám sát không cần Agent

- Ping/ICMP: online/offline, latency, jitter, packet loss.
- TCP: kiểm tra port dịch vụ.
- HTTP/HTTPS: status code, nội dung phản hồi, TLS.
- SNMP: CPU, RAM, storage, interface traffic và OID sensor.

Với CPU theo core, Windows Services, Event Log hoặc process, nên dùng Agent.

## 10. Database và cổng

- Database: SQLite.
- Windows: data\noc.db.
- Ubuntu Server: /opt/noc-monitor/data/noc.db.
- NOC Server: TCP 6969.
- Agent: không cần mở inbound port.

Không đưa cổng 6969 trực tiếp ra Internet. Dùng VPN hoặc HTTPS reverse proxy khi truy cập từ mạng không tin cậy.

## 11. Cập nhật

~~~bash
cd noc-monitor
git fetch --tags origin
git pull --ff-only origin main
~~~

Ubuntu:

~~~bash
sudo bash ./LinuxSetup/Server/install_linux.sh --lan-access
~~~

Windows PowerShell Administrator:

~~~powershell
powershell.exe -ExecutionPolicy Bypass -File .\WindowSetup\Server\setup.ps1 -LanAccess
~~~

Sao lưu data hoặc /opt/noc-monitor/data trước khi cập nhật production.

## 12. Lỗi thường gặp

Dashboard Ubuntu:

~~~bash
sudo systemctl status noc-monitor
sudo journalctl -u noc-monitor -n 100 --no-pager
sudo ss -ltnp | grep ':6969'
~~~

Dashboard Windows:

~~~powershell
Get-ScheduledTask -TaskName "NOC Monitor"
Get-Content .\data\noc-server.err.log -Tail 100
Test-NetConnection 127.0.0.1 -Port 6969
~~~

Nếu Agent DOWN, kiểm tra Push URL dùng IP NOC Server, firewall TCP 6969, token đúng host và LAN access đã bật.

Nếu Linux báo lỗi set: pipefail hoặc invalid option name, chuẩn hóa line ending:

~~~bash
sed -i 's/\r$//' LinuxSetup/Server/install_linux.sh LinuxSetup/Agent/install_linux.sh
~~~

## 13. Kiểm tra mã nguồn

~~~bash
python -m pytest tests/ -v
curl http://127.0.0.1:6969/api/health
~~~
