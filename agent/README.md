# NOC Monitor Agent

Agent gửi CPU, RAM, disk, network và thông tin hệ điều hành về NOC Server bằng kết nối Push. Agent không mở cổng inbound.

## 1. Chuẩn bị trên NOC Server

1. Đăng nhập dashboard.
2. Chọn Add host hoặc Configuration.
3. Chọn Remote agent và chế độ Push.
4. Lưu host và sao chép Agent token.
5. Bật LAN access trên NOC Server.

Push URL:

~~~text
http://IP-NOC-SERVER:6969/api/agent/push
~~~

Dùng IP LAN của NOC Server. 127.0.0.1 chỉ đúng khi Agent chạy cùng máy.

## 2. Ubuntu/Linux

### Từ source

~~~bash
git clone https://github.com/thanhhuyit3020/noc-monitor.git
cd noc-monitor
sudo bash ./LinuxSetup/Agent/install_linux.sh
~~~

### Từ ZIP Agent

Tải ZIP từ GitHub Releases, giải nén rồi chạy:

~~~bash
sudo bash ./install_linux.sh \
  --push-url http://IP-NOC-SERVER:6969/api/agent/push \
  --token YOUR_AGENT_TOKEN \
  --interval 15
~~~

Agent được cài vào /opt/noc-agent.

Kiểm tra:

~~~bash
sudo systemctl status noc-agent --no-pager
sudo journalctl -u noc-agent -f
~~~

## 3. Windows

1. Cài Python 3.10+ cho all users.
2. Giải nén ZIP vào ví dụ C:\NOC-Agent.
3. Mở PowerShell Administrator.
4. Chạy:

~~~powershell
cd C:\NOC-Agent
powershell.exe -ExecutionPolicy Bypass -File .\install_windows.ps1
~~~

Nhập Push URL và token. Agent được cài vào C:\ProgramData\NOC-Agent và chạy bằng Scheduled Task NOC Monitor Agent.

Kiểm tra:

~~~powershell
Get-ScheduledTask -TaskName "NOC Monitor Agent"
Start-ScheduledTask -TaskName "NOC Monitor Agent"
Test-NetConnection IP-NOC-SERVER -Port 6969
~~~

Không mở inbound port trên máy Agent. Chỉ cần cho phép outbound tới NOC Server.
