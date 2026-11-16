(() => {
  const $ = selector => document.querySelector(selector);
  const state = {hosts: [], snapshots: [], incidents: [], rules: [], channels: [], users: [], user: null, page: "wallboard", socket: null, retry: 500};
  const messages = {
    vi: {
      language: "Ngôn ngữ", navigation: "Điều hướng", wallboard: "Tổng quan", incidents: "Sự cố", configuration: "Cấu hình", system: "HỆ THỐNG", connecting: "Đang kết nối", liveConnection: "Đã kết nối trực tiếp", reconnecting: "Đang kết nối lại", localPolling: "Giám sát cục bộ · SQLite WAL", networkOperations: "VẬN HÀNH MẠNG", signOut: "Đăng xuất", fullscreen: "Toàn màn hình", fullscreenKiosk: "Toàn màn hình kiosk", audioEnable: "◖ Bật âm thanh cảnh báo", audioDisable: "◖ Âm thanh đang bật · Tắt", monitoredHosts: "Host đang theo dõi", liveTelemetry: "Dữ liệu trực tiếp từ local, agent, SNMP và các probe", filterHosts: "Lọc host…", addHost: "＋ Thêm host", hostsOnline: "HOST ĐANG ONLINE", monitored: "đang theo dõi", openIncidents: "SỰ CỐ ĐANG MỞ", allClear: "không có cảnh báo", critical: "critical", avgCpu: "CPU TRUNG BÌNH", fleetTelemetry: "dữ liệu toàn hệ thống", polling: "GIÁM SÁT", webSocketStream: "luồng WebSocket", noHostMatch: "Không có host phù hợp với bộ lọc.", incidentConsole: "Bảng điều khiển sự cố", incidentSubtitle: "Mở, xác nhận và xử lý các sự kiện được theo dõi", allStates: "Tất cả trạng thái", severity: "Mức độ", incident: "Sự cố", host: "Host", resource: "Tài nguyên", state: "Trạng thái", updated: "Cập nhật", ack: "Xác nhận", resolve: "Xử lý", noIncidents: "Không có sự cố.", incidentAcknowledged: "Đã xác nhận sự cố", incidentResolved: "Đã xử lý sự cố", hosts: "Hosts", hostsSubtitle: "Cấu hình chu kỳ lấy mẫu và thông tin xác thực", alertRules: "Luật cảnh báo", alertRulesSubtitle: "Ngưỡng và số lần lấy mẫu liên tiếp", addRule: "＋ Luật", notificationChannels: "Kênh thông báo", channelsSubtitle: "Dashboard, Telegram, webhook và SMTP", addChannel: "＋ Kênh", userAccess: "Quyền người dùng", userAccessSubtitle: "Quản lý tài khoản dashboard và cấp độ truy cập", addUser: "＋ Người dùng", edit: "Sửa", poll: "Lấy mẫu", maintain: "Bảo trì", resume: "Tiếp tục", delete: "Xóa", disable: "Tắt", manage: "Quản lý", enabled: "đã bật", disabled: "đã tắt", you: "bạn", noData: "Không có dữ liệu.", performanceHistory: "Lịch sử hiệu năng", pollNow: "Lấy mẫu ngay", coreSensors: "Cảm biến chính", packetLoss: "Mất gói", eventErrors: "Lỗi sự kiện / giờ", uptime: "Thời gian hoạt động", tcpEstablished: "TCP established", perCoreCpu: "CPU theo lõi", usage: "Mức dùng", disks: "Ổ đĩa", volume: "Volume", mount: "Mount", used: "Đã dùng", free: "Còn trống", networkInterfaces: "Giao diện mạng", interface: "Giao diện", networkState: "Trạng thái", receive: "Nhận", transmit: "Gửi", speed: "Tốc độ", errorsPerSecond: "Lỗi/giây", dropsPerSecond: "Drop/giây", diskIo: "I/O ổ đĩa", device: "Thiết bị", read: "Đọc", write: "Ghi", readIops: "IOPS đọc", writeIops: "IOPS ghi", tcpStates: "Trạng thái TCP", windowsServices: "Dịch vụ Windows", service: "Dịch vụ", startup: "Khởi động", topProcessesCpu: "Tiến trình dùng CPU cao nhất", process: "Tiến trình", user: "Người dùng", memory: "Bộ nhớ", recentWindowsErrors: "Lỗi Windows gần đây", time: "Thời gian", channel: "Kênh", id: "ID", source: "Nguồn", message: "Thông báo", probes: "Probe TCP / HTTP / TLS", target: "Đích", stateStatus: "Trạng thái / mã", latency: "Độ trễ", sslDays: "Số ngày SSL", statusDetail: "Chi tiết trạng thái", configureAgent: "Cài agent từ xa trên máy chủ này để thu thập CPU, RAM, ổ đĩa và tiến trình.", noHistory: "Chưa có lịch sử cho số liệu này", editHost: "Sửa host", hostUpdated: "Đã cập nhật host", hostAdded: "Đã thêm host", deleteHostConfirm: "Xóa host {name}, toàn bộ số liệu đã lưu và lịch sử sự cố?", hostDeleted: "Đã xóa host", deleteRuleConfirm: "Xóa luật cảnh báo này?", ruleDeleted: "Đã xóa luật", audioPlayed: "Đã phát âm thanh cảnh báo", testSent: "Đã gửi thử thông báo", notificationFailed: "Gửi thông báo thất bại", deleteChannelConfirm: "Xóa kênh thông báo này?", pollCompleted: "Đã lấy mẫu xong", addMonitoredHost: "Thêm host theo dõi", hostConfiguration: "Cấu hình host và chu kỳ lấy mẫu", displayName: "Tên hiển thị", hostnameIp: "Hostname / IP", monitoringType: "Loại giám sát", localNocServer: "Máy chủ NOC local", remoteAgent: "Agent từ xa", pingHttp: "Ping / TCP / HTTP", pollInterval: "Chu kỳ lấy mẫu (giây)", pollingEnabled: "Bật giám sát", windowsServiceNames: "Tên dịch vụ Windows", tcpPorts: "Cổng TCP", httpUrls: "URL HTTP", eventLogChannels: "Kênh Event Log", agentTransport: "Giao thức agent", pushRecommended: "Push (khuyến nghị)", pull: "Pull", agentToken: "Agent token", pullUrl: "URL Pull (tùy chọn)", agentPort: "Cổng agent", snmpVersion: "Phiên bản SNMP", udpPort: "Cổng UDP", community: "Community", oidProfile: "OID profile", customCpuOid: "CPU OID tùy chỉnh", walkTimeout: "Thời gian walk (giây)", excludedInterfaces: "Giao diện loại trừ", snmpUser: "User SNMPv3", snmpAuth: "Xác thực SNMPv3", authKey: "Khóa xác thực SNMPv3", snmpPrivacy: "Mã hóa SNMPv3", privacyKey: "Khóa mã hóa SNMPv3", icmpPing: "Ping ICMP", checkSsl: "Kiểm tra chứng chỉ SSL", expectedStatuses: "Mã HTTP mong đợi", bodyMatch: "Nội dung cần có", sslWarningDays: "Số ngày cảnh báo SSL", sslCriticalDays: "Số ngày nghiêm trọng SSL", cancel: "Hủy", saveHost: "Lưu host", agentCreated: "Đã tạo host agent", agentCreatedSubtitle: "Sao chép lệnh này sang máy chủ Windows hoặc Linux từ xa. Giữ token bí mật.", runOnServer: "Chạy trên máy chủ được giám sát", copyCommand: "Sao chép lệnh", done: "Xong", commandCopied: "Đã sao chép lệnh agent", editAlertRule: "Sửa luật cảnh báo", newAlertRule: "Luật cảnh báo mới", ruleSubtitle: "Bỏ qua số liệu thiếu; luật chỉ đánh giá cảm biến mà từng host hỗ trợ.", ruleName: "Tên luật", metric: "Số liệu", operator: "Toán tử", warningThreshold: "Ngưỡng cảnh báo", criticalThreshold: "Ngưỡng nghiêm trọng", consecutivePolls: "Số lần lấy mẫu liên tiếp", cooldown: "Thời gian chờ (giây)", saveRule: "Lưu luật", ruleSaved: "Đã lưu luật", editChannel: "Sửa kênh thông báo", addChannelTitle: "Thêm kênh thông báo", channelSubtitle: "Thông tin xác thực sẽ được che sau khi lưu.", channelType: "Loại kênh", dashboardAudio: "Âm thanh dashboard", emailSmtp: "Email SMTP", botToken: "Bot token", chatId: "Chat ID", webhookUrl: "URL Webhook", optionalHeaders: "Header tùy chọn dạng JSON", smtpHost: "SMTP host", from: "Từ", to: "Đến", password: "Mật khẩu", startTls: "Dùng STARTTLS", implicitTls: "Dùng TLS ngầm định", alarmAudioNotice: "Âm thanh cảnh báo sẽ phát trên dashboard sau khi bật âm thanh trình duyệt.", webhookJsonError: "Header webhook phải là JSON hợp lệ", channelSaved: "Đã lưu kênh", manageUser: "Quản lý người dùng", createUser: "Tạo người dùng", passwordRule: "Mật khẩu phải có ít nhất 8 ký tự.", accessLevel: "Cấp độ truy cập", resetPassword: "Đặt lại mật khẩu (tùy chọn)", initialPassword: "Mật khẩu ban đầu", accountActive: "Tài khoản đang hoạt động", saveUser: "Lưu người dùng", initialPasswordRequired: "Hãy nhập mật khẩu ban đầu.", userUpdated: "Đã cập nhật người dùng", userCreated: "Đã tạo người dùng", changePassword: "Đổi mật khẩu", changePasswordSubtitle: "Dùng ít nhất 8 ký tự. Các phiên đăng nhập khác sẽ bị kết thúc.", currentPassword: "Mật khẩu hiện tại", newPassword: "Mật khẩu mới", passwordChanged: "Đã đổi mật khẩu", audioError: "Không thể bật âm thanh. Hãy bấm nút lần nữa để cho phép âm thanh trình duyệt.", audioStartError: "Không thể khởi động âm thanh. Hãy bấm nút lần nữa để cho phép âm thanh trình duyệt.", loginTitle: "Đăng nhập NOC Monitor", loginSubtitle: "Dùng tài khoản NOC để mở dashboard giám sát.", firstUse: "Lần đầu sử dụng", firstUseDescription: "Tạo Global Admin đầu tiên bằng PowerShell trong thư mục dự án:", username: "Tài khoản", signIn: "Đăng nhập", loginFootnote: "Quyền truy cập do quản trị viên NOC quản lý.", apiAuthRequired: "Yêu cầu xác thực", apiNetworkError: "Không thể kết nối đến máy chủ NOC.", apiLoginFailed: "Đăng nhập thất bại.", apiUnableSignIn: "Không thể đăng nhập.", allConfiguredProbesFailed: "Tất cả probe đã cấu hình đều thất bại", awaitingFirstSample: "Đang chờ mẫu đầu tiên", noIncidentsShort: "Không có sự cố", noHosts: "Không có host", status: "Trạng thái", failed: "thất bại", unknown: "không rõ"
    },
    en: {
      language: "Language", navigation: "Main navigation", wallboard: "Wallboard", incidents: "Incidents", configuration: "Configuration", system: "SYSTEM", connecting: "Connecting", liveConnection: "Live connection", reconnecting: "Reconnecting", localPolling: "Local polling · SQLite WAL", networkOperations: "NETWORK OPERATIONS", signOut: "Sign out", fullscreen: "Fullscreen", fullscreenKiosk: "Fullscreen kiosk", audioEnable: "◖ Enable alarm sound", audioDisable: "◖ Alarm sound on · Turn off", monitoredHosts: "Monitored hosts", liveTelemetry: "Live telemetry from local, agent, SNMP and active probes", filterHosts: "Filter hosts…", addHost: "＋ Add host", hostsOnline: "HOSTS ONLINE", monitored: "monitored", openIncidents: "OPEN INCIDENTS", allClear: "all clear", critical: "critical", avgCpu: "AVG CPU", fleetTelemetry: "fleet telemetry", polling: "POLLING", webSocketStream: "WebSocket stream", noHostMatch: "No hosts match this filter.", incidentConsole: "Incident console", incidentSubtitle: "Open, acknowledge and resolve monitored events", allStates: "All states", severity: "Severity", incident: "Incident", host: "Host", resource: "Resource", state: "State", updated: "Updated", ack: "ACK", resolve: "Resolve", noIncidents: "No incidents.", incidentAcknowledged: "Incident acknowledged", incidentResolved: "Incident resolved", hosts: "Hosts", hostsSubtitle: "Configure polling and credentials", alertRules: "Alert rules", alertRulesSubtitle: "Thresholds and consecutive polls", addRule: "＋ Rule", notificationChannels: "Notification channels", channelsSubtitle: "Dashboard, Telegram, webhook and SMTP", addChannel: "＋ Channel", userAccess: "User access", userAccessSubtitle: "Manage dashboard accounts and access levels", addUser: "＋ User", edit: "Edit", poll: "Poll", maintain: "Maintain", resume: "Resume", delete: "Delete", disable: "Disable", manage: "Manage", enabled: "enabled", disabled: "disabled", you: "you", noData: "No data available.", performanceHistory: "Performance history", pollNow: "Poll now", coreSensors: "Core sensors", packetLoss: "Packet loss", eventErrors: "Event errors / h", uptime: "Uptime", tcpEstablished: "TCP established", perCoreCpu: "Per-core CPU", usage: "Usage", disks: "Disks", volume: "Volume", mount: "Mount", used: "Used", free: "Free", networkInterfaces: "Network interfaces", interface: "Interface", networkState: "State", receive: "RX", transmit: "TX", speed: "Speed", errorsPerSecond: "Errors/s", dropsPerSecond: "Drops/s", diskIo: "Disk I/O", device: "Device", read: "Read", write: "Write", readIops: "Read IOPS", writeIops: "Write IOPS", tcpStates: "TCP states", windowsServices: "Windows services", service: "Service", startup: "Startup", topProcessesCpu: "Top processes by CPU", process: "Process", user: "User", memory: "Memory", recentWindowsErrors: "Recent Windows errors", time: "Time", channel: "Channel", id: "ID", source: "Source", message: "Message", probes: "TCP / HTTP / TLS probes", target: "Target", stateStatus: "State / status", latency: "Latency", sslDays: "SSL days", statusDetail: "Status detail", configureAgent: "Configure a remote agent on this server to collect CPU, RAM, disks, and process metrics.", noHistory: "No history collected for this metric yet", editHost: "Edit host", hostUpdated: "Host updated", hostAdded: "Host added", deleteHostConfirm: "Delete host {name}, its stored metrics, and its incident history?", hostDeleted: "Host deleted", deleteRuleConfirm: "Delete this alert rule?", ruleDeleted: "Rule deleted", audioPlayed: "Audio alarm played", testSent: "Test notification sent", notificationFailed: "Notification failed", deleteChannelConfirm: "Delete this notification channel?", pollCompleted: "Poll completed", addMonitoredHost: "Add monitored host", hostConfiguration: "Host configuration and polling settings", displayName: "Display name", hostnameIp: "Hostname / IP", monitoringType: "Monitoring type", localNocServer: "Local NOC server", remoteAgent: "Remote agent", pingHttp: "Ping / TCP / HTTP", pollInterval: "Poll interval (seconds)", pollingEnabled: "Polling enabled", windowsServiceNames: "Windows service names", tcpPorts: "TCP ports", httpUrls: "HTTP URLs", eventLogChannels: "Event log channels", agentTransport: "Agent transport", pushRecommended: "Push (recommended)", pull: "Pull", agentToken: "Agent token", pullUrl: "Pull URL (optional)", agentPort: "Agent port", snmpVersion: "SNMP version", udpPort: "UDP port", community: "Community", oidProfile: "OID profile", customCpuOid: "Custom CPU OID", walkTimeout: "Walk timeout (sec)", excludedInterfaces: "Excluded interfaces", snmpUser: "SNMPv3 user", snmpAuth: "SNMPv3 auth", authKey: "SNMPv3 auth key", snmpPrivacy: "SNMPv3 privacy", privacyKey: "SNMPv3 privacy key", icmpPing: "ICMP ping", checkSsl: "Check SSL certificate", expectedStatuses: "Expected HTTP statuses", bodyMatch: "Body should contain", sslWarningDays: "SSL warning days", sslCriticalDays: "SSL critical days", cancel: "Cancel", saveHost: "Save host", agentCreated: "Agent host created", agentCreatedSubtitle: "Copy this command to the remote Windows or Linux server. Keep the token private.", runOnServer: "Run on the monitored server", copyCommand: "Copy command", done: "Done", commandCopied: "Agent command copied", editAlertRule: "Edit alert rule", newAlertRule: "New alert rule", ruleSubtitle: "Missing metrics are skipped; rules only evaluate sensors supported by each host.", ruleName: "Rule name", metric: "Metric", operator: "Operator", warningThreshold: "Warning threshold", criticalThreshold: "Critical threshold", consecutivePolls: "Consecutive polls", cooldown: "Cooldown (seconds)", saveRule: "Save rule", ruleSaved: "Rule saved", editChannel: "Edit notification channel", addChannelTitle: "Add notification channel", channelSubtitle: "Notification credentials are masked after saving.", channelType: "Channel type", dashboardAudio: "Dashboard audio", emailSmtp: "Email SMTP", botToken: "Bot token", chatId: "Chat ID", webhookUrl: "Webhook URL", optionalHeaders: "Optional headers as JSON", smtpHost: "SMTP host", from: "From", to: "To", password: "Password", startTls: "Use STARTTLS", implicitTls: "Use implicit TLS", alarmAudioNotice: "Alarm audio is played in this dashboard after the user enables browser audio.", webhookJsonError: "Webhook headers must be valid JSON", channelSaved: "Channel saved", manageUser: "Manage user", createUser: "Create user", passwordRule: "Passwords must contain at least 8 characters.", accessLevel: "Access level", resetPassword: "Reset password (optional)", initialPassword: "Initial password", accountActive: "Account active", saveUser: "Save user", initialPasswordRequired: "Set an initial password.", userUpdated: "User updated", userCreated: "User created", changePassword: "Change password", changePasswordSubtitle: "Use at least 8 characters. Other sign-ins will be ended.", currentPassword: "Current password", newPassword: "New password", passwordChanged: "Password changed", audioError: "Audio could not start. Click the button again to allow browser audio.", audioStartError: "Audio could not start. Click the button again to allow browser audio.", loginTitle: "Sign in to NOC Monitor", loginSubtitle: "Use your NOC account to open the monitoring dashboard.", firstUse: "First use", firstUseDescription: "Create the first Global Admin from PowerShell in the project folder:", username: "Username", signIn: "Sign in", loginFootnote: "Access is managed by your NOC administrator.", apiAuthRequired: "Authentication required", apiNetworkError: "Unable to reach the NOC server.", apiLoginFailed: "Sign in failed.", apiUnableSignIn: "Unable to sign in.", allConfiguredProbesFailed: "All configured probes failed", awaitingFirstSample: "Awaiting first sample", noIncidentsShort: "No incidents", noHosts: "No hosts", status: "Status", failed: "failed", unknown: "unknown"
    }
  };
  Object.assign(messages.vi, {configurationSubtitle: "Hosts, luật cảnh báo và kênh thông báo", port: "Cổng", username: "Tài khoản", topProcessesMemory: "Tiến trình dùng RAM cao nhất", test: "Kiểm tra", viewerRole: "chỉ xem", operatorRole: "vận hành", adminRole: "quản trị viên", globalAdminRole: "quản trị viên toàn cục", invalidCredentials: "Tên tài khoản hoặc mật khẩu không đúng", tooManyAttempts: "Quá nhiều lần đăng nhập thất bại. Hãy thử lại sau một phút.", currentPasswordIncorrect: "Mật khẩu hiện tại không đúng", userNotFound: "Không tìm thấy người dùng", hostNotFound: "Không tìm thấy host", ruleNotFound: "Không tìm thấy luật", channelNotFound: "Không tìm thấy kênh", failedToFetch: "Không thể kết nối đến máy chủ NOC."});
  Object.assign(messages.en, {configurationSubtitle: "Hosts, alert rules and notification channels", port: "Port", username: "Username", topProcessesMemory: "Top processes by memory", test: "Test", viewerRole: "viewer", operatorRole: "operator", adminRole: "admin", globalAdminRole: "global admin", invalidCredentials: "Invalid username or password", tooManyAttempts: "Too many failed sign-in attempts. Try again in one minute.", currentPasswordIncorrect: "Current password is incorrect", userNotFound: "User not found", hostNotFound: "Host not found", ruleNotFound: "Rule not found", channelNotFound: "Channel not found", failedToFetch: "Unable to reach the NOC server."});
  let language = localStorage.getItem("noc-language") || "vi";
  const t = (key, values = {}) => (messages[language][key] || messages.en[key] || key).replace(/\{(\w+)\}/g, (_, name) => values[name] ?? "");
  const serverMessageKeys = {"Authentication required": "apiAuthRequired", "Unable to reach the NOC server.": "apiNetworkError", "Failed to fetch": "failedToFetch", "Sign in failed.": "apiLoginFailed", "Unable to sign in.": "apiUnableSignIn", "All configured probes failed": "allConfiguredProbesFailed", "Invalid username or password": "invalidCredentials", "Too many failed sign-in attempts. Try again in one minute.": "tooManyAttempts", "Current password is incorrect": "currentPasswordIncorrect", "User not found": "userNotFound", "Host not found": "hostNotFound", "Rule not found": "ruleNotFound", "Channel not found": "channelNotFound"};
  const translateServerMessage = message => serverMessageKeys[message] ? t(serverMessageKeys[message]) : message;
  const roleRank = {viewer: 1, operator: 2, admin: 3, global_admin: 4};
  const roleLabel = role => t({viewer: "viewerRole", operator: "operatorRole", admin: "adminRole", global_admin: "globalAdminRole"}[role] || "unknown");
  const titleByPage = {wallboard: "wallboard", incidents: "incidents", settings: "configuration"};
  const esc = value => String(value ?? "").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
  const stamp = value => value ? new Date(value * 1000).toLocaleString(language === "vi" ? "vi-VN" : "en-US") : "—";
  const num = (value, digits = 1) => value === null || value === undefined || Number.isNaN(Number(value)) ? "—" : Number(value).toFixed(digits);
  const pctClass = value => Number(value) >= 95 ? "crit" : Number(value) >= 80 ? "warn" : "";
  const hostById = id => state.hosts.find(host => host.id === id);
  const canOperate = () => roleRank[state.user?.role] >= roleRank.operator;
  const canAdmin = () => roleRank[state.user?.role] >= roleRank.admin;

  function applyLanguage() {
    document.documentElement.lang = language;
    document.querySelectorAll("[data-i18n]").forEach(node => { node.textContent = t(node.dataset.i18n); });
    document.querySelectorAll("[data-i18n-placeholder]").forEach(node => { node.placeholder = t(node.dataset.i18nPlaceholder); });
    document.querySelectorAll("[data-i18n-title]").forEach(node => { node.title = t(node.dataset.i18nTitle); });
    document.querySelectorAll("[data-i18n-aria-label]").forEach(node => { node.setAttribute("aria-label", t(node.dataset.i18nAriaLabel)); });
    ["vi", "en"].forEach(code => { const button = $("#lang-" + code); if (button) { button.classList.toggle("active", code === language); button.setAttribute("aria-pressed", String(code === language)); } });
    $("#page-title").textContent = t(titleByPage[state.page]);
    if (state.user) render();
  }

  function setLanguage(next) {
    language = next;
    localStorage.setItem("noc-language", language);
    applyLanguage();
  }

  function cookieValue(name) {
    const item = document.cookie.split(";").map(value => value.trim()).find(value => value.startsWith(name + "="));
    return item ? decodeURIComponent(item.slice(name.length + 1)) : "";
  }

  async function api(path, options = {}) {
    const method = (options.method || "GET").toUpperCase();
    const headers = {"Content-Type": "application/json", ...(options.headers || {})};
    if (!["GET", "HEAD", "OPTIONS"].includes(method)) headers["X-CSRF-Token"] = cookieValue("noc_csrf");
    const response = await fetch(path, {...options, method, credentials: "same-origin", headers});
    if (!response.ok) {
      let message = response.statusText;
      try { const body = await response.json(); message = body.detail || message; } catch {}
      if (response.status === 401) location.replace("/login");
      throw new Error(translateServerMessage(message));
    }
    return response.status === 204 ? null : response.json();
  }

  function toast(message, kind = "success") {
    const item = document.createElement("div");
    item.className = "toast " + kind;
    item.textContent = message;
    $("#toast-stack").append(item);
    setTimeout(() => item.remove(), 4200);
  }

  async function loadAll() {
    try {
      const [snapshots, hosts, incidents, rules, channels, catalog] = await Promise.all([
        api("/api/snapshots"), api("/api/hosts"), api("/api/incidents"), api("/api/rules"), api("/api/channels"), api("/api/catalog")
      ]);
      state.snapshots = snapshots;
      state.hosts = hosts;
      state.incidents = incidents;
      state.rules = rules;
      state.channels = channels;
      state.users = canAdmin() ? await api("/api/auth/users") : [];
      window.NOC_CATALOG = catalog;
      render();
    } catch (error) { toast(error.message, "error"); }
  }

  function connect() {
    const scheme = location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(scheme + "://" + location.host + "/ws/live");
    state.socket = socket;
    socket.onopen = () => {
      state.retry = 500;
      $("#connection-state").textContent = t("liveConnection");
      $("#ws-indicator").className = "status-dot connected";
      state.heartbeat = setInterval(() => { if (socket.readyState === WebSocket.OPEN) socket.send("ping"); }, 20000);
    };
    socket.onmessage = event => {
      try {
        const message = JSON.parse(event.data);
        if (message.type === "snapshot") {
          const row = state.snapshots.find(host => host.id === message.host_id);
          if (row) {
            row.snapshot = message.snapshot;
            row.status = message.snapshot.status;
            row.status_reason = message.snapshot.status_reason;
            row.ts = message.snapshot.ts;
          }
          renderWallboard();
          setTimeout(loadAll, 350);
        } else if (message.type === "incident" || message.type === "incident_resolved" || message.type === "incident_acknowledged") {
          setTimeout(loadAll, 80);
        } else if (message.type === "hosts_changed" || message.type === "host_status") setTimeout(loadAll, 80);
        else if (message.type === "alarm_test") NocAudio.test().catch(() => {});
      } catch {}
    };
    socket.onclose = event => {
      clearInterval(state.heartbeat);
      if (event.code === 4401) { location.replace("/login"); return; }
      $("#connection-state").textContent = t("reconnecting");
      $("#ws-indicator").className = "status-dot disconnected";
      const delay = state.retry;
      state.retry = Math.min(15000, state.retry * 1.7);
      setTimeout(connect, delay);
    };
    socket.onerror = () => socket.close();
  }

  function render() {
    $("#account-button").textContent = state.user.username + " · " + roleLabel(state.user.role);
    $("#add-host").hidden = !canAdmin();
    $("#add-host-settings").hidden = !canAdmin();
    $("#add-rule").hidden = !canAdmin();
    $("#add-channel").hidden = !canAdmin();
    renderWallboard();
    renderIncidents();
    renderSettings();
    NocAudio.update(activeIncidents());
    $("#incident-count").textContent = state.incidents.filter(item => item.state === "OPEN").length;
  }

  function renderWallboard() {
    const hosts = state.snapshots;
    const up = hosts.filter(host => host.status === "up").length;
    const open = state.incidents.filter(item => item.state === "OPEN").length;
    const critical = state.incidents.filter(item => item.state === "OPEN" && item.severity === "critical").length;
    const avgCpu = hosts.map(host => host.cpu_pct).filter(value => value !== null).reduce((sum, value, _, all) => sum + Number(value) / all.length, 0);
    $("#summary").innerHTML =
      summaryCard(t("hostsOnline"), up + " / " + hosts.length, t("monitored")) +
      summaryCard(t("openIncidents"), String(open), critical ? critical + " " + t("critical") : t("allClear")) +
      summaryCard(t("avgCpu"), num(avgCpu) + "%", t("fleetTelemetry")) +
      summaryCard(t("polling"), "LIVE", t("webSocketStream"));
    const query = $("#host-filter").value.trim().toLowerCase();
    const filtered = hosts.filter(host => (host.name + " " + host.hostname + " " + host.host_type).toLowerCase().includes(query));
    $("#host-grid").innerHTML = filtered.length ? filtered.map(renderHostCard).join("") : '<div class="empty-state">' + esc(t("noHostMatch")) + '</div>';
    $("#host-grid").querySelectorAll("[data-host-card]").forEach(card => {
      card.addEventListener("click", () => openDrawer(card.dataset.hostCard));
      card.addEventListener("keydown", event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); openDrawer(card.dataset.hostCard); } });
    });
  }

  function summaryCard(label, value, note) {
    return '<div class="telemetry-card"><span>' + esc(label) + '</span><strong>' + esc(value) + '</strong><em>' + esc(note) + '</em></div>';
  }

  function metricValue(host, key) {
    const values = host.snapshot && host.snapshot.metrics || [];
    return values.find(metric => metric.key === key && !metric.resource_key)?.value ?? null;
  }

  function activeIncidents() {
    return state.incidents.filter(item => hostById(item.host_id)?.status !== "maintenance");
  }

  function renderHostCard(host) {
    const status = host.status || "unknown";
    const cpu = host.cpu_pct ?? metricValue(host, "cpu.total_pct");
    const ram = host.ram_pct ?? metricValue(host, "ram.used_pct");
    const disk = host.disk_pct ?? Math.max(0, ...(host.snapshot?.metrics || []).filter(metric => metric.key === "disk.used_pct").map(metric => Number(metric.value) || 0));
    const latency = host.latency_ms ?? metricValue(host, "ping.latency_ms");
    return '<article class="host-card status-' + esc(status) + '" data-host-card="' + esc(host.id) + '" tabindex="0" role="button">' +
      '<div class="host-card-top"><div><h3>' + esc(host.name) + '</h3><div class="host-address">' + esc(host.hostname) + ' · ' + esc(host.host_type) + '</div></div><span class="host-badge badge-' + esc(status) + '">' + esc(status) + '</span></div>' +
      '<div class="host-summary">' +
      cardMetric("CPU", cpu, "%") + cardMetric("RAM", ram, "%") + cardMetric("DISK", disk, "%") + cardMetric("LATENCY", latency, "ms") +
      '</div><div class="host-card-footer"><span>' + esc(host.os_info || translateServerMessage(host.status_reason) || t("awaitingFirstSample")) + '</span><span>' + esc(stamp(host.last_seen_at || host.ts)) + '</span></div></article>';
  }

  function cardMetric(label, value, unit) {
    return '<div class="metric"><label>' + esc(label) + '</label><strong class="' + pctClass(value) + '">' + esc(num(value)) + '<small>' + esc(unit) + '</small></strong></div>';
  }

  async function openDrawer(hostId) {
    const host = state.snapshots.find(row => row.id === hostId);
    if (!host) return;
    const drawer = $("#host-drawer");
    drawer.classList.add("open");
    drawer.setAttribute("aria-hidden", "false");
    const detail = host.snapshot?.details || {};
    const config = hostById(hostId)?.config || {};
    const windowsHost = /^windows\b/i.test(host.snapshot?.os_info || "");
    drawer.innerHTML =
      '<div class="drawer-header"><div><h2>' + esc(host.name) + '</h2><p>' + esc(host.hostname) + ' · ' + esc(host.host_type) + ' · ' + esc(host.status) + '</p></div>' +
      '<div class="drawer-actions">' + (host.host_type === "agent" && config.mode !== "pull" ? "" : '<button class="button secondary" data-drawer-poll="' + esc(hostId) + '">' + esc(t("pollNow")) + '</button>') + '<button class="button secondary" data-close-drawer>✕</button></div></div>' +
      '<div class="section-title">' + esc(t("performanceHistory")) + '</div><div class="chart-tools"><select id="chart-metric" class="select"><option value="cpu.total_pct">CPU</option><option value="ram.used_pct">RAM</option><option value="ping.latency_ms">' + esc(t("latency")) + '</option></select><select id="chart-range" class="select"><option>1h</option><option>6h</option><option>24h</option><option>7d</option><option>30d</option></select></div><div id="host-chart" class="chart-box"></div>' +
      '<div class="section-title">' + esc(t("coreSensors")) + '</div><div class="detail-grid">' +
      detailCell("CPU", num(metricValue(host, "cpu.total_pct")) + "%") +
      detailCell("RAM", num(metricValue(host, "ram.used_pct")) + "%") +
      detailCell(t("packetLoss"), num(metricValue(host, "ping.packet_loss_pct")) + "%") +
      detailCell(t("eventErrors"), num(metricValue(host, "eventlog.crit_err_1h"), 0)) +
      detailCell(t("uptime"), formatDuration(metricValue(host, "system.uptime_sec"))) +
      detailCell(t("tcpEstablished"), num(metricValue(host, "tcp.established"), 0)) +
      '</div>' +
      '<div class="section-title">' + esc(t("perCoreCpu")) + '</div>' + detailTable(["Core", t("usage")], (host.snapshot?.metrics || []).filter(metric => metric.key === "cpu.core_pct").map(metric => [metric.resource_key, num(metric.value) + "%"])) +
      '<div class="section-title">' + esc(t("disks")) + '</div>' + detailTable([t("volume"), t("mount"), t("used"), t("free")], (detail.disks || detail.storage || []).map(item => [item.name, item.mountpoint || item.type_oid || "", item.used_pct === undefined ? bytes(item.used_bytes) : num(item.used_pct) + "%", item.free_bytes === undefined ? bytes(Math.max(0, (item.total_bytes || 0) - (item.used_bytes || 0))) : bytes(item.free_bytes)])) +
      '<div class="section-title">' + esc(t("networkInterfaces")) + '</div>' + detailTable([t("interface"), t("networkState"), t("receive"), t("transmit"), t("speed"), t("errorsPerSecond"), t("dropsPerSecond")], (detail.networks || detail.interfaces || []).map(item => [item.name, item.is_up == null && item.status == null ? "unknown" : (item.is_up !== undefined ? item.is_up : Number(item.status) === 1) ? "up" : "down", rate(item.rx_bps), rate(item.tx_bps), item.speed_mbps == null ? "—" : item.speed_mbps + " Mbps", num(item.errors_per_sec ?? ((item.errin_per_sec || 0) + (item.errout_per_sec || 0))), num(item.drops_per_sec ?? ((item.dropin_per_sec || 0) + (item.dropout_per_sec || 0)))])) +
      '<div class="section-title">' + esc(t("diskIo")) + '</div>' + detailTable([t("device"), t("read"), t("write"), t("readIops"), t("writeIops")], (detail.disk_io || []).map(item => [item.name, rate(item.read_bps), rate(item.write_bps), num(item.read_iops), num(item.write_iops)])) +
      '<div class="section-title">' + esc(t("tcpStates")) + '</div>' + detailTable([t("state"), "Connections"], Object.entries(detail.tcp_states || {}).map(row => row)) +
      (windowsHost ? '<div class="section-title">' + esc(t("windowsServices")) + '</div>' + detailTable([t("service"), t("status"), t("startup")], (detail.services || []).map(item => [item.name, item.status, item.start_type])) : "") +
      '<div class="section-title">' + esc(t("topProcessesCpu")) + '</div>' + detailTable(["PID", t("process"), t("user"), "CPU", t("memory")], ((detail.processes || {}).cpu || []).map(item => [item.pid, item.name, item.user || "", num(item.cpu_pct) + "%", num(item.memory_mb) + " MB"])) +
      '<div class="section-title">' + esc(t("topProcessesMemory")) + '</div>' + detailTable(["PID", t("process"), t("user"), "CPU", t("memory")], ((detail.processes || {}).memory || []).map(item => [item.pid, item.name, item.user || "", num(item.cpu_pct) + "%", num(item.memory_mb) + " MB"])) +
      (windowsHost ? '<div class="section-title">' + esc(t("recentWindowsErrors")) + '</div>' + detailTable([t("time"), t("channel"), t("id"), t("source"), t("message")], (detail.event_logs || []).map(item => [item.time, item.channel, item.event_id, item.source, item.message])) : "") +
      '<div class="section-title">' + esc(t("probes")) + '</div>' + detailTable([t("target"), t("stateStatus"), t("latency"), t("sslDays")], (detail.ports || []).map(item => [":" + item.port, item.up ? "up" : "down", num(item.response_ms) + " ms", "—"]).concat((detail.http || []).map(item => [item.url, item.status_code ?? "failed", num(item.response_ms) + " ms", item.ssl_days_remaining === null ? "—" : num(item.ssl_days_remaining) + "d"]))) +
      '<div class="section-title">' + esc(t("statusDetail")) + '</div><div class="muted small">' + esc(translateServerMessage(host.status_reason) || "—") + '</div>';
    if (canAdmin()) {
      const editButton = document.createElement("button");
      editButton.className = "button secondary";
      editButton.textContent = t("edit");
      editButton.onclick = () => { closeDrawer(); openHostForm(hostById(hostId)); };
      drawer.querySelector(".drawer-actions").prepend(editButton);
    }
    if (host.host_type === "ping_http") {
      const note = document.createElement("p");
      note.className = "muted small";
      note.textContent = t("configureAgent");
      drawer.querySelector(".drawer-header").after(note);
    }
    drawer.querySelector("[data-close-drawer]").onclick = closeDrawer;
    const pollButton = drawer.querySelector("[data-drawer-poll]");
    if (pollButton) pollButton.onclick = () => pollHost(hostId);
    $("#chart-metric").onchange = () => drawHistory(hostId);
    $("#chart-range").onchange = () => drawHistory(hostId);
    drawHistory(hostId);
  }

  function closeDrawer() {
    $("#host-drawer").classList.remove("open");
    $("#host-drawer").setAttribute("aria-hidden", "true");
  }

  async function drawHistory(hostId) {
    try {
      const range = $("#chart-range").value;
      const metric = $("#chart-metric").value;
      const response = await api("/api/metrics/" + encodeURIComponent(hostId) + "?range=" + range + "&metric_key=" + encodeURIComponent(metric));
      const unit = metric === "ping.latency_ms" ? "ms" : "%";
      NocCharts.draw($("#host-chart"), response.points, metric, unit);
    } catch (error) { $("#host-chart").textContent = error.message; }
  }

  function detailCell(label, value) {
    return '<div class="detail-cell"><span>' + esc(label) + '</span><strong>' + esc(value) + '</strong></div>';
  }

  function detailTable(headers, rows) {
    if (!rows.length) return '<div class="muted small">' + esc(t("noData")) + '</div>';
    return '<div class="table-wrap"><table class="detail-table"><thead><tr>' + headers.map(cell => '<th>' + esc(cell) + '</th>').join("") + '</tr></thead><tbody>' +
      rows.map(row => '<tr>' + row.map(cell => '<td>' + esc(cell) + '</td>').join("") + '</tr>').join("") + '</tbody></table></div>';
  }

  function bytes(value) {
    if (value === null || value === undefined) return "—";
    const units = ["B", "KB", "MB", "GB", "TB"];
    let number = Number(value), index = 0;
    while (number >= 1024 && index < units.length - 1) { number /= 1024; index++; }
    return number.toFixed(index ? 1 : 0) + " " + units[index];
  }

  function rate(value) { return value === null || value === undefined ? "—" : bytes(value) + "/s"; }
  function formatDuration(value) {
    if (value === null || value === undefined) return "—";
    const days = Math.floor(value / 86400), hours = Math.floor(value % 86400 / 3600);
    return days + (language === "vi" ? " ngày " : "d ") + hours + (language === "vi" ? " giờ" : "h");
  }

  function renderIncidents() {
    const filter = $("#incident-filter").value;
    const rows = state.incidents.filter(item => !filter || item.state === filter);
    $("#incidents-table").innerHTML = rows.length ? rows.map(item =>
      '<tr><td><span class="severity ' + esc(item.severity) + '">' + esc(item.severity) + '</span></td><td><strong>' + esc(item.message) + '</strong></td><td>' + esc(item.host_name || hostById(item.host_id)?.name || item.host_id) + '</td><td>' + esc(item.resource_key || "—") + '</td><td><span class="state-badge state-' + esc(item.state) + '">' + esc(item.state) + '</span></td><td>' + esc(stamp(item.updated_at)) + '</td><td><div class="table-actions">' +
      (canOperate() && item.state === "OPEN" ? '<button class="button secondary" data-ack="' + esc(item.id) + '">' + esc(t("ack")) + '</button>' : '') +
      (canOperate() && item.state !== "RESOLVED" ? '<button class="button secondary" data-resolve="' + esc(item.id) + '">' + esc(t("resolve")) + '</button>' : '') +
      '</div></td></tr>').join("") : '<tr><td colspan="7" class="muted">' + esc(t("noIncidents")) + '</td></tr>';
    $("#incidents-table").querySelectorAll("[data-ack]").forEach(button => button.onclick = () => incidentAction(button.dataset.ack, "ack"));
    $("#incidents-table").querySelectorAll("[data-resolve]").forEach(button => button.onclick = () => incidentAction(button.dataset.resolve, "resolve"));
    $("#incident-count").textContent = state.incidents.filter(item => item.state === "OPEN").length;
    NocAudio.update(activeIncidents());
  }

  async function incidentAction(id, action) {
    try {
      await api("/api/incidents/" + encodeURIComponent(id) + "/" + action, {method: "POST"});
      await loadAll();
      toast(action === "ack" ? t("incidentAcknowledged") : t("incidentResolved"));
    } catch (error) { toast(error.message, "error"); }
  }

  function renderSettings() {
    const manage = canAdmin(), operate = canOperate();
    $("#hosts-table").innerHTML = '<div class="mini-list">' + state.hosts.map(host =>
      '<div class="mini-row"><div class="grow"><strong>' + esc(host.name) + '</strong><div class="muted">' + esc(host.hostname) + ' · ' + esc(host.host_type) + '</div></div><span class="host-badge badge-' + esc(host.status) + '">' + esc(host.status) + '</span><div class="table-actions">' + (manage ? '<button class="button secondary" data-edit-host="' + esc(host.id) + '">' + esc(t("edit")) + '</button>' : '') + (operate && (host.host_type !== "agent" || host.config?.mode === "pull") ? '<button class="button secondary" data-host-poll="' + esc(host.id) + '">' + esc(t("poll")) + '</button>' : '') +
      (operate && host.id !== "local" ? '<button class="button secondary" data-maintenance="' + esc(host.id) + '" data-enabled="' + (host.status === "maintenance" ? "false" : "true") + '">' + esc(host.status === "maintenance" ? t("resume") : t("maintain")) + '</button>' : '') + (manage && host.id !== "local" ? '<button class="button danger" data-delete-host="' + esc(host.id) + '">' + esc(t("delete")) + '</button>' : '') +
      '</div></div>').join("") + '</div>';
    $("#rules-table").innerHTML = '<div class="mini-list">' + state.rules.map(rule =>
      '<div class="mini-row"><div class="grow"><strong>' + esc(rule.name) + (rule.enabled ? "" : " · " + t("disabled")) + '</strong><div class="muted">' + esc(rule.metric_key) + ' ' + esc(rule.operator) + ' ' + esc(rule.warning) + ' / ' + esc(rule.critical) + '</div></div>' + (manage ? '<button class="button secondary" data-edit-rule="' + esc(rule.id) + '">' + esc(t("edit")) + '</button>' + (rule.enabled ? '<button class="button danger" data-delete-rule="' + esc(rule.id) + '">' + esc(t("disable")) + '</button>' : '') : '') + '</div>').join("") + '</div>';
    $("#channels-table").innerHTML = '<div class="mini-list">' + state.channels.map(channel =>
      '<div class="mini-row"><div class="grow"><strong>' + esc(channel.name) + '</strong><div class="muted">' + esc(channel.channel_type) + ' · ' + (channel.enabled ? t("enabled") : t("disabled")) + '</div></div>' + (manage ? '<button class="button secondary" data-test-channel="' + esc(channel.id) + '">' + esc(t("testSent")) + '</button><button class="button secondary" data-edit-channel="' + esc(channel.id) + '">' + esc(t("edit")) + '</button><button class="button danger" data-delete-channel="' + esc(channel.id) + '">×</button>' : '') + '</div>').join("") + '</div>';
    $("#user-management-panel").hidden = !manage;
    $("#users-table").innerHTML = '<div class="mini-list">' + state.users.map(user =>
      '<div class="mini-row"><div class="grow"><strong>' + esc(user.username) + (user.id === state.user.id ? ' <span class="muted">(' + esc(t("you")) + ')</span>' : '') + '</strong><div class="muted">' + esc(user.role.replace("_", " ")) + ' · ' + (user.is_active ? t("enabled") : t("disabled")) + '</div></div>' + (user.id === state.user.id ? '' : '<button class="button secondary" data-edit-user="' + esc(user.id) + '">' + esc(t("manage")) + '</button>') + '</div>').join("") + '</div>';
    bindSettingsActions();
  }

  function bindSettingsActions() {
    $("#hosts-table").querySelectorAll("[data-edit-host]").forEach(button => button.onclick = () => openHostForm(hostById(button.dataset.editHost)));
    $("#hosts-table").querySelectorAll("[data-host-poll]").forEach(button => button.onclick = () => pollHost(button.dataset.hostPoll));
    $("#hosts-table").querySelectorAll("[data-maintenance]").forEach(button => button.onclick = async () => {
      try { await api("/api/hosts/" + button.dataset.maintenance + "/maintenance", {method: "POST", body: JSON.stringify({enabled: button.dataset.enabled === "true"})}); await loadAll(); }
      catch (error) { toast(error.message, "error"); }
    });
    $("#hosts-table").querySelectorAll("[data-delete-host]").forEach(button => button.onclick = async () => {
      const host = hostById(button.dataset.deleteHost);
      if (!confirm(t("deleteHostConfirm", {name: host.name}))) return;
      try { await api("/api/hosts/" + encodeURIComponent(host.id), {method: "DELETE"}); await loadAll(); toast(t("hostDeleted")); }
      catch (error) { toast(error.message, "error"); }
    });
    $("#rules-table").querySelectorAll("[data-edit-rule]").forEach(button => button.onclick = () => openRuleForm(state.rules.find(rule => rule.id === button.dataset.editRule)));
    $("#rules-table").querySelectorAll("[data-delete-rule]").forEach(button => button.onclick = async () => {
      if (!confirm(t("deleteRuleConfirm"))) return;
      try { await api("/api/rules/" + button.dataset.deleteRule, {method: "DELETE"}); await loadAll(); toast(t("ruleDeleted")); }
      catch (error) { toast(error.message, "error"); }
    });
    $("#channels-table").querySelectorAll("[data-test-channel]").forEach(button => button.onclick = async () => {
      try {
        const channel = state.channels.find(item => item.id === button.dataset.testChannel);
        if (channel?.channel_type === "web_audio") { await NocAudio.test(); toast(t("audioPlayed")); return; }
        const result = await api("/api/channels/" + button.dataset.testChannel + "/test", {method: "POST"});
        toast(result.ok ? t("testSent") : translateServerMessage(result.error) || t("notificationFailed"), result.ok ? "success" : "error");
      }
      catch (error) { toast(error.message, "error"); }
    });
    $("#channels-table").querySelectorAll("[data-edit-channel]").forEach(button => button.onclick = () => openChannelForm(state.channels.find(channel => channel.id === button.dataset.editChannel)));
    $("#channels-table").querySelectorAll("[data-delete-channel]").forEach(button => button.onclick = async () => {
      if (!confirm(t("deleteChannelConfirm"))) return;
      try { await api("/api/channels/" + button.dataset.deleteChannel, {method: "DELETE"}); await loadAll(); }
      catch (error) { toast(error.message, "error"); }
    });
    $("#users-table").querySelectorAll("[data-edit-user]").forEach(button => button.onclick = () => openUserForm(state.users.find(user => user.id === button.dataset.editUser)));
  }

  async function pollHost(id) {
    try {
      await api("/api/hosts/" + encodeURIComponent(id) + "/poll", {method: "POST"});
      await loadAll();
      toast(t("pollCompleted"));
    } catch (error) { toast(error.message, "error"); }
  }

  function field(label, name, value = "", type = "text", extra = "") {
    return '<div class="field"><label for="f-' + esc(name) + '">' + esc(label) + '</label><input id="f-' + esc(name) + '" name="' + esc(name) + '" type="' + esc(type) + '" value="' + esc(value) + '" ' + extra + '></div>';
  }

  function selectField(label, name, values, selected) {
    return '<div class="field"><label for="f-' + esc(name) + '">' + esc(label) + '</label><select id="f-' + esc(name) + '" name="' + esc(name) + '">' +
      values.map(value => '<option value="' + esc(value[0]) + '"' + (value[0] === selected ? " selected" : "") + '>' + esc(value[1]) + '</option>').join("") + '</select></div>';
  }

  function checkbox(label, name, checked) {
    return '<label class="checkbox-row"><input type="checkbox" name="' + esc(name) + '"' + (checked ? " checked" : "") + '>' + esc(label) + '</label>';
  }

  function renderHostConfig(type, cfg) {
    cfg = cfg || {};
    const text = (key, fallback = "") => Array.isArray(cfg[key]) ? cfg[key].join(", ") : (cfg[key] ?? fallback);
    if (type === "local") return '<div class="form-grid">' +
      field(t("windowsServiceNames"), "services", text("windows_services", "EventLog,LanmanServer,Dnscache,Winmgmt,Schedule,W32Time,Spooler"), "text", 'class="wide"') +
      field(t("tcpPorts"), "ports", text("tcp_ports"), "text") + field(t("httpUrls"), "urls", text("http_urls"), "text") +
      field(t("eventLogChannels"), "eventlogs", text("eventlog_channels", "System,Application"), "text") + '</div>';
    if (type === "agent") return '<div class="form-grid">' +
      selectField(t("agentTransport"), "mode", [["push",t("pushRecommended")],["pull",t("pull")]], cfg.mode || "push") +
      field(t("agentToken"), "agent_token", cfg.agent_token || "", "password", 'autocomplete="new-password"') +
      field(t("pullUrl"), "pull_url", cfg.pull_url || "", "text") + field(t("agentPort"), "port", cfg.port || 9108, "number") +
      field(t("windowsServices"), "services", text("windows_services"), "text") + field(t("tcpPorts"), "ports", text("tcp_ports"), "text") +
      field(t("httpUrls"), "urls", text("http_urls"), "text") + '</div>';
    if (type === "snmp") {
      const v3 = cfg.v3 || {};
      return '<div class="form-grid">' +
        selectField(t("snmpVersion"), "version", [["1","v1"],["2c","v2c"],["3","v3"]], cfg.version || "2c") +
        field(t("udpPort"), "port", cfg.port || 161, "number") + field(t("community"), "community", cfg.community || "", "password", 'autocomplete="new-password"') +
        selectField(t("oidProfile"), "oid_profile", [["windows_snmp","Windows SNMP"],["linux_snmpd","Linux net-snmp"],["netgear_generic","Generic network"],["mikrotik","MikroTik"],["cisco","Cisco"],["fortinet","Fortinet"],["huawei","Huawei"],["hpe_aruba","HPE / Aruba"]], cfg.oid_profile || "netgear_generic") +
        field(t("customCpuOid"), "cpu_vendor_oid", cfg.cpu_vendor_oid || "") + field(t("walkTimeout"), "walk_timeout_sec", cfg.walk_timeout_sec || 2, "number", 'step="0.1"') +
        field(t("excludedInterfaces"), "if_exclude", text("if_exclude", "lo")) +
        field(t("snmpUser"), "v3_user", v3.user || "") + selectField(t("snmpAuth"), "v3_auth_proto", [["SHA","SHA"],["MD5","MD5"],["SHA224","SHA-224"],["SHA256","SHA-256"],["SHA384","SHA-384"],["SHA512","SHA-512"]], v3.auth_proto || "SHA") +
        field(t("authKey"), "v3_auth_key", v3.auth_key || "", "password", 'autocomplete="new-password"') +
        selectField(t("snmpPrivacy"), "v3_priv_proto", [["AES","AES"],["DES","DES"],["AES192","AES-192"],["AES256","AES-256"]], v3.priv_proto || "AES") +
        field(t("privacyKey"), "v3_priv_key", v3.priv_key || "", "password", 'autocomplete="new-password"') + '</div>';
    }
    return '<div class="form-grid">' + checkbox(t("icmpPing"), "icmp", cfg.icmp !== false) +
      checkbox(t("checkSsl"), "ssl_check", cfg.ssl_check !== false) +
      field(t("tcpPorts"), "ports", text("tcp_ports"), "text") + field(t("httpUrls"), "urls", text("http_urls"), "text") +
      field(t("expectedStatuses"), "expected_status", text("expected_status", "200,204,301,302"), "text") +
      field(t("bodyMatch"), "body_match", cfg.body_match || "") + field(t("sslWarningDays"), "ssl_warn_days", cfg.ssl_warn_days || 30, "number") +
      field(t("sslCriticalDays"), "ssl_crit_days", cfg.ssl_crit_days || 7, "number") + '</div>';
  }

  function splitList(value, numeric = false) {
    return value.split(",").map(item => item.trim()).filter(Boolean).map(item => numeric ? Number(item) : item);
  }

  function readHostConfig(form, type) {
    const get = name => form.elements[name];
    if (type === "local") return {windows_services: splitList(get("services").value), tcp_ports: splitList(get("ports").value, true), http_urls: splitList(get("urls").value), eventlog_channels: splitList(get("eventlogs").value)};
    if (type === "agent") return {mode: get("mode").value, pull_url: get("pull_url").value || null, port: Number(get("port").value || 9108), agent_token: get("agent_token").value || "", windows_services: splitList(get("services").value), tcp_ports: splitList(get("ports").value, true), http_urls: splitList(get("urls").value)};
    if (type === "snmp") return {
      version: get("version").value, port: Number(get("port").value || 161), community: get("community").value,
      oid_profile: get("oid_profile").value, cpu_vendor_oid: get("cpu_vendor_oid").value, walk_timeout_sec: Number(get("walk_timeout_sec").value || 2), if_exclude: splitList(get("if_exclude").value),
      v3: {user: get("v3_user").value, auth_proto: get("v3_auth_proto").value, auth_key: get("v3_auth_key").value, priv_proto: get("v3_priv_proto").value, priv_key: get("v3_priv_key").value}
    };
    return {
      icmp: get("icmp").checked, ssl_check: get("ssl_check").checked, tcp_ports: splitList(get("ports").value, true), http_urls: splitList(get("urls").value),
      expected_status: splitList(get("expected_status").value, true), body_match: get("body_match").value || null,
      ssl_warn_days: Number(get("ssl_warn_days").value || 30), ssl_crit_days: Number(get("ssl_crit_days").value || 7)
    };
  }

  function openHostForm(host) {
    const form = $("#host-form");
    const config = host?.config || {};
    const hostTypes = host?.id === "local"
      ? [["local",t("localNocServer")]]
      : [["agent",t("remoteAgent")],["snmp","SNMP"],["ping_http",t("pingHttp")]];
    form.innerHTML = '<h2>' + (host ? t("editHost") : t("addMonitoredHost")) + '</h2><p class="subheading">' + t("hostConfiguration") + '</p>' +
      '<div class="form-grid">' + field(t("displayName"), "name", host?.name || "") + field(t("hostnameIp"), "hostname", host?.hostname || "") +
      selectField(t("monitoringType"), "host_type", hostTypes, host?.host_type || "ping_http") +
      field(t("pollInterval"), "poll_interval_sec", host?.poll_interval_sec || 15, "number") + '</div>' + checkbox(t("pollingEnabled"), "enabled", host ? host.enabled : true) + '<div id="host-config-fields">' + renderHostConfig(host?.host_type || "ping_http", config) + '</div>' +
      '<div class="modal-actions"><button class="button secondary" type="button" data-cancel>' + t("cancel") + '</button><button class="button primary" type="submit">' + t("saveHost") + '</button></div>';
    $("#host-dialog").showModal();
    form.querySelector('[name="host_type"]').onchange = event => { $("#host-config-fields").innerHTML = renderHostConfig(event.target.value, {}); };
    form.querySelector("[data-cancel]").onclick = () => $("#host-dialog").close();
    form.onsubmit = async event => {
      event.preventDefault();
      const type = form.elements.host_type.value;
      const body = {name: form.elements.name.value.trim(), hostname: form.elements.hostname.value.trim(), host_type: type, poll_interval_sec: Number(form.elements.poll_interval_sec.value || 15), enabled: form.elements.enabled.checked, tags: host?.tags || [], config: readHostConfig(form, type)};
      if (type === "agent" && !body.config.agent_token) body.config.agent_token = randomToken();
      try {
        if (host) await api("/api/hosts/" + encodeURIComponent(host.id), {method: "PUT", body: JSON.stringify(body)});
        else await api("/api/hosts", {method: "POST", body: JSON.stringify(body)});
        await loadAll();
        if (!host && type === "agent" && body.config.mode === "push") showAgentCommand(body.config.agent_token, body.config.windows_services);
        else $("#host-dialog").close();
        toast(host ? t("hostUpdated") : t("hostAdded"));
      } catch (error) { toast(error.message, "error"); }
    };
  }

  function randomToken() {
    const values = new Uint8Array(24);
    crypto.getRandomValues(values);
    return [...values].map(value => value.toString(16).padStart(2, "0")).join("");
  }

  function showAgentCommand(token, services = []) {
    const localAddress = ["localhost", "127.0.0.1", "::1"].includes(location.hostname);
    const origin = localAddress ? "http://NOC_SERVER_IP:" + (location.port || "6969") : location.origin;
    const serviceArg = services.length ? ' --services "' + services.join(",") + '"' : "";
    const command = 'python run_agent.py --push-url "' + origin + '/api/agent/push" --token ' + token + serviceArg;
    $("#host-form").innerHTML = '<h2>' + t("agentCreated") + '</h2><p class="subheading">' + t("agentCreatedSubtitle") + '</p><div class="field"><label>' + t("runOnServer") + '</label><textarea id="agent-command" readonly></textarea></div><div class="modal-actions"><button class="button secondary" type="button" id="copy-agent-command">' + t("copyCommand") + '</button><button class="button primary" type="button" id="close-agent-command">' + t("done") + '</button></div>';
    $("#agent-command").value = command;
    $("#copy-agent-command").onclick = async () => { await navigator.clipboard.writeText(command); toast(t("commandCopied")); };
    $("#close-agent-command").onclick = () => $("#host-dialog").close();
  }

  function openRuleForm(rule) {
    const form = $("#rule-form");
    const metrics = Object.keys(window.NOC_CATALOG || {});
    form.innerHTML = '<h2>' + (rule ? t("editAlertRule") : t("newAlertRule")) + '</h2><p class="subheading">' + t("ruleSubtitle") + '</p><div class="form-grid">' +
      field(t("ruleName"), "name", rule?.name || "") + selectField(t("metric"), "metric_key", metrics.map(key => [key, key]), rule?.metric_key || metrics[0]) +
      selectField(t("operator"), "operator", [[">",">"],[">=","≥"],["<","<"],["<=","≤"],["==","="],["!=","≠"]], rule?.operator || ">") +
      field(t("warningThreshold"), "warning", rule?.warning ?? "") + field(t("criticalThreshold"), "critical", rule?.critical ?? "") +
      field(t("consecutivePolls"), "consecutive_polls", rule?.consecutive_polls || 1, "number") + field(t("cooldown"), "cooldown_sec", rule?.cooldown_sec ?? 300, "number") +
      '</div><div class="modal-actions"><button class="button secondary" type="button" data-cancel>' + t("cancel") + '</button><button class="button primary" type="submit">' + t("saveRule") + '</button></div>';
    $("#rule-dialog").showModal();
    form.querySelector("[data-cancel]").onclick = () => $("#rule-dialog").close();
    form.onsubmit = async event => {
      event.preventDefault();
      const body = {name: form.elements.name.value.trim(), metric_key: form.elements.metric_key.value, operator: form.elements.operator.value, warning: optionalNumber(form.elements.warning.value), critical: optionalNumber(form.elements.critical.value), consecutive_polls: Number(form.elements.consecutive_polls.value || 1), cooldown_sec: Number(form.elements.cooldown_sec.value || 0), enabled: true};
      try {
        await api(rule ? "/api/rules/" + rule.id : "/api/rules", {method: rule ? "PUT" : "POST", body: JSON.stringify(body)});
        $("#rule-dialog").close(); await loadAll(); toast(t("ruleSaved"));
      } catch (error) { toast(error.message, "error"); }
    };
  }

  function optionalNumber(value) { return value === "" ? null : Number(value); }

  function openChannelForm(channel) {
    const form = $("#channel-form");
    const cfg = channel?.config || {};
    const type = channel?.channel_type || "web_audio";
    form.innerHTML = '<h2>' + (channel ? t("editChannel") : t("addChannelTitle")) + '</h2><p class="subheading">' + t("channelSubtitle") + '</p>' +
      '<div class="form-grid">' + field(t("displayName"), "name", channel?.name || "") + selectField(t("channelType"), "channel_type", [["web_audio",t("dashboardAudio")],["telegram","Telegram"],["webhook","Webhook"],["smtp",t("emailSmtp")]], type) + '</div>' +
      '<div id="channel-fields"></div><div class="modal-actions"><button class="button secondary" type="button" data-cancel>' + t("cancel") + '</button><button class="button primary" type="submit">' + t("saveHost") + '</button></div>';
    const renderFields = (selected, values) => {
      if (selected === "telegram") return '<div class="form-grid">' + field(t("botToken"), "bot_token", values.bot_token || "", "password", 'autocomplete="new-password"') + field(t("chatId"), "chat_id", values.chat_id || "") + '</div>';
      if (selected === "webhook") return '<div class="form-grid"><div class="field full"><label>' + t("webhookUrl") + '</label><input name="url" value="' + esc(values.url || "") + '"></div><div class="field full"><label>' + t("optionalHeaders") + '</label><textarea name="headers">' + esc(JSON.stringify(values.headers || {}, null, 2)) + '</textarea></div></div>';
      if (selected === "smtp") return '<div class="form-grid">' + field(t("smtpHost"), "host", values.host || "") + field(t("port"), "port", values.port || 587, "number") + field(t("from"), "from", values.from || "") + field(t("to"), "to", values.to || "") + field(t("username"), "username", values.username || "") + field(t("password"), "password", values.password || "", "password", 'autocomplete="new-password"') + '</div>' + checkbox(t("startTls"), "start_tls", values.start_tls !== false) + checkbox(t("implicitTls"), "use_tls", Boolean(values.use_tls));
      return '<div class="notice">' + t("alarmAudioNotice") + '</div>';
    };
    $("#channel-fields").innerHTML = renderFields(type, cfg);
    $("#channel-dialog").showModal();
    form.elements.channel_type.onchange = event => { $("#channel-fields").innerHTML = renderFields(event.target.value, {}); };
    form.querySelector("[data-cancel]").onclick = () => $("#channel-dialog").close();
    form.onsubmit = async event => {
      event.preventDefault();
      const selected = form.elements.channel_type.value;
      const get = name => form.elements[name];
      let config = {};
      if (selected === "telegram") config = {bot_token: get("bot_token").value, chat_id: get("chat_id").value};
      if (selected === "webhook") {
        try { config = {url: get("url").value, headers: JSON.parse(get("headers").value || "{}")}; }
        catch { toast(t("webhookJsonError"), "error"); return; }
      }
      if (selected === "smtp") config = {host: get("host").value, port: Number(get("port").value || 587), from: get("from").value, to: get("to").value, username: get("username").value, password: get("password").value, start_tls: get("start_tls").checked, use_tls: get("use_tls").checked};
      try {
        await api("/api/channels/" + (channel?.id || "new"), {method: "PUT", body: JSON.stringify({name: get("name").value.trim(), channel_type: selected, enabled: true, config})});
        $("#channel-dialog").close(); await loadAll(); toast(t("channelSaved"));
      } catch (error) { toast(error.message, "error"); }
    };
  }

  function switchPage(page) {
    state.page = page;
    document.querySelectorAll(".nav-item").forEach(button => button.classList.toggle("active", button.dataset.page === page));
    document.querySelectorAll(".page").forEach(section => section.classList.toggle("active", section.id === page + "-page"));
    $("#page-title").textContent = t(titleByPage[page]);
  }

  function openUserForm(user) {
    const form = $("#user-form");
    const roles = state.user.role === "global_admin" ? ["global_admin", "admin", "operator", "viewer"] : ["operator", "viewer"];
    const roleOptions = roles.map(role => [role, role.replace("_", " ")]);
    form.innerHTML = '<h2>' + (user ? t("manageUser") : t("createUser")) + '</h2><p class="subheading">' + t("passwordRule") + '</p>' +
      '<div class="form-grid">' + field(t("username"), "username", user?.username || "") + selectField(t("accessLevel"), "role", roleOptions, user?.role || roles[roles.length - 1]) +
      field(user ? t("resetPassword") : t("initialPassword"), "password", "", "password", 'autocomplete="new-password" minlength="8" maxlength="128"' ) + '</div>' +
      (user ? checkbox(t("accountActive"), "is_active", Boolean(user.is_active)) : '') +
      '<div class="modal-actions"><button class="button secondary" type="button" data-cancel>' + t("cancel") + '</button><button class="button primary" type="submit">' + t("saveUser") + '</button></div>';
    $("#user-dialog").showModal();
    form.querySelector("[data-cancel]").onclick = () => $("#user-dialog").close();
    form.onsubmit = async event => {
      event.preventDefault();
      const body = {username: form.elements.username.value.trim(), role: form.elements.role.value};
      if (user) body.is_active = form.elements.is_active.checked;
      if (form.elements.password.value) body.password = form.elements.password.value;
      if (!user && !body.password) { toast(t("initialPasswordRequired"), "error"); return; }
      try {
        await api(user ? "/api/auth/users/" + encodeURIComponent(user.id) : "/api/auth/users", {method: user ? "PUT" : "POST", body: JSON.stringify(body)});
        $("#user-dialog").close();
        await loadAll();
        toast(user ? t("userUpdated") : t("userCreated"));
      } catch (error) { toast(error.message, "error"); }
    };
  }

  function openPasswordForm() {
    const form = $("#password-form");
    form.innerHTML = '<h2>' + t("changePassword") + '</h2><p class="subheading">' + t("changePasswordSubtitle") + '</p>' +
      '<div class="form-grid">' + field(t("currentPassword"), "current_password", "", "password", 'autocomplete="current-password" required maxlength="128"') +
      field(t("newPassword"), "new_password", "", "password", 'autocomplete="new-password" required minlength="8" maxlength="128"') + '</div>' +
      '<div class="modal-actions"><button class="button secondary" type="button" data-cancel>' + t("cancel") + '</button><button class="button primary" type="submit">' + t("changePassword") + '</button></div>';
    $("#password-dialog").showModal();
    form.querySelector("[data-cancel]").onclick = () => $("#password-dialog").close();
    form.onsubmit = async event => {
      event.preventDefault();
      try {
        await api("/api/auth/change-password", {method: "POST", body: JSON.stringify({current_password: form.elements.current_password.value, new_password: form.elements.new_password.value})});
        $("#password-dialog").close();
        toast(t("passwordChanged"));
      } catch (error) { toast(error.message, "error"); }
    };
  }

  document.querySelectorAll(".nav-item").forEach(button => button.addEventListener("click", () => switchPage(button.dataset.page)));
  ["vi", "en"].forEach(code => $("#lang-" + code).addEventListener("click", () => setLanguage(code)));
  $("#host-filter").addEventListener("input", renderWallboard);
  $("#incident-filter").addEventListener("change", renderIncidents);
  $("#add-host").onclick = () => openHostForm(null);
  $("#add-host-settings").onclick = () => openHostForm(null);
  $("#add-rule").onclick = () => openRuleForm(null);
  $("#add-channel").onclick = () => openChannelForm(null);
  $("#add-user").onclick = () => openUserForm(null);
  $("#account-button").onclick = openPasswordForm;
  $("#logout-button").onclick = async () => {
    try { await api("/api/auth/logout", {method: "POST"}); } finally { location.replace("/login"); }
  };
  $("#audio-toggle").onclick = async () => {
      try { await NocAudio.toggle(); $("#audio-toggle").textContent = NocAudio.enabled ? t("audioDisable") : t("audioEnable"); NocAudio.update(state.incidents); }
    catch { toast(t("audioError"), "error"); }
  };
  $("#fullscreen").onclick = () => document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen?.();
  $("#host-drawer").addEventListener("click", event => { if (event.target === $("#host-drawer")) closeDrawer(); });
  document.addEventListener("keydown", event => { if (event.key === "Escape") closeDrawer(); });
  window.NOC_CATALOG = {};
  setInterval(() => { $("#clock").textContent = new Date().toLocaleString(language === "vi" ? "vi-VN" : "en-US"); }, 1000);
  if (NocAudio.enabled) $("#audio-toggle").textContent = t("audioDisable");
  applyLanguage();
  (async () => {
    try {
      state.user = await api("/api/auth/me");
      await loadAll();
      connect();
      setInterval(loadAll, 30000);
    } catch (error) { toast(error.message, "error"); }
  })();
})();
