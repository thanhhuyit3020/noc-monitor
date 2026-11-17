# NOC Monitor V1.0.2

> **Mô tả GitHub:** NOC Monitor V1.0.2: Nền tảng NOC giám sát máy chủ và thiết bị mạng qua Agent, SNMP, ICMP, TCP, HTTP; dashboard thời gian thực và cảnh báo đa kênh trên Windows Server hoặc Ubuntu.

NOC Monitor là phần mềm giám sát tập trung gọn nhẹ theo mô hình Zabbix/PRTG. Máy chủ NOC thu thập số liệu, lưu lịch sử trong SQLite và hiển thị trạng thái hệ thống trên dashboard web. Có thể giám sát máy chủ Windows/Linux và thiết bị mạng mà không cần cài agent, hoặc cài agent nhẹ để lấy thêm chỉ số chuyên sâu.

## Tính năng

- **Dashboard thời gian thực:** Wallboard, trạng thái host, lịch sử biểu đồ, chi tiết tài nguyên và giao diện tối ưu cho màn hình NOC.
- **Giám sát máy NOC:** CPU tổng/theo core, RAM, swap, dung lượng ổ đĩa, disk I/O và IOPS, trạng thái up/down và lưu lượng từng card mạng, TCP connections, tiến trình, Windows Services, Windows Event Log, uptime và reboot.
- **SNMP agentless:** SNMP v1/v2c bằng client BER Python tích hợp; SNMPv3 qua PySNMP. Hỗ trợ IF-MIB/HOST-RESOURCES-MIB và profile cho Windows, Linux, Cisco, MikroTik, Fortinet, Huawei, HPE Aruba.
- **Agent từ xa:** mã runtime trong `agent/`, bộ cài Windows trong `WindowSetup/Agent/` và bộ cài Linux trong `LinuxSetup/Agent/`; hỗ trợ Push và Pull, thu thập chỉ số hệ điều hành bằng token.
- **Active probes:** ICMP ping (latency, jitter, packet loss), TCP port, HTTP/HTTPS status và nội dung phản hồi, hạn chứng chỉ TLS.
- **Cảnh báo và sự cố:** Ngưỡng Warning/Critical, số lần vượt ngưỡng liên tiếp, incident theo từng tài nguyên, acknowledge, resolve và maintenance mode. Có thể tạo rule `net.if_up == 0` để cảnh báo card mạng down; rule này không bật mặc định để tránh cảnh báo trên các cổng không sử dụng.
- **Thông báo:** Dashboard/âm thanh, Telegram, webhook tương thích Discord/Slack và SMTP.
- **Lưu trữ cục bộ:** SQLite WAL, snapshot mới nhất, metrics độ phân giải cao và dữ liệu tổng hợp theo giờ. Giao diện dùng uPlot được đóng gói cùng ứng dụng, không cần CDN.

## Yêu cầu

- Windows Server/Windows 11 64-bit hoặc Ubuntu 22.04+ cho NOC Server.
- Python 3.13.x 64-bit trên Windows; Python 3.10+ trên Ubuntu/Linux.
- Git để clone mã nguồn.
- Kết nối Internet trong lúc cài Python packages; khi chạy dashboard, frontend không cần truy cập CDN.

## Cài đặt NOC Server

### Cài NOC Server trên Windows

Sau khi clone repository và mở PowerShell tại thư mục `noc-monitor`, chạy:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\WindowSetup\Server\setup.ps1
```

Script kiểm tra Python 3.13, tạo virtual environment `.venv`, cài các package, hỏi tạo Global Admin nếu chưa có, đăng ký task `NOC Monitor` cho tài khoản Windows hiện tại và khởi động server ẩn trên cổng `6969`. Mặc định server chỉ nhận kết nối trên máy cục bộ. Task tự chạy khi tài khoản đăng nhập và thử khởi động lại nếu server bị lỗi. Setup chỉ báo thành công sau khi `/api/health` trả HTTP 200.

Khi chạy lần đầu, ứng dụng tự tạo database SQLite `data/noc.db`, schema, host `NOC Server (Local)` và các rule cảnh báo mặc định. Không cần cài hoặc cấu hình SQL Server/MySQL riêng.

Khi cài bằng `setup.ps1`, lệnh sẽ hỏi username và password của Global Admin đầu tiên; password được lưu dưới dạng hash. Nếu server đã được cài nhưng chưa có tài khoản, chạy lệnh sau từ thư mục dự án:

```powershell
.\.venv\Scripts\python.exe -m noc.auth_cli bootstrap
```

Sau đó mở trang đăng nhập tại:

```text
http://127.0.0.1:6969/login
```

Quản lý task trong PowerShell:

```powershell
Get-ScheduledTask -TaskName "NOC Monitor"
Start-ScheduledTask -TaskName "NOC Monitor"
Stop-ScheduledTask -TaskName "NOC Monitor"
```

Output và lỗi server được ghi vào `data/noc-server.out.log` và `data/noc-server.err.log`. Task chỉ chạy sau khi tài khoản Windows đăng nhập; để dừng hẳn tự khởi động, xóa task bằng `Unregister-ScheduledTask -TaskName "NOC Monitor"`.

### Cài NOC Server trên Ubuntu/Linux

Ubuntu 22.04 trở lên được hỗ trợ. Từ thư mục source đã clone, chạy:

```bash
sudo bash ./LinuxSetup/Server/install_linux.sh
```

Script cài NOC Server vào `/opt/noc-monitor`, tạo virtualenv, hỏi tạo Global Admin, đăng ký systemd service `noc-monitor` và giữ dashboard trên cổng `6969`. Mặc định server chỉ bind vào localhost. Nếu cần cho agent hoặc operator trong LAN truy cập:

```bash
sudo bash ./LinuxSetup/Server/install_linux.sh --lan-access
```

Tùy chọn `--lan-access` bind server vào `0.0.0.0`; hãy giới hạn TCP 6969 bằng firewall của máy Linux. Xem log bằng:

```bash
sudo systemctl status noc-monitor
sudo journalctl -u noc-monitor -f
```

### Cài thủ công

Nếu muốn tự chạy từng bước trên Windows:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m noc.auth_cli bootstrap
python run_server.py
```

Nếu PowerShell chặn kích hoạt virtual environment, chỉ cho phép script trong cửa sổ hiện tại rồi kích hoạt lại:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Trên Ubuntu/Linux, dùng Python 3.10 trở lên:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m noc.auth_cli bootstrap
python run_server.py
```

## Truy cập NOC từ LAN

Để cho operator hoặc agent trong LAN kết nối, chạy PowerShell bằng quyền Administrator và cài với tùy chọn LAN:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\WindowSetup\Server\setup.ps1 -LanAccess
```

Tùy chọn này bind server vào các interface mạng. Chỉ cho phép subnet tin cậy qua Windows Firewall:

```powershell
New-NetFirewallRule -DisplayName "NOC Monitor LAN" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 6969 -RemoteAddress LocalSubnet -Profile Domain,Private
```

Không đưa cổng 6969 trực tiếp ra Internet. Dùng HTTPS reverse proxy khi cần truy cập từ mạng không tin cậy.

Có thể chạy nền bằng Task Scheduler hoặc NSSM. Với NSSM, chọn `.venv\Scripts\python.exe`, đối số `run_server.py` và thư mục khởi động là thư mục repository. Không bật Uvicorn reload trên server production.

Các biến môi trường chính:

| Biến | Mặc định | Mục đích |
| --- | --- | --- |
| `NOC_HOST` | `127.0.0.1` | Địa chỉ bind; bộ cài Windows `-LanAccess` hoặc Linux `--lan-access` dùng `0.0.0.0` |
| `NOC_PORT` | `6969` | Cổng dashboard/API |
| `NOC_SESSION_TTL_SEC` | `28800` | Thời hạn session (900–86400 giây) |
| `NOC_COOKIE_SECURE` | `0` | Đặt `1` khi dashboard được phục vụ qua HTTPS |
| `NOC_DATA_DIR` | `./data` | Thư mục database |
| `NOC_POLL_INTERVAL_SEC` | `15` | Chu kỳ poll ban đầu của local host |
| `NOC_TIMEOUT_FACTOR` | `3` | Hệ số xác định host stale/offline |
| `NOC_RAW_RETENTION_DAYS` | `7` | Số ngày giữ metrics thô |
| `NOC_HOURLY_RETENTION_DAYS` | `365` | Số ngày giữ dữ liệu tổng hợp theo giờ |
| `NOC_MAX_CONCURRENT_POLLS` | `32` | Số poll đồng thời tối đa |

## Database và tự động khởi tạo

NOC Monitor V1.0.2 dùng **SQLite** qua `aiosqlite`, không dùng Microsoft SQL Server hay MySQL. Database mặc định là `data/noc.db`. Khi server khởi động, ứng dụng tự tạo thư mục, file database, bảng, host local và các rule mặc định nếu chưa có; không cần tạo database, user hay password riêng.

Để lưu database ở nơi khác, đặt `NOC_DATA_DIR` trước khi chạy server:

```powershell
$env:NOC_DATA_DIR = "D:\NOC\data"
$env:NOC_PORT = "6969"
.\.venv\Scripts\python.exe run_server.py
```

Lệnh `setup.ps1` dùng `data/` mặc định và tự khởi tạo SQLite khi server chạy lần đầu.

## Thêm máy chủ và thiết bị

Trong Wallboard chọn **Add host** hoặc vào **Configuration**.

- **Local:** máy đang chạy NOC Server; dịch vụ cần theo dõi, TCP port, URL và Event Log channels có thể cấu hình.
- **Agent:** tạo host trong dashboard, lấy token và lệnh chạy, sau đó cấu hình agent Push hoặc Pull.
- **SNMP:** nhập địa chỉ thiết bị, phiên bản, thông tin truy cập và OID profile phù hợp. Chọn profile theo loại thiết bị và firmware.
- **Ping / HTTP:** cấu hình ICMP, TCP ports, HTTP URLs, mã trạng thái mong đợi và chuỗi nội dung cần có.

SNMP v1/v2c dùng client BER tích hợp; SNMPv3 dùng PySNMP. Chỉ số CPU vendor phụ thuộc firmware/OID của thiết bị. Với SNMP Windows, CPU và Windows Services/Event Log nên thu thập qua agent vì Windows SNMP Service thường không cung cấp `hrProcessorLoad`.

### Agent cho máy được giám sát (cài riêng)

Agent không được cài trên NOC Server. Tải gói **NOC Monitor Agent** riêng trong GitHub Releases và làm theo hướng dẫn Windows/Ubuntu tại [`agent/README.md`](agent/README.md). Agent Push chỉ cần kết nối đi ra tới NOC; không cần mở cổng inbound trên máy được giám sát.

## Cảnh báo và thông báo

Các rule mặc định theo dõi host offline, CPU, RAM, disk, ping latency/loss, Windows Service dừng, chứng chỉ TLS sắp hết hạn và reboot. Có thể thêm rule từ metric catalog. Để cảnh báo khi HTTP status hoặc body check thất bại, chọn metric `http.check_ok` và ngưỡng `0`.

Incident đi qua các trạng thái `OPEN` → `ACKNOWLEDGED` → `RESOLVED`. Rule bỏ qua metric không có dữ liệu; maintenance mode vẫn lưu metrics nhưng tạm dừng đánh giá cảnh báo.

Các kênh thông báo hỗ trợ Telegram, webhook, SMTP và âm thanh trên dashboard. Trình duyệt chỉ phát âm thanh sau khi operator bấm **Bật âm thanh cảnh báo**.

## Bảo mật và vận hành

- Dashboard yêu cầu đăng nhập. `Global Admin` quản lý mọi tài khoản; `Admin` quản lý Operator/Viewer; `Operator` xem số liệu, poll host, bật maintenance và xử lý incident; `Viewer` chỉ xem. Phân quyền được kiểm tra ở backend API.
- Cookie phiên dùng `HttpOnly`, `SameSite=Strict`, thời hạn mặc định 8 giờ; thao tác ghi yêu cầu CSRF token. Khi truy cập qua reverse proxy HTTPS, đặt `NOC_COOKIE_SECURE=1`.
- Không đưa TCP 6969 trực tiếp ra Internet. Khi cần truy cập từ xa, dùng HTTPS reverse proxy và giới hạn mạng operator tin cậy.
- Giới hạn ACL của thư mục `data/` cho service account, SYSTEM và Administrators. API không trả config thô và che các secret trong cấu hình.
- Dùng token riêng cho từng agent; không đưa token, community SNMP hay mật khẩu vào Git.
- Theo dõi log service và sao lưu database theo quy trình vận hành của Windows Server.

## Kiểm tra

```powershell
python -m pytest tests/ -v
python run_agent.py --once --push-url "http://127.0.0.1:6969/api/agent/push" --token YOUR_AGENT_TOKEN
```

Với thiết bị SNMP thật, dùng **Test SNMP** và xác minh profile/OID trước khi dựa vào số liệu để vận hành. OID vendor thay đổi theo sản phẩm và firmware.

## API chính

- `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`, `POST /api/auth/change-password`
- `GET/POST /api/auth/users`, `PUT /api/auth/users/{id}` (chỉ cấp vai trò thấp hơn hoặc bằng cấp quản trị của caller)
- `GET/POST /api/hosts`, `PUT/DELETE /api/hosts/{id}`
- `POST /api/hosts/{id}/poll`, `/maintenance`, `/test-snmp`
- `GET /api/snapshots`, `GET /api/metrics/{host_id}?range=1h|6h|24h|7d|30d`
- `GET/POST /api/rules`, `PUT/DELETE /api/rules/{id}`
- `GET /api/incidents`, `POST /api/incidents/{id}/ack|resolve`
- `GET/PUT/DELETE /api/channels`, `POST /api/channels/{id}/test`
- `POST /api/agent/push` với header `X-Agent-Token`
- WebSocket `/ws/live`
