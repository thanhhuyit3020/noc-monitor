(() => {
  const $ = selector => document.querySelector(selector);
  const state = {hosts: [], snapshots: [], incidents: [], rules: [], channels: [], page: "wallboard", socket: null, retry: 500};
  const titleByPage = {wallboard: "Wallboard", incidents: "Incidents", settings: "Configuration"};
  const esc = value => String(value ?? "").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
  const stamp = value => value ? new Date(value * 1000).toLocaleString() : "—";
  const num = (value, digits = 1) => value === null || value === undefined || Number.isNaN(Number(value)) ? "—" : Number(value).toFixed(digits);
  const pctClass = value => Number(value) >= 95 ? "crit" : Number(value) >= 80 ? "warn" : "";
  const hostById = id => state.hosts.find(host => host.id === id);

  async function api(path, options = {}) {
    const response = await fetch(path, {headers: {"Content-Type": "application/json", ...(options.headers || {})}, ...options});
    if (!response.ok) {
      let message = response.statusText;
      try { const body = await response.json(); message = body.detail || message; } catch {}
      throw new Error(message);
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
      $("#connection-state").textContent = "Live connection";
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
    socket.onclose = () => {
      clearInterval(state.heartbeat);
      $("#connection-state").textContent = "Reconnecting";
      $("#ws-indicator").className = "status-dot disconnected";
      const delay = state.retry;
      state.retry = Math.min(15000, state.retry * 1.7);
      setTimeout(connect, delay);
    };
    socket.onerror = () => socket.close();
  }

  function render() {
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
      summaryCard("HOSTS ONLINE", up + " / " + hosts.length, "monitored") +
      summaryCard("OPEN INCIDENTS", String(open), critical ? critical + " critical" : "all clear") +
      summaryCard("AVG CPU", num(avgCpu) + "%", "fleet telemetry") +
      summaryCard("POLLING", "LIVE", "WebSocket stream");
    const query = $("#host-filter").value.trim().toLowerCase();
    const filtered = hosts.filter(host => (host.name + " " + host.hostname + " " + host.host_type).toLowerCase().includes(query));
    $("#host-grid").innerHTML = filtered.length ? filtered.map(renderHostCard).join("") : '<div class="empty-state">No hosts match this filter.</div>';
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
      '</div><div class="host-card-footer"><span>' + esc(host.os_info || host.status_reason || "Awaiting first sample") + '</span><span>' + esc(stamp(host.last_seen_at || host.ts)) + '</span></div></article>';
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
    drawer.innerHTML =
      '<div class="drawer-header"><div><h2>' + esc(host.name) + '</h2><p>' + esc(host.hostname) + ' · ' + esc(host.host_type) + ' · ' + esc(host.status) + '</p></div>' +
      '<div class="drawer-actions">' + (host.host_type === "agent" && config.mode !== "pull" ? "" : '<button class="button secondary" data-drawer-poll="' + esc(hostId) + '">Poll now</button>') + '<button class="button secondary" data-close-drawer>✕</button></div></div>' +
      '<div class="section-title">Performance history</div><div class="chart-tools"><select id="chart-metric" class="select"><option value="cpu.total_pct">CPU</option><option value="ram.used_pct">RAM</option><option value="ping.latency_ms">Latency</option></select><select id="chart-range" class="select"><option>1h</option><option>6h</option><option>24h</option><option>7d</option><option>30d</option></select></div><div id="host-chart" class="chart-box"></div>' +
      '<div class="section-title">Core sensors</div><div class="detail-grid">' +
      detailCell("CPU", num(metricValue(host, "cpu.total_pct")) + "%") +
      detailCell("RAM", num(metricValue(host, "ram.used_pct")) + "%") +
      detailCell("Packet loss", num(metricValue(host, "ping.packet_loss_pct")) + "%") +
      detailCell("Event errors / h", num(metricValue(host, "eventlog.crit_err_1h"), 0)) +
      detailCell("Uptime", formatDuration(metricValue(host, "system.uptime_sec"))) +
      detailCell("TCP established", num(metricValue(host, "tcp.established"), 0)) +
      '</div>' +
      '<div class="section-title">Per-core CPU</div>' + detailTable(["Core", "Usage"], (host.snapshot?.metrics || []).filter(metric => metric.key === "cpu.core_pct").map(metric => [metric.resource_key, num(metric.value) + "%"])) +
      '<div class="section-title">Disks</div>' + detailTable(["Volume", "Mount", "Used", "Free"], (detail.disks || detail.storage || []).map(item => [item.name, item.mountpoint || item.type_oid || "", item.used_pct === undefined ? bytes(item.used_bytes) : num(item.used_pct) + "%", item.free_bytes === undefined ? bytes(Math.max(0, (item.total_bytes || 0) - (item.used_bytes || 0))) : bytes(item.free_bytes)])) +
      '<div class="section-title">Network interfaces</div>' + detailTable(["Interface", "State", "RX", "TX", "Speed", "Errors/s", "Drops/s"], (detail.networks || detail.interfaces || []).map(item => [item.name, item.is_up === undefined ? (item.status === 1 ? "up" : "down") : (item.is_up ? "up" : "down"), rate(item.rx_bps), rate(item.tx_bps), item.speed_mbps == null ? "—" : item.speed_mbps + " Mbps", num(item.errors_per_sec ?? ((item.errin_per_sec || 0) + (item.errout_per_sec || 0))), num(item.drops_per_sec ?? ((item.dropin_per_sec || 0) + (item.dropout_per_sec || 0)))])) +
      '<div class="section-title">Disk I/O</div>' + detailTable(["Device", "Read", "Write", "Read IOPS", "Write IOPS"], (detail.disk_io || []).map(item => [item.name, rate(item.read_bps), rate(item.write_bps), num(item.read_iops), num(item.write_iops)])) +
      '<div class="section-title">TCP states</div>' + detailTable(["State", "Connections"], Object.entries(detail.tcp_states || {}).map(row => row)) +
      '<div class="section-title">Windows services</div>' + detailTable(["Service", "Status", "Startup"], (detail.services || []).map(item => [item.name, item.status, item.start_type])) +
      '<div class="section-title">Top processes by CPU</div>' + detailTable(["PID", "Process", "User", "CPU", "Memory"], ((detail.processes || {}).cpu || []).map(item => [item.pid, item.name, item.user || "", num(item.cpu_pct) + "%", num(item.memory_mb) + " MB"])) +
      '<div class="section-title">Top processes by memory</div>' + detailTable(["PID", "Process", "User", "CPU", "Memory"], ((detail.processes || {}).memory || []).map(item => [item.pid, item.name, item.user || "", num(item.cpu_pct) + "%", num(item.memory_mb) + " MB"])) +
      '<div class="section-title">Recent Windows errors</div>' + detailTable(["Time", "Channel", "ID", "Source", "Message"], (detail.event_logs || []).map(item => [item.time, item.channel, item.event_id, item.source, item.message])) +
      '<div class="section-title">TCP / HTTP / TLS probes</div>' + detailTable(["Target", "State / status", "Latency", "SSL days"], (detail.ports || []).map(item => [":" + item.port, item.up ? "up" : "down", num(item.response_ms) + " ms", "—"]).concat((detail.http || []).map(item => [item.url, item.status_code ?? "failed", num(item.response_ms) + " ms", item.ssl_days_remaining === null ? "—" : num(item.ssl_days_remaining) + "d"]))) +
      '<div class="section-title">Status detail</div><div class="muted small">' + esc(host.status_reason || "—") + '</div>';
    drawer.querySelector("[data-close-drawer]").onclick = closeDrawer;
    drawer.querySelector("[data-drawer-poll]").onclick = () => pollHost(hostId);
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
    if (!rows.length) return '<div class="muted small">No data available.</div>';
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
    return days + "d " + hours + "h";
  }

  function renderIncidents() {
    const filter = $("#incident-filter").value;
    const rows = state.incidents.filter(item => !filter || item.state === filter);
    $("#incidents-table").innerHTML = rows.length ? rows.map(item =>
      '<tr><td><span class="severity ' + esc(item.severity) + '">' + esc(item.severity) + '</span></td><td><strong>' + esc(item.message) + '</strong></td><td>' + esc(item.host_name || hostById(item.host_id)?.name || item.host_id) + '</td><td>' + esc(item.resource_key || "—") + '</td><td><span class="state-badge state-' + esc(item.state) + '">' + esc(item.state) + '</span></td><td>' + esc(stamp(item.updated_at)) + '</td><td><div class="table-actions">' +
      (item.state === "OPEN" ? '<button class="button secondary" data-ack="' + esc(item.id) + '">ACK</button>' : '') +
      (item.state !== "RESOLVED" ? '<button class="button secondary" data-resolve="' + esc(item.id) + '">Resolve</button>' : '') +
      '</div></td></tr>').join("") : '<tr><td colspan="7" class="muted">No incidents.</td></tr>';
    $("#incidents-table").querySelectorAll("[data-ack]").forEach(button => button.onclick = () => incidentAction(button.dataset.ack, "ack"));
    $("#incidents-table").querySelectorAll("[data-resolve]").forEach(button => button.onclick = () => incidentAction(button.dataset.resolve, "resolve"));
    $("#incident-count").textContent = state.incidents.filter(item => item.state === "OPEN").length;
    NocAudio.update(activeIncidents());
  }

  async function incidentAction(id, action) {
    try {
      await api("/api/incidents/" + encodeURIComponent(id) + "/" + action, {method: "POST"});
      await loadAll();
      toast(action === "ack" ? "Incident acknowledged" : "Incident resolved");
    } catch (error) { toast(error.message, "error"); }
  }

  function renderSettings() {
    $("#hosts-table").innerHTML = '<div class="mini-list">' + state.hosts.map(host =>
      '<div class="mini-row"><div class="grow"><strong>' + esc(host.name) + '</strong><div class="muted">' + esc(host.hostname) + ' · ' + esc(host.host_type) + '</div></div><span class="host-badge badge-' + esc(host.status) + '">' + esc(host.status) + '</span><div class="table-actions"><button class="button secondary" data-edit-host="' + esc(host.id) + '">Edit</button>' + (host.host_type === "agent" && host.config?.mode !== "pull" ? "" : '<button class="button secondary" data-host-poll="' + esc(host.id) + '">Poll</button>') +
      (host.id !== "local" ? '<button class="button secondary" data-maintenance="' + esc(host.id) + '" data-enabled="' + (host.status === "maintenance" ? "false" : "true") + '">' + (host.status === "maintenance" ? "Resume" : "Maintain") + '</button><button class="button danger" data-delete-host="' + esc(host.id) + '">Delete</button>' : '') +
      '</div></div>').join("") + '</div>';
    $("#rules-table").innerHTML = '<div class="mini-list">' + state.rules.map(rule =>
      '<div class="mini-row"><div class="grow"><strong>' + esc(rule.name) + (rule.enabled ? "" : " · disabled") + '</strong><div class="muted">' + esc(rule.metric_key) + ' ' + esc(rule.operator) + ' ' + esc(rule.warning) + ' / ' + esc(rule.critical) + '</div></div><button class="button secondary" data-edit-rule="' + esc(rule.id) + '">Edit</button>' + (rule.enabled ? '<button class="button danger" data-delete-rule="' + esc(rule.id) + '">Disable</button>' : '') + '</div>').join("") + '</div>';
    $("#channels-table").innerHTML = '<div class="mini-list">' + state.channels.map(channel =>
      '<div class="mini-row"><div class="grow"><strong>' + esc(channel.name) + '</strong><div class="muted">' + esc(channel.channel_type) + ' · ' + (channel.enabled ? "enabled" : "disabled") + '</div></div><button class="button secondary" data-test-channel="' + esc(channel.id) + '">Test</button><button class="button secondary" data-edit-channel="' + esc(channel.id) + '">Edit</button><button class="button danger" data-delete-channel="' + esc(channel.id) + '">×</button></div>').join("") + '</div>';
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
      if (!confirm("Delete host " + host.name + ", its stored metrics, and its incident history?")) return;
      try { await api("/api/hosts/" + encodeURIComponent(host.id), {method: "DELETE"}); await loadAll(); toast("Host deleted"); }
      catch (error) { toast(error.message, "error"); }
    });
    $("#rules-table").querySelectorAll("[data-edit-rule]").forEach(button => button.onclick = () => openRuleForm(state.rules.find(rule => rule.id === button.dataset.editRule)));
    $("#rules-table").querySelectorAll("[data-delete-rule]").forEach(button => button.onclick = async () => {
      if (!confirm("Delete this alert rule?")) return;
      try { await api("/api/rules/" + button.dataset.deleteRule, {method: "DELETE"}); await loadAll(); toast("Rule deleted"); }
      catch (error) { toast(error.message, "error"); }
    });
    $("#channels-table").querySelectorAll("[data-test-channel]").forEach(button => button.onclick = async () => {
      try {
        const channel = state.channels.find(item => item.id === button.dataset.testChannel);
        if (channel?.channel_type === "web_audio") { await NocAudio.test(); toast("Audio alarm played"); return; }
        const result = await api("/api/channels/" + button.dataset.testChannel + "/test", {method: "POST"});
        toast(result.ok ? "Test notification sent" : result.error || "Notification failed", result.ok ? "success" : "error");
      }
      catch (error) { toast(error.message, "error"); }
    });
    $("#channels-table").querySelectorAll("[data-edit-channel]").forEach(button => button.onclick = () => openChannelForm(state.channels.find(channel => channel.id === button.dataset.editChannel)));
    $("#channels-table").querySelectorAll("[data-delete-channel]").forEach(button => button.onclick = async () => {
      if (!confirm("Delete this notification channel?")) return;
      try { await api("/api/channels/" + button.dataset.deleteChannel, {method: "DELETE"}); await loadAll(); }
      catch (error) { toast(error.message, "error"); }
    });
  }

  async function pollHost(id) {
    try {
      await api("/api/hosts/" + encodeURIComponent(id) + "/poll", {method: "POST"});
      await loadAll();
      toast("Poll completed");
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
      field("Windows service names", "services", text("windows_services", "EventLog,LanmanServer,Dnscache,Winmgmt,Schedule,W32Time,Spooler"), "text", 'class="wide"') +
      field("TCP ports", "ports", text("tcp_ports"), "text") + field("HTTP URLs", "urls", text("http_urls"), "text") +
      field("Event log channels", "eventlogs", text("eventlog_channels", "System,Application"), "text") + '</div>';
    if (type === "agent") return '<div class="form-grid">' +
      selectField("Agent transport", "mode", [["push","Push (recommended)"],["pull","Pull"]], cfg.mode || "push") +
      field("Agent token", "agent_token", cfg.agent_token || "", "password", 'autocomplete="new-password"') +
      field("Pull URL (optional)", "pull_url", cfg.pull_url || "", "text") + field("Agent port", "port", cfg.port || 9108, "number") +
      field("Windows services", "services", text("windows_services"), "text") + field("TCP ports", "ports", text("tcp_ports"), "text") +
      field("HTTP URLs", "urls", text("http_urls"), "text") + '</div>';
    if (type === "snmp") {
      const v3 = cfg.v3 || {};
      return '<div class="form-grid">' +
        selectField("SNMP version", "version", [["1","v1"],["2c","v2c"],["3","v3"]], cfg.version || "2c") +
        field("UDP port", "port", cfg.port || 161, "number") + field("Community", "community", cfg.community || "", "password", 'autocomplete="new-password"') +
        selectField("OID profile", "oid_profile", [["windows_snmp","Windows SNMP"],["linux_snmpd","Linux net-snmp"],["netgear_generic","Generic network"],["mikrotik","MikroTik"],["cisco","Cisco"],["fortinet","Fortinet"],["huawei","Huawei"],["hpe_aruba","HPE / Aruba"]], cfg.oid_profile || "netgear_generic") +
        field("Custom CPU OID", "cpu_vendor_oid", cfg.cpu_vendor_oid || "") + field("Walk timeout (sec)", "walk_timeout_sec", cfg.walk_timeout_sec || 2, "number", 'step="0.1"') +
        field("Excluded interfaces", "if_exclude", text("if_exclude", "lo")) +
        field("SNMPv3 user", "v3_user", v3.user || "") + selectField("SNMPv3 auth", "v3_auth_proto", [["SHA","SHA"],["MD5","MD5"],["SHA224","SHA-224"],["SHA256","SHA-256"],["SHA384","SHA-384"],["SHA512","SHA-512"]], v3.auth_proto || "SHA") +
        field("SNMPv3 auth key", "v3_auth_key", v3.auth_key || "", "password", 'autocomplete="new-password"') +
        selectField("SNMPv3 privacy", "v3_priv_proto", [["AES","AES"],["DES","DES"],["AES192","AES-192"],["AES256","AES-256"]], v3.priv_proto || "AES") +
        field("SNMPv3 privacy key", "v3_priv_key", v3.priv_key || "", "password", 'autocomplete="new-password"') + '</div>';
    }
    return '<div class="form-grid">' + checkbox("ICMP ping", "icmp", cfg.icmp !== false) +
      checkbox("Check SSL certificate", "ssl_check", cfg.ssl_check !== false) +
      field("TCP ports", "ports", text("tcp_ports"), "text") + field("HTTP / HTTPS URLs", "urls", text("http_urls"), "text") +
      field("Expected HTTP statuses", "expected_status", text("expected_status", "200,204,301,302"), "text") +
      field("Body should contain", "body_match", cfg.body_match || "") + field("SSL warning days", "ssl_warn_days", cfg.ssl_warn_days || 30, "number") +
      field("SSL critical days", "ssl_crit_days", cfg.ssl_crit_days || 7, "number") + '</div>';
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
    form.innerHTML = '<h2>' + (host ? "Edit host" : "Add monitored host") + '</h2><p class="subheading">Host configuration and polling settings</p>' +
      '<div class="form-grid">' + field("Display name", "name", host?.name || "") + field("Hostname / IP", "hostname", host?.hostname || "") +
      selectField("Monitoring type", "host_type", [["local","Local server"],["agent","Remote agent"],["snmp","SNMP"],["ping_http","Ping / TCP / HTTP"]], host?.host_type || "ping_http") +
      field("Poll interval (seconds)", "poll_interval_sec", host?.poll_interval_sec || 15, "number") + '</div>' + checkbox("Polling enabled", "enabled", host ? host.enabled : true) + '<div id="host-config-fields">' + renderHostConfig(host?.host_type || "ping_http", config) + '</div>' +
      '<div class="modal-actions"><button class="button secondary" type="button" data-cancel>Cancel</button><button class="button primary" type="submit">Save host</button></div>';
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
        toast(host ? "Host updated" : "Host added");
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
    const origin = localAddress ? "http://NOC_SERVER_IP:" + (location.port || "8080") : location.origin;
    const serviceArg = services.length ? ' --services "' + services.join(",") + '"' : "";
    const command = 'python run_agent.py --push-url "' + origin + '/api/agent/push" --token ' + token + serviceArg;
    $("#host-form").innerHTML = '<h2>Agent host created</h2><p class="subheading">Copy this command to the remote Windows or Linux server. Keep the token private.</p><div class="field"><label>Run on the monitored server</label><textarea id="agent-command" readonly></textarea></div><div class="modal-actions"><button class="button secondary" type="button" id="copy-agent-command">Copy command</button><button class="button primary" type="button" id="close-agent-command">Done</button></div>';
    $("#agent-command").value = command;
    $("#copy-agent-command").onclick = async () => { await navigator.clipboard.writeText(command); toast("Agent command copied"); };
    $("#close-agent-command").onclick = () => $("#host-dialog").close();
  }

  function openRuleForm(rule) {
    const form = $("#rule-form");
    const metrics = Object.keys(window.NOC_CATALOG || {});
    form.innerHTML = '<h2>' + (rule ? "Edit alert rule" : "New alert rule") + '</h2><p class="subheading">Missing metrics are skipped; rules only evaluate sensors supported by each host.</p><div class="form-grid">' +
      field("Rule name", "name", rule?.name || "") + selectField("Metric", "metric_key", metrics.map(key => [key, key]), rule?.metric_key || metrics[0]) +
      selectField("Operator", "operator", [[">",">"],[">=","≥"],["<","<"],["<=","≤"],["==","="],["!=","≠"]], rule?.operator || ">") +
      field("Warning threshold", "warning", rule?.warning ?? "") + field("Critical threshold", "critical", rule?.critical ?? "") +
      field("Consecutive polls", "consecutive_polls", rule?.consecutive_polls || 1, "number") + field("Cooldown (seconds)", "cooldown_sec", rule?.cooldown_sec ?? 300, "number") +
      '</div><div class="modal-actions"><button class="button secondary" type="button" data-cancel>Cancel</button><button class="button primary" type="submit">Save rule</button></div>';
    $("#rule-dialog").showModal();
    form.querySelector("[data-cancel]").onclick = () => $("#rule-dialog").close();
    form.onsubmit = async event => {
      event.preventDefault();
      const body = {name: form.elements.name.value.trim(), metric_key: form.elements.metric_key.value, operator: form.elements.operator.value, warning: optionalNumber(form.elements.warning.value), critical: optionalNumber(form.elements.critical.value), consecutive_polls: Number(form.elements.consecutive_polls.value || 1), cooldown_sec: Number(form.elements.cooldown_sec.value || 0), enabled: true};
      try {
        await api(rule ? "/api/rules/" + rule.id : "/api/rules", {method: rule ? "PUT" : "POST", body: JSON.stringify(body)});
        $("#rule-dialog").close(); await loadAll(); toast("Rule saved");
      } catch (error) { toast(error.message, "error"); }
    };
  }

  function optionalNumber(value) { return value === "" ? null : Number(value); }

  function openChannelForm(channel) {
    const form = $("#channel-form");
    const cfg = channel?.config || {};
    const type = channel?.channel_type || "web_audio";
    form.innerHTML = '<h2>' + (channel ? "Edit notification channel" : "Add notification channel") + '</h2><p class="subheading">Notification credentials are masked after saving.</p>' +
      '<div class="form-grid">' + field("Display name", "name", channel?.name || "") + selectField("Channel type", "channel_type", [["web_audio","Dashboard audio"],["telegram","Telegram"],["webhook","Webhook"],["smtp","Email SMTP"]], type) + '</div>' +
      '<div id="channel-fields"></div><div class="modal-actions"><button class="button secondary" type="button" data-cancel>Cancel</button><button class="button primary" type="submit">Save channel</button></div>';
    const renderFields = (selected, values) => {
      if (selected === "telegram") return '<div class="form-grid">' + field("Bot token", "bot_token", values.bot_token || "", "password", 'autocomplete="new-password"') + field("Chat ID", "chat_id", values.chat_id || "") + '</div>';
      if (selected === "webhook") return '<div class="form-grid"><div class="field full"><label>Webhook URL</label><input name="url" value="' + esc(values.url || "") + '"></div><div class="field full"><label>Optional headers as JSON</label><textarea name="headers">' + esc(JSON.stringify(values.headers || {}, null, 2)) + '</textarea></div></div>';
      if (selected === "smtp") return '<div class="form-grid">' + field("SMTP host", "host", values.host || "") + field("Port", "port", values.port || 587, "number") + field("From", "from", values.from || "") + field("To", "to", values.to || "") + field("Username", "username", values.username || "") + field("Password", "password", values.password || "", "password", 'autocomplete="new-password"') + '</div>' + checkbox("Use STARTTLS", "start_tls", values.start_tls !== false) + checkbox("Use implicit TLS", "use_tls", Boolean(values.use_tls));
      return '<div class="notice">Alarm audio is played in this dashboard after the user enables browser audio.</div>';
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
        catch { toast("Webhook headers must be valid JSON", "error"); return; }
      }
      if (selected === "smtp") config = {host: get("host").value, port: Number(get("port").value || 587), from: get("from").value, to: get("to").value, username: get("username").value, password: get("password").value, start_tls: get("start_tls").checked, use_tls: get("use_tls").checked};
      try {
        await api("/api/channels/" + (channel?.id || "new"), {method: "PUT", body: JSON.stringify({name: get("name").value.trim(), channel_type: selected, enabled: true, config})});
        $("#channel-dialog").close(); await loadAll(); toast("Channel saved");
      } catch (error) { toast(error.message, "error"); }
    };
  }

  function switchPage(page) {
    state.page = page;
    document.querySelectorAll(".nav-item").forEach(button => button.classList.toggle("active", button.dataset.page === page));
    document.querySelectorAll(".page").forEach(section => section.classList.toggle("active", section.id === page + "-page"));
    $("#page-title").textContent = titleByPage[page];
  }

  document.querySelectorAll(".nav-item").forEach(button => button.addEventListener("click", () => switchPage(button.dataset.page)));
  $("#host-filter").addEventListener("input", renderWallboard);
  $("#incident-filter").addEventListener("change", renderIncidents);
  $("#add-host").onclick = () => openHostForm(null);
  $("#add-host-settings").onclick = () => openHostForm(null);
  $("#add-rule").onclick = () => openRuleForm(null);
  $("#add-channel").onclick = () => openChannelForm(null);
  $("#audio-toggle").onclick = async () => {
    try { await NocAudio.toggle(); $("#audio-toggle").textContent = NocAudio.enabled ? "◖ Âm thanh đang bật · Tắt" : "◖ Bật âm thanh cảnh báo"; NocAudio.update(state.incidents); }
    catch { toast("Audio could not start. Click the button again to allow browser audio.", "error"); }
  };
  $("#fullscreen").onclick = () => document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen?.();
  $("#host-drawer").addEventListener("click", event => { if (event.target === $("#host-drawer")) closeDrawer(); });
  document.addEventListener("keydown", event => { if (event.key === "Escape") closeDrawer(); });
  window.NOC_CATALOG = {};
  setInterval(() => { $("#clock").textContent = new Date().toLocaleString(); }, 1000);
  if (NocAudio.enabled) $("#audio-toggle").textContent = "◖ Âm thanh đã bật · Tắt";
  loadAll();
  connect();
  setInterval(loadAll, 30000);
})();
