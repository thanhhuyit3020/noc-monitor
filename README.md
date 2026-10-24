# NOC Monitor V1.0

> **Mô tả GitHub:** NOC Monitor V1.0: Nền tảng NOC giám sát máy chủ và thiết bị mạng qua Agent, SNMP, ICMP, TCP, HTTP; dashboard thời gian thực và cảnh báo đa kênh trên Windows Server.

NOC Monitor là phần mềm giám sát tập trung gọn nhẹ theo mô hình Zabbix/PRTG. Máy chủ NOC thu thập số liệu, lưu lịch sử trong SQLite và hiển thị trạng thái hệ thống trên dashboard web. Có thể giám sát máy chủ Windows/Linux và thiết bị mạng mà không cần cài agent, hoặc cài agent nhẹ để lấy thêm chỉ số chuyên sâu.

## Tính năng

- **Dashboard thời gian thực:** Wallboard, trạng thái host, lịch sử biểu đồ, chi tiết tài nguyên và giao diện tối ưu cho màn hình NOC.
- **Giám sát máy NOC:** CPU tổng/theo core, RAM, swap, dung lượng ổ đĩa, disk I/O và IOPS, lưu lượng từng card mạng, TCP connections, tiến trình, Windows Services, Windows Event Log, uptime và reboot.
- **SNMP agentless:** SNMP v1/v2c bằng client BER Python tích hợp; SNMPv3 qua PySNMP. Hỗ trợ IF-MIB/HOST-RESOURCES-MIB và profile cho Windows, Linux, Cisco, MikroTik, Fortinet, Huawei, HPE Aruba.
- **Agent từ xa:** `run_agent.py` hỗ trợ Push và Pull, thu thập chỉ số hệ điều hành và gửi dữ liệu bằng token.
- **Active probes:** ICMP ping (latency, jitter, packet loss), TCP port, HTTP/HTTPS status và nội dung phản hồi, hạn chứng chỉ TLS.
- **Cảnh báo và sự cố:** Ngưỡng Warning/Critical, số lần vượt ngưỡng liên tiếp, incident theo từng tài nguyên, acknowledge, resolve và maintenance mode.
- **Thông báo:** Dashboard/âm thanh, Telegram, webhook tương thích Discord/Slack và SMTP.
- **Lưu trữ cục bộ:** SQLite WAL, snapshot mới nhất, metrics độ phân giải cao và dữ liệu tổng hợp theo giờ. Giao diện dùng uPlot được đóng gói cùng ứng dụng, không cần CDN.

## Yêu cầu

- Windows Server hoặc Windows 11 64-bit cho NOC Server.
- Python 3.13.x 64-bit.
- Git for Windows để clone mã nguồn.
- Kết nối Internet trong lúc cài Python packages; khi chạy dashboard, frontend không cần truy cập CDN.

## Cài đặt NOC Server

Mở PowerShell tại thư mục muốn cài phần mềm:

```powershell
git clone https://github.com/thanhhuyit3020/noc-monitor.git
cd noc-monitor
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python run_server.py
```

Mở trình duyệt trên máy chủ NOC:

```text
http://127.0.0.1:8080/
```

Lần chạy đầu sẽ tạo `data/noc.db`, host `NOC Server (Local)` và các rule cảnh báo mặc định.

Nếu PowerShell chặn kích hoạt virtual environment, chỉ cho phép script trong cửa sổ hiện tại rồi kích hoạt lại:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Cấu hình mạng và khởi động

Mặc định server bind `0.0.0.0:8080` để operator trong LAN có thể truy cập. Để chỉ mở trên máy cục bộ, đặt biến môi trường trước khi chạy:

```powershell
$env:NOC_HOST = "127.0.0.1"
$env:NOC_PORT = "8080"
python run_server.py
```

Nếu cần truy cập từ LAN, mở TCP 8080 trong Windows Firewall:

```powershell
netsh advfirewall firewall add rule name="NOC Dashboard" dir=in action=allow protocol=TCP localport=8080
```

Có thể chạy nền bằng Task Scheduler hoặc NSSM. Với NSSM, chọn `.venv\Scripts\python.exe`, đối số `run_server.py` và thư mục khởi động là thư mục repository. Không bật Uvicorn reload trên server production.

Các biến môi trường chính:

| Biến | Mặc định | Mục đích |
| --- | --- | --- |
| `NOC_HOST` | `0.0.0.0` | Địa chỉ bind của web server |
| `NOC_PORT` | `8080` | Cổng dashboard/API |
| `NOC_DATA_DIR` | `./data` | Thư mục database |
| `NOC_POLL_INTERVAL_SEC` | `15` | Chu kỳ poll ban đầu của local host |
| `NOC_TIMEOUT_FACTOR` | `3` | Hệ số xác định host stale/offline |
| `NOC_RAW_RETENTION_DAYS` | `7` | Số ngày giữ metrics thô |
| `NOC_HOURLY_RETENTION_DAYS` | `365` | Số ngày giữ dữ liệu tổng hợp theo giờ |
| `NOC_MAX_CONCURRENT_POLLS` | `32` | Số poll đồng thời tối đa |

## Thêm máy chủ và thiết bị

Trong Wallboard chọn **Add host** hoặc vào **Configuration**.

- **Local:** máy đang chạy NOC Server; dịch vụ cần theo dõi, TCP port, URL và Event Log channels có thể cấu hình.
- **Agent:** tạo host trong dashboard, lấy token và lệnh chạy, sau đó cấu hình agent Push hoặc Pull.
- **SNMP:** nhập địa chỉ thiết bị, phiên bản, thông tin truy cập và OID profile phù hợp. Chọn profile theo loại thiết bị và firmware.
- **Ping / HTTP:** cấu hình ICMP, TCP ports, HTTP URLs, mã trạng thái mong đợi và chuỗi nội dung cần có.

SNMP v1/v2c dùng client BER tích hợp; SNMPv3 dùng PySNMP. Chỉ số CPU vendor phụ thuộc firmware/OID của thiết bị. Với SNMP Windows, CPU và Windows Services/Event Log nên thu thập qua agent vì Windows SNMP Service thường không cung cấp `hrProcessorLoad`.

### Cài agent trên máy từ xa

Sao chép `run_agent.py` sang Windows hoặc Linux cần giám sát. Cài Python 3.13 và `psutil`; trên Windows cài thêm `pywin32` nếu cần Event Log:

```powershell
py -3.13 -m pip install psutil pywin32
python run_agent.py --once --push-url "http://NOC_SERVER_IP:8080/api/agent/push" --token YOUR_AGENT_TOKEN
```

Trên Linux, cài `psutil` rồi chạy bằng Python 3.13:

```bash
python3 -m pip install psutil
python3 run_agent.py --once --push-url "http://NOC_SERVER_IP:8080/api/agent/push" --token YOUR_AGENT_TOKEN
```

Để agent gửi liên tục, bỏ `--once`:

```powershell
python run_agent.py --push-url "http://NOC_SERVER_IP:8080/api/agent/push" --token YOUR_AGENT_TOKEN
```

Push mode không mở cổng lắng nghe trên máy agent. Pull mode chỉ bind loopback theo mặc định; chỉ mở bind/firewall từ xa khi thật sự cần thiết.

## Cảnh báo và thông báo

Các rule mặc định theo dõi host offline, CPU, RAM, disk, ping latency/loss, Windows Service dừng, chứng chỉ TLS sắp hết hạn và reboot. Có thể thêm rule từ metric catalog. Để cảnh báo khi HTTP status hoặc body check thất bại, chọn metric `http.check_ok` và ngưỡng `0`.

Incident đi qua các trạng thái `OPEN` → `ACKNOWLEDGED` → `RESOLVED`. Rule bỏ qua metric không có dữ liệu; maintenance mode vẫn lưu metrics nhưng tạm dừng đánh giá cảnh báo.

Các kênh thông báo hỗ trợ Telegram, webhook, SMTP và âm thanh trên dashboard. Trình duyệt chỉ phát âm thanh sau khi operator bấm **Bật âm thanh cảnh báo**.

## Bảo mật và vận hành

- Bản V1.0 chưa có đăng nhập người dùng. Chỉ cho phép truy cập từ mạng operator tin cậy; không đưa TCP 8080 trực tiếp ra Internet. Khi cần truy cập WAN, đặt sau reverse proxy HTTPS có xác thực.
- Giới hạn ACL của thư mục `data/` cho service account, SYSTEM và Administrators. API không trả config thô và che các secret trong cấu hình.
- Dùng token riêng cho từng agent; không đưa token, community SNMP hay mật khẩu vào Git.
- Theo dõi log service và sao lưu database theo quy trình vận hành của Windows Server.

## Kiểm tra

```powershell
python -m pytest tests/ -v
python run_agent.py --once --push-url "http://127.0.0.1:8080/api/agent/push" --token YOUR_AGENT_TOKEN
```

Với thiết bị SNMP thật, dùng **Test SNMP** và xác minh profile/OID trước khi dựa vào số liệu để vận hành. OID vendor thay đổi theo sản phẩm và firmware.

## API chính

- `GET/POST /api/hosts`, `PUT/DELETE /api/hosts/{id}`
- `POST /api/hosts/{id}/poll`, `/maintenance`, `/test-snmp`
- `GET /api/snapshots`, `GET /api/metrics/{host_id}?range=1h|6h|24h|7d|30d`
- `GET/POST /api/rules`, `PUT/DELETE /api/rules/{id}`
- `GET /api/incidents`, `POST /api/incidents/{id}/ack|resolve`
- `GET/PUT/DELETE /api/channels`, `POST /api/channels/{id}/test`
- `POST /api/agent/push` với header `X-Agent-Token`
- WebSocket `/ws/live`
