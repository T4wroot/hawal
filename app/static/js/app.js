let STATE = {
  nodes: [],
  tunnels: [],
  pings: [],
  settings: {},
  activeTab: 'dashboard',
  currentInstallerToken: '',
  currentInstallerRole: '',
  currentInstallerName: '',
  installerMode: 'native',
  activePortTags: [443, 2083],
  ws: null
};

document.addEventListener('DOMContentLoaded', () => {
  initWebSocket();
  fetchData();
  fetchSettings();
  renderPortChips();
  setInterval(fetchData, 6000);
});

function initWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws`;

  STATE.ws = new WebSocket(wsUrl);
  STATE.ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (['node_updated', 'tunnel_updated', 'node_heartbeat', 'settings_updated'].includes(data.event)) {
        fetchData();
      }
    } catch (e) {}
  };
  STATE.ws.onclose = () => {
    setTimeout(initWebSocket, 3000);
  };
}

async function fetchData() {
  try {
    const [resNodes, resTunnels, resPings] = await Promise.all([
      fetch('/api/nodes').then(r => r.json()),
      fetch('/api/tunnels').then(r => r.json()),
      fetch('/api/pings/latest').then(r => r.json())
    ]);

    STATE.nodes = resNodes.nodes || [];
    STATE.tunnels = resTunnels.tunnels || [];
    STATE.pings = resPings.pings || [];

    renderDashboard();
    renderTopology();
    renderNodes();
    renderTunnels();
    renderPingSelects();
    renderPingHistory();
  } catch (e) {
    console.error("Fetch error:", e);
  }
}

async function fetchSettings() {
  try {
    const res = await fetch('/api/settings').then(r => r.json());
    if (res.settings) {
      STATE.settings = res.settings;
      const pPort = document.getElementById('setting-panel-port');
      const dTrans = document.getElementById('setting-default-transport');
      const dMux = document.getElementById('setting-default-mux');
      const dMtu = document.getElementById('setting-mtu-clamp');
      if (pPort) pPort.value = res.settings.panel_port || 9090;
      if (dTrans) dTrans.value = res.settings.default_transport || 'ws';
      if (dMux) dMux.value = res.settings.default_mux_con || 8;
      if (dMtu) dMtu.value = res.settings.mtu_clamp || 1360;
    }
  } catch (e) {}
}

function switchTab(tabId) {
  STATE.activeTab = tabId;
  document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');
  document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));

  const tabEl = document.getElementById(`tab-${tabId}`);
  if (tabEl) tabEl.style.display = 'block';

  const titles = {
    dashboard: 'داشبورد و وضعیت کلی هه‌واڵ',
    nodes: 'مدیریت سرورها و نودهای هه‌واڵ',
    tunnels: 'مدیریت تانل‌های Backhaul هوشمند',
    ping: 'سنجش زنده کیفیت ارتباط و پینگ سرورها',
    settings: 'تنظیمات متغیرها و پیکربندی پنل'
  };
  document.getElementById('page-title').innerText = titles[tabId] || 'داشبورد هه‌واڵ';

  const navItems = document.querySelectorAll('.nav-item');
  const indexMap = { dashboard: 0, nodes: 1, tunnels: 2, ping: 3, settings: 4 };
  if (navItems[indexMap[tabId]]) {
    navItems[indexMap[tabId]].classList.add('active');
  }
}

function renderDashboard() {
  const totalNodes = STATE.nodes.length;
  const onlineNodes = STATE.nodes.filter(n => n.status === 'online').length;
  const activeTunnels = STATE.tunnels.filter(t => t.status === 'running').length;

  document.getElementById('stat-total-nodes').innerText = totalNodes;
  document.getElementById('stat-online-nodes').innerText = onlineNodes;
  document.getElementById('stat-active-tunnels').innerText = activeTunnels;

  if (STATE.pings.length > 0) {
    document.getElementById('stat-avg-latency').innerText = `${STATE.pings[0].latency_avg_ms} ms`;
  }

  // Quick Nodes Grid
  const grid = document.getElementById('dashboard-nodes-grid');
  if (STATE.nodes.length === 0) {
    grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 32px;">هنوز نودی تعریف نشده است. روی «افزودن نود جدید» کلیک کنید.</div>`;
    return;
  }

  grid.innerHTML = STATE.nodes.map(n => `
    <div class="stat-card" style="display: flex; flex-direction: column; align-items: flex-start; gap: 12px;">
      <div style="display: flex; justify-content: space-between; width: 100%; align-items: center;">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span class="status-dot ${n.status}"></span>
          <strong style="font-size: 15px;">${n.flag || '🌐'} ${n.name}</strong>
        </div>
        <span class="badge ${n.role === 'iran' ? 'badge-role-iran' : 'badge-role-kharej'}">
          ${n.country_name || (n.role === 'iran' ? 'ایران' : 'خارج')}
        </span>
      </div>
      <div style="font-size: 13px; color: var(--text-muted); font-family: monospace; direction: ltr;">
        ${n.ip}
      </div>
      <div style="display: flex; justify-content: space-between; width: 100%; font-size: 12px; color: var(--text-muted); border-top: 1px solid var(--border); padding-top: 8px;">
        <span>CPU: ${n.cpu_percent}%</span>
        <span>RAM: ${n.ram_used_mb}/${n.ram_total_mb} MB</span>
      </div>
    </div>
  `).join('');
}

function renderTopology() {
  const container = document.getElementById('topology-container');
  if (STATE.nodes.length < 2) {
    container.innerHTML = `
      <div style="text-align: center; width: 100%; color: var(--text-muted); font-size: 13px; padding: 12px;">
        برای نمایش توپولوژی زنده، حداقل ۲ نود (یک نود مبدا ایران و یک نود خارج) اضافه کنید.
      </div>`;
    return;
  }

  const iranNode = STATE.nodes.find(n => n.role === 'iran') || STATE.nodes[0];
  const kharejNode = STATE.nodes.find(n => n.role !== 'iran' && n.id !== iranNode.id) || STATE.nodes[1];
  const latency = STATE.pings.length > 0 ? `${STATE.pings[0].latency_avg_ms} ms` : '~96 ms';
  const activeTun = STATE.tunnels.find(t => t.status === 'running');
  const transport = activeTun ? activeTun.transport.toUpperCase() : 'WS';
  const corePort = activeTun ? activeTun.core_port : '3080';

  container.innerHTML = `
    <div class="topology-node">
      <span style="font-size: 24px;">${iranNode.flag || '🇮🇷'}</span>
      <div>
        <div style="font-weight: 700; font-size: 14px;">${iranNode.name}</div>
        <div style="font-size: 12px; color: var(--text-muted); font-family: monospace; direction: ltr;">${iranNode.ip}</div>
      </div>
    </div>

    <div class="topology-line">
      <span class="topology-badge">⚡ Backhaul ${transport} : ${corePort} (${latency})</span>
      <div class="topology-track"></div>
      <span style="font-size: 11px; color: var(--text-muted);">ارتباط ایمن و مالتی‌پلکس هه‌واڵ</span>
    </div>

    <div class="topology-node">
      <span style="font-size: 24px;">${kharejNode.flag || '🌐'}</span>
      <div>
        <div style="font-weight: 700; font-size: 14px;">${kharejNode.name}</div>
        <div style="font-size: 12px; color: var(--text-muted); font-family: monospace; direction: ltr;">${kharejNode.ip}</div>
      </div>
    </div>
  `;
}

function renderNodes() {
  const tbody = document.getElementById('nodes-table-body');
  if (STATE.nodes.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 24px;">هیچ نودی یافت نشد.</td></tr>`;
    return;
  }

  tbody.innerHTML = STATE.nodes.map(n => `
    <tr>
      <td><strong>${n.flag || '🌐'} ${n.name}</strong></td>
      <td>
        <span class="badge ${n.role === 'iran' ? 'badge-role-iran' : 'badge-role-kharej'}">
          ${n.flag || '🌐'} ${n.country_name || (n.role === 'iran' ? 'ایران' : 'خارج')}
        </span>
      </td>
      <td style="font-family: monospace; direction: ltr;">${n.ip}</td>
      <td>
        <span class="badge ${n.status === 'online' ? 'badge-online' : 'badge-offline'}">
          <span class="status-dot ${n.status}"></span>
          ${n.status === 'online' ? 'آنلاین' : 'آفلاین'}
        </span>
      </td>
      <td style="font-size: 12px;">
        CPU: ${n.cpu_percent}% | RAM: ${n.ram_used_mb}MB
      </td>
      <td>
        <button class="btn btn-secondary btn-sm" onclick="showInstallCmd('${n.token}', '${n.role}', '${n.name}')">
          📋 دستور نصب
        </button>
      </td>
      <td>
        <button class="btn btn-danger btn-sm" onclick="deleteNode('${n.id}')">حذف</button>
      </td>
    </tr>
  `).join('');
}

function renderTunnels() {
  const tbody = document.getElementById('tunnels-table-body');
  if (STATE.tunnels.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 24px;">هیچ تانلی تعریف نشده است.</td></tr>`;
    return;
  }

  tbody.innerHTML = STATE.tunnels.map(t => {
    const isRunning = t.status === 'running';
    return `
      <tr>
        <td><strong>${t.name}</strong></td>
        <td>${t.server_node_name || 'نامشخص'}</td>
        <td>${t.client_node_name || 'نامشخص'}</td>
        <td style="font-family: monospace;">${t.core_port}</td>
        <td>
          <span class="badge badge-tag">${t.transport.toUpperCase()}</span>
        </td>
        <td>
          ${t.ports.map(p => `<span class="badge badge-tag" style="margin: 2px;">${p}</span>`).join('')}
        </td>
        <td>
          <span class="badge ${isRunning ? 'badge-online' : 'badge-offline'}">
            ${isRunning ? 'در حال اجرا' : 'متوقف'}
          </span>
        </td>
        <td style="display: flex; gap: 6px;">
          <button class="btn ${isRunning ? 'btn-secondary' : 'btn-success'} btn-sm" onclick="toggleTunnel('${t.id}', '${isRunning ? 'stopped' : 'running'}')">
            ${isRunning ? 'توقف' : 'شروع تانل'}
          </button>
          <button class="btn btn-secondary btn-sm" onclick="showDockerCompose('${t.id}')">🐳 داکر</button>
          <button class="btn btn-danger btn-sm" onclick="deleteTunnel('${t.id}')">حذف</button>
        </td>
      </tr>
    `;
  }).join('');
}

function renderPingSelects() {
  const addTunnelModal = document.getElementById('modal-add-tunnel');
  const isTunnelModalOpen = addTunnelModal && addTunnelModal.classList.contains('active');

  const select = document.getElementById('ping-target-select');
  if (select) {
    const curPingVal = select.value;
    select.innerHTML = STATE.nodes.map(n => `
      <option value="${n.ip}" data-id="${n.id}">${n.flag || '🌐'} ${n.name} (${n.ip} - ${n.country_name || n.role})</option>
    `).join('');
    if (curPingVal && Array.from(select.options).some(o => o.value === curPingVal)) {
      select.value = curPingVal;
    }
  }

  // If user is currently filling the Add Tunnel modal, do not reset their choices
  if (isTunnelModalOpen) {
    return;
  }

  const sSelect = document.getElementById('tunnel-server-node');
  const cSelect = document.getElementById('tunnel-client-node');
  if (sSelect && cSelect) {
    const iranNode = STATE.nodes.find(n => n.role === 'iran') || STATE.nodes[0];
    const kharejNode = STATE.nodes.find(n => n.role !== 'iran') || STATE.nodes[1] || STATE.nodes[0];

    sSelect.innerHTML = STATE.nodes.map(n => `
      <option value="${n.id}" ${iranNode && n.id === iranNode.id ? 'selected' : ''}>
        ${n.flag || '🌐'} ${n.name} (${n.country_name || n.role})
      </option>
    `).join('');

    cSelect.innerHTML = STATE.nodes.map(n => `
      <option value="${n.id}" ${kharejNode && n.id === kharejNode.id ? 'selected' : ''}>
        ${n.flag || '🌐'} ${n.name} (${n.country_name || n.role})
      </option>
    `).join('');
  }
}

function renderPingHistory() {
  const tbody = document.getElementById('ping-history-body');
  if (STATE.pings.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 16px;">هنوز تستی ثبت نشده است.</td></tr>`;
    return;
  }

  tbody.innerHTML = STATE.pings.map(p => `
    <tr>
      <td style="font-size: 12px; color: var(--text-muted);">${new Date(p.created_at * 1000).toLocaleTimeString('fa-IR')}</td>
      <td>${p.source_name || 'کنترل پنل'}</td>
      <td>${p.target_name || p.target_node_id}</td>
      <td><strong style="color: var(--accent-cyan);">${p.latency_avg_ms} ms</strong> (Min: ${p.latency_min_ms} / Max: ${p.latency_max_ms})</td>
      <td>
        <span class="badge ${p.packet_loss === 0 ? 'badge-online' : 'badge-offline'}">
          ${p.packet_loss}%
        </span>
      </td>
    </tr>
  `).join('');
}

// Interactive Port Tags
function renderPortChips() {
  const container = document.getElementById('port-chip-list');
  if (!container) return;

  if (STATE.activePortTags.length === 0) {
    container.innerHTML = `<span style="font-size: 12px; color: var(--text-muted);">هیچ پورتی افزوده نشده است. از لیست زیر یا فیلد بالا پورت اضافه کنید.</span>`;
    return;
  }

  container.innerHTML = STATE.activePortTags.map(port => `
    <span class="port-chip">
      <span>پورت ${port}</span>
      <button type="button" class="port-chip-remove" onclick="removePortChip(${port})">&times;</button>
    </span>
  `).join('');
}

function addPortChip(port) {
  const p = parseInt(port);
  if (isNaN(p) || p < 1 || p > 65535) {
    alert('لطفاً یک شماره پورت معتبر بین ۱ تا ۶۵۵۳۵ وارد کنید.');
    return;
  }
  if (!STATE.activePortTags.includes(p)) {
    STATE.activePortTags.push(p);
    renderPortChips();
  }
}

function removePortChip(port) {
  STATE.activePortTags = STATE.activePortTags.filter(p => p !== port);
  renderPortChips();
}

// Modal Handlers
function openAddNodeModal() {
  document.getElementById('modal-add-node').classList.add('active');
}

function openAddTunnelModal() {
  document.getElementById('modal-add-tunnel').classList.add('active');
  const sSelect = document.getElementById('tunnel-server-node');
  const cSelect = document.getElementById('tunnel-client-node');
  if (sSelect && cSelect) {
    const iranNode = STATE.nodes.find(n => n.role === 'iran') || STATE.nodes[0];
    const kharejNode = STATE.nodes.find(n => n.role !== 'iran') || STATE.nodes[1] || STATE.nodes[0];

    sSelect.innerHTML = STATE.nodes.map(n => `
      <option value="${n.id}" ${iranNode && n.id === iranNode.id ? 'selected' : ''}>
        ${n.flag || '🌐'} ${n.name} (${n.country_name || n.role})
      </option>
    `).join('');

    cSelect.innerHTML = STATE.nodes.map(n => `
      <option value="${n.id}" ${kharejNode && n.id === kharejNode.id ? 'selected' : ''}>
        ${n.flag || '🌐'} ${n.name} (${n.country_name || n.role})
      </option>
    `).join('');
  }
  renderPortChips();
}

function closeModal(id) {
  document.getElementById(id).classList.remove('active');
}

async function handleAddNode(e) {
  e.preventDefault();
  const name = document.getElementById('node-name').value;
  const ip = document.getElementById('node-ip').value;
  const role = document.getElementById('node-role').value;

  const res = await fetch('/api/nodes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, ip, role })
  }).then(r => r.json());

  closeModal('modal-add-node');
  fetchData();
  showInstallCmd(res.token, res.role, res.name);
}

function showInstallCmd(token, role, name) {
  STATE.currentInstallerToken = token;
  STATE.currentInstallerRole = role;
  STATE.currentInstallerName = name;
  updateInstallerCommand();
  document.getElementById('modal-install-code').classList.add('active');
}

function switchInstallerMode(mode) {
  STATE.installerMode = mode;
  document.getElementById('btn-mode-native').className = mode === 'native' ? 'btn btn-primary btn-sm' : 'btn btn-secondary btn-sm';
  document.getElementById('btn-mode-docker').className = mode === 'docker' ? 'btn btn-primary btn-sm' : 'btn btn-secondary btn-sm';
  updateInstallerCommand();
}

function updateInstallerCommand() {
  const host = window.location.host;
  let cmd = '';
  if (STATE.installerMode === 'native') {
    cmd = `curl -fsSL "http://${host}/install?token=${STATE.currentInstallerToken}&role=${STATE.currentInstallerRole}&name=${encodeURIComponent(STATE.currentInstallerName)}" | bash`;
  } else {
    cmd = `docker run -d --name hawal-node --restart always --net=host -e PANEL_URL="http://${host}" -e TOKEN="${STATE.currentInstallerToken}" -e ROLE="${STATE.currentInstallerRole}" musixal/backhaul:latest`;
  }
  document.getElementById('install-command-text').innerText = cmd;
}

function copyInstallCmd() {
  const text = document.getElementById('install-command-text').innerText;
  navigator.clipboard.writeText(text);
  alert('✅ دستور تک‌خطی در کلیپ‌بورد کپی شد!');
}

async function deleteNode(id) {
  if (!confirm('آیا از حذف این نود مطمئن هستید؟')) return;
  await fetch(`/api/nodes/${id}`, { method: 'DELETE' });
  fetchData();
}

async function handleAddTunnel(e) {
  e.preventDefault();
  const name = document.getElementById('tunnel-name').value;
  const server_node_id = document.getElementById('tunnel-server-node').value;
  const client_node_id = document.getElementById('tunnel-client-node').value;
  const core_port = document.getElementById('tunnel-core-port').value;
  const transport = document.getElementById('tunnel-transport').value;

  if (STATE.activePortTags.length === 0) {
    alert('لطفاً حداقل یک پورت فوروارد اضافه کنید.');
    return;
  }

  const ports = STATE.activePortTags.map(p => `${p}=127.0.0.1:${p}`);

  const res = await fetch('/api/tunnels', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, server_node_id, client_node_id, core_port, transport, ports })
  }).then(r => r.json());

  if (res.error) {
    alert('خطا: ' + res.error);
    return;
  }

  closeModal('modal-add-tunnel');
  fetchData();
}

async function toggleTunnel(id, status) {
  await fetch(`/api/tunnels/${id}/status`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status })
  });
  fetchData();
}

async function deleteTunnel(id) {
  if (!confirm('آیا از حذف این تانل مطمئن هستید؟')) return;
  await fetch(`/api/tunnels/${id}`, { method: 'DELETE' });
  fetchData();
}

async function showDockerCompose(tunnelId) {
  const res = await fetch(`/api/tunnels/${tunnelId}/docker`).then(r => r.json());
  if (res.server_compose) {
    document.getElementById('docker-compose-text').innerText = res.server_compose;
    document.getElementById('modal-tunnel-docker').classList.add('active');
  }
}

function copyDockerCompose() {
  const text = document.getElementById('docker-compose-text').innerText;
  navigator.clipboard.writeText(text);
  alert('✅ محتوای docker-compose.yml کپی شد!');
}

async function handleSaveSettings(e) {
  e.preventDefault();
  const panel_port = parseInt(document.getElementById('setting-panel-port').value);
  const default_transport = document.getElementById('setting-default-transport').value;
  const default_mux_con = parseInt(document.getElementById('setting-default-mux').value);
  const mtu_clamp = parseInt(document.getElementById('setting-mtu-clamp').value);

  const res = await fetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ panel_port, default_transport, default_mux_con, mtu_clamp })
  }).then(r => r.json());

  if (res.success) {
    alert('✅ تنظیمات با موفقیت ذخیره شدند.');
  }
}

async function triggerPingTest() {
  const select = document.getElementById('ping-target-select');
  const target_ip = select.value;
  const selectedOpt = select.options[select.selectedIndex];
  const target_node_id = selectedOpt ? selectedOpt.getAttribute('data-id') : 'target';

  document.getElementById('ping-result-container').style.display = 'block';
  document.getElementById('ping-res-avg').innerText = 'در حال تست...';

  const res = await fetch('/api/ping', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target_ip, target_node_id })
  }).then(r => r.json());

  if (res.success) {
    document.getElementById('ping-res-avg').innerText = `${res.avg_ms} ms`;
    document.getElementById('ping-res-min').innerText = `${res.min_ms} ms`;
    document.getElementById('ping-res-max').innerText = `${res.max_ms} ms`;
    document.getElementById('ping-res-loss').innerText = `${res.packet_loss}%`;
    fetchData();
  } else {
    document.getElementById('ping-res-avg').innerText = 'خطا در ارتباط';
  }
}
