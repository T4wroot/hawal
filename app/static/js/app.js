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
  editPortTags: [],
  ws: null,
  tunnelTestResults: {}
};

// UI UX Pro Max: Toast Notification System
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  
  let iconSvg = '';
  if (type === 'success') {
    iconSvg = '<svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>';
  } else if (type === 'error') {
    iconSvg = '<svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>';
  } else {
    iconSvg = '<svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>';
  }

  toast.innerHTML = `${iconSvg}<span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(15px)';
    toast.style.transition = 'all 0.25s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// -------------------------------------------------------------
// Engine Selector Segmented Cards
// -------------------------------------------------------------
function selectEngine(type) {
  document.getElementById('tunnel-core-type').value = type;
  const cardHawal = document.getElementById('card-engine-hawal');
  const cardPaqet = document.getElementById('card-engine-paqet');
  const cardBackhaul = document.getElementById('card-engine-backhaul');
  const cardGost = document.getElementById('card-engine-gost');
  const transportSelect = document.getElementById('tunnel-transport');

  if (cardHawal) cardHawal.classList.toggle('active', type === 'hawal');
  if (cardPaqet) cardPaqet.classList.toggle('active', type === 'paqet');
  if (cardBackhaul) cardBackhaul.classList.toggle('active', type === 'backhaul');
  if (cardGost) cardGost.classList.toggle('active', type === 'gost');

  if (transportSelect) {
    if (type === 'hawal') {
      transportSelect.innerHTML = '<option value="stealth" selected>⚡ Stealth Multi-Stream (ضد فیلتر و نویز متغیر)</option>';
    } else if (type === 'paqet') {
      transportSelect.innerHTML = '<option value="kcp" selected>🛡️ Raw Packet KCP (AES-128-GCM • ضد فیلترینگ شدید)</option>';
    } else if (type === 'gost') {
      transportSelect.innerHTML = `
        <option value="tls" selected>🔒 Relay over TLS (رمزنگاری‌شده و پایدار)</option>
        <option value="ws">WebSocket Relay</option>
        <option value="kcp">KCP Relay (UDP)</option>
        <option value="quic">QUIC Relay (UDP)</option>
      `;
    } else {
      transportSelect.innerHTML = `
        <option value="ws" selected>WebSocket (بکهول استاندارد)</option>
        <option value="tcp">TCP (خام و مستقیم)</option>
        <option value="tcpmux">TCP Mux (مالتی‌پلکس)</option>
        <option value="tls">TLS Encrypted</option>
      `;
    }
  }
}

function handleEditCoreTypeChange() {
  const coreType = document.getElementById('edit-tunnel-core-type').value;
  const transportSelect = document.getElementById('edit-tunnel-transport');
  if (!transportSelect) return;

  if (coreType === 'hawal') {
    transportSelect.innerHTML = '<option value="stealth" selected>⚡ Stealth Multi-Stream (ضد فیلتر و نویز متغیر)</option>';
  } else if (coreType === 'paqet') {
    transportSelect.innerHTML = '<option value="kcp" selected>🛡️ Raw Packet KCP (AES-128-GCM • ضد فیلترینگ شدید)</option>';
  } else if (coreType === 'gost') {
    transportSelect.innerHTML = `
      <option value="tls" selected>🔒 Relay over TLS</option>
      <option value="ws">WebSocket Relay</option>
      <option value="kcp">KCP Relay (UDP)</option>
      <option value="quic">QUIC Relay (UDP)</option>
    `;
  } else {
    transportSelect.innerHTML = `
      <option value="ws" selected>WebSocket (بکهول استاندارد)</option>
      <option value="tcp">TCP (خام و مستقیم)</option>
      <option value="tcpmux">TCP Mux (مالتی‌پلکس)</option>
      <option value="tls">TLS Encrypted</option>
    `;
  }
}

// -------------------------------------------------------------
// Port Chip Tag Manager (Add Modal)
// -------------------------------------------------------------
function renderPortChips() {
  const container = document.getElementById('port-chip-list');
  if (!container) return;
  container.innerHTML = '';

  if (STATE.activePortTags.length === 0) {
    container.innerHTML = '<span style="color: var(--text-dim); font-size: 12px;">هنوز پورتی اضافه نشده است. از لیست زیر یا فیلد بالا پورت اضافه کنید.</span>';
    return;
  }

  STATE.activePortTags.forEach(port => {
    const chip = document.createElement('div');
    chip.className = 'port-chip';
    chip.innerHTML = `
      <span>${port} ──► ${port}</span>
      <button type="button" class="port-chip-remove" onclick="removePortChip(${port})">&times;</button>
    `;
    container.appendChild(chip);
  });
}

function addPortChip(portVal) {
  const port = parseInt(portVal);
  if (isNaN(port) || port < 1 || port > 65535) {
    showToast('شماره پورت نامعتبر است (باید بین ۱ تا ۶۵۵۳۵ باشد)', 'error');
    return;
  }
  if (STATE.activePortTags.includes(port)) {
    showToast(`پورت ${port} قبلاً اضافه شده است`, 'info');
    return;
  }
  STATE.activePortTags.push(port);
  renderPortChips();
}

function removePortChip(port) {
  STATE.activePortTags = STATE.activePortTags.filter(p => p !== port);
  renderPortChips();
}

// -------------------------------------------------------------
// Port Chip Tag Manager (Edit Modal)
// -------------------------------------------------------------
function renderEditPortChips() {
  const container = document.getElementById('edit-port-chip-list');
  if (!container) return;
  container.innerHTML = '';

  if (STATE.editPortTags.length === 0) {
    container.innerHTML = '<span style="color: var(--text-dim); font-size: 12px;">هیچ پورتی برای این تانل ست نشده است.</span>';
    return;
  }

  STATE.editPortTags.forEach(port => {
    const chip = document.createElement('div');
    chip.className = 'port-chip';
    chip.innerHTML = `
      <span>${port} ──► ${port}</span>
      <button type="button" class="port-chip-remove" onclick="removeEditPortChip(${port})">&times;</button>
    `;
    container.appendChild(chip);
  });
}

function addEditPortChip(portVal) {
  const port = parseInt(portVal);
  if (isNaN(port) || port < 1 || port > 65535) {
    showToast('شماره پورت نامعتبر است', 'error');
    return;
  }
  if (STATE.editPortTags.includes(port)) {
    showToast(`پورت ${port} قبلاً در لیست وجود دارد`, 'info');
    return;
  }
  STATE.editPortTags.push(port);
  renderEditPortChips();
}

function removeEditPortChip(port) {
  STATE.editPortTags = STATE.editPortTags.filter(p => p !== port);
  renderEditPortChips();
}

// -------------------------------------------------------------
// Cloudflare Keyboard Shortcut & Quick Search
// -------------------------------------------------------------
document.addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault();
    const searchInput = document.getElementById('cf-home-search-input') || document.getElementById('sidebar-search-input');
    if (searchInput) searchInput.focus();
  }
});

function handleQuickFilter(query) {
  const q = (query || '').toLowerCase().trim();
  const tunnelRows = document.querySelectorAll('#cf-col-tunnels-list .cf-asset-row');
  tunnelRows.forEach(row => {
    const text = row.innerText.toLowerCase();
    row.style.display = text.includes(q) ? 'flex' : 'none';
  });

  const nodeRows = document.querySelectorAll('#cf-col-nodes-list .cf-asset-row');
  nodeRows.forEach(row => {
    const text = row.innerText.toLowerCase();
    row.style.display = text.includes(q) ? 'flex' : 'none';
  });
}

// -------------------------------------------------------------
// Tab Navigation
// -------------------------------------------------------------
function switchTab(tabId) {
  STATE.activeTab = tabId;
  document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');
  const activeSection = document.getElementById(`tab-${tabId}`);
  if (activeSection) activeSection.style.display = 'block';

  document.querySelectorAll('.cf-nav-item').forEach(el => el.classList.remove('active'));
  const activeNav = document.getElementById(`nav-${tabId}`);
  if (activeNav) activeNav.classList.add('active');

  const titles = {
    'dashboard': 'نمای کلی',
    'nodes': 'نودها',
    'tunnels': 'تانل‌ها',
    'ping': 'آزمایش شبکه',
    'settings': 'تنظیمات'
  };
  const breadcrumbs = document.getElementById('cf-breadcrumbs');
  if (breadcrumbs) {
    breadcrumbs.innerHTML = `
      <span>Hawal</span>
      <span>/</span>
      <span style="color: var(--cf-text-primary); font-weight: 700;">${titles[tabId] || 'نمای کلی'}</span>
    `;
  }
}

// -------------------------------------------------------------
// Live WebSocket Connection
// -------------------------------------------------------------
function connectWebSocket() {
  const loc = window.location;
  const wsProtocol = loc.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${wsProtocol}//${loc.host}/ws`;

  STATE.ws = new WebSocket(wsUrl);

  STATE.ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      if (msg.event === 'node_updated' || msg.event === 'tunnel_updated' || msg.event === 'ping_updated') {
        fetchData();
      }
    } catch (e) {}
  };

  STATE.ws.onclose = () => {
    setTimeout(connectWebSocket, 3000);
  };
}

// -------------------------------------------------------------
// Fetch and Render
// -------------------------------------------------------------
async function fetchData() {
  try {
    const [nodesRes, tunnelsRes, pingsRes, settingsRes] = await Promise.all([
      fetch('/api/nodes').then(r => r.json()),
      fetch('/api/tunnels').then(r => r.json()),
      fetch('/api/ping/history').then(r => r.json()),
      fetch('/api/settings').then(r => r.json())
    ]);

    STATE.nodes = nodesRes.nodes || [];
    STATE.tunnels = tunnelsRes.tunnels || [];
    STATE.pings = pingsRes.history || [];
    STATE.settings = settingsRes.settings || {};

    renderDashboard();
    renderNodes();
    renderTunnels();
    renderPingSection();
  } catch (e) {
    console.error('Error fetching state:', e);
  }
}

function formatBytes(bytes) {
  if (!bytes || bytes <= 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(k)), sizes.length - 1);
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function renderDashboard() {
  const colCountTunnels = document.getElementById('col-count-tunnels');
  const colCountNodes = document.getElementById('col-count-nodes');
  const colTotalTraffic = document.getElementById('col-total-traffic');

  if (colCountTunnels) colCountTunnels.innerText = STATE.tunnels.length;
  if (colCountNodes) colCountNodes.innerText = STATE.nodes.length;

  const totalIn = STATE.tunnels.reduce((acc, t) => acc + (t.bytes_in || 0), 0);
  const totalOut = STATE.tunnels.reduce((acc, t) => acc + (t.bytes_out || 0), 0);
  const totalNetworkTraffic = totalIn + totalOut;
  if (colTotalTraffic) colTotalTraffic.innerText = formatBytes(totalNetworkTraffic);

  renderCloudflareTunnelsColumn();
  renderCloudflareNodesColumn();
  renderCloudflareAnalyticsColumn(totalIn, totalOut);
  renderTopology();
}

function renderCloudflareTunnelsColumn() {
  const container = document.getElementById('cf-col-tunnels-list');
  if (!container) return;
  container.innerHTML = '';

  if (STATE.tunnels.length === 0) {
    container.innerHTML = '<div style="padding: 16px; color: var(--cf-text-muted); font-size: 13px;">هیچ تانلی ایجاد نشده است.</div>';
    return;
  }

  STATE.tunnels.forEach(tun => {
    const row = document.createElement('div');
    row.className = 'cf-asset-row';
    row.onclick = () => switchTab('tunnels');

    let engineLabel = '🚀 Backhaul';
    if (tun.core_type === 'paqet') engineLabel = '🛡️ Paqet KCP';
    else if (tun.core_type === 'hawal') engineLabel = '⚡ Stealth Core';
    else if (tun.core_type === 'gost') engineLabel = '👻 GOST Relay';
    const totalBytes = (tun.bytes_in || 0) + (tun.bytes_out || 0);

    row.innerHTML = `
      <div class="cf-asset-left">
        <svg class="cf-asset-icon" style="color: var(--cf-orange);" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
        <div>
          <div class="cf-asset-title">${tun.name}</div>
          <div class="cf-asset-subtitle">
            ${engineLabel} • پورت ${tun.core_port} • ${formatBytes(totalBytes)}
          </div>
        </div>
      </div>
      <svg class="cf-asset-chevron" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg>
    `;
    container.appendChild(row);
  });
}

function renderCloudflareNodesColumn() {
  const container = document.getElementById('cf-col-nodes-list');
  if (!container) return;
  container.innerHTML = '';

  if (STATE.nodes.length === 0) {
    container.innerHTML = '<div style="padding: 16px; color: var(--cf-text-muted); font-size: 13px;">هیچ نودی یافت نشد.</div>';
    return;
  }

  STATE.nodes.forEach(node => {
    const row = document.createElement('div');
    row.className = 'cf-asset-row';
    row.onclick = () => switchTab('nodes');

    const isOnline = node.status === 'online';

    row.innerHTML = `
      <div class="cf-asset-left">
        <span style="font-size: 16px;">${node.flag || '🌐'}</span>
        <div>
          <div class="cf-asset-title">${node.name}</div>
          <div class="cf-asset-subtitle">
            ${node.ip} • <span style="color: ${isOnline ? 'var(--cf-green)' : 'var(--cf-red)'}; font-weight: 700;">${isOnline ? '🟢 آنلاین' : '🔴 آفلاین'}</span>
          </div>
        </div>
      </div>
      <svg class="cf-asset-chevron" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg>
    `;
    container.appendChild(row);
  });
}

function renderCloudflareAnalyticsColumn(totalIn, totalOut) {
  const container = document.getElementById('cf-col-analytics-list');
  if (!container) return;

  container.innerHTML = `
    <div class="cf-asset-row" onclick="switchTab('tunnels')">
      <div class="cf-asset-left">
        <svg class="cf-asset-icon" style="color: var(--cf-green);" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
        <div>
          <div class="cf-asset-title">ترافیک ورودی</div>
          <div class="cf-asset-subtitle">${formatBytes(totalIn)}</div>
        </div>
      </div>
      <svg class="cf-asset-chevron" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg>
    </div>

    <div class="cf-asset-row" onclick="switchTab('tunnels')">
      <div class="cf-asset-left">
        <svg class="cf-asset-icon" style="color: var(--cf-blue);" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
        <div>
          <div class="cf-asset-title">ترافیک خروجی</div>
          <div class="cf-asset-subtitle">${formatBytes(totalOut)}</div>
        </div>
      </div>
      <svg class="cf-asset-chevron" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg>
    </div>

    <div class="cf-asset-row" onclick="switchTab('ping')">
      <div class="cf-asset-left">
        <svg class="cf-asset-icon" style="color: var(--cf-orange);" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
        <div>
          <div class="cf-asset-title">تاخیر میانگین شبکه</div>
          <div class="cf-asset-subtitle">برای مشاهده، آزمایش شبکه را اجرا کنید</div>
        </div>
      </div>
      <svg class="cf-asset-chevron" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg>
    </div>
  `;
}

function renderTopology() {
  const container = document.getElementById('topology-container');
  if (!container) return;

  const iranNode = STATE.nodes.find(n => n.role === 'iran');
  const kharejNode = STATE.nodes.find(n => n.role === 'kharej');
  const indicator = document.getElementById('cf-rtt-indicator');

  if (!iranNode || !kharejNode) {
    if (indicator) indicator.textContent = 'برای نمایش مسیر، دو نود اضافه کنید';
    container.innerHTML = `
      <div class="topology-empty">
        <div class="topology-empty-icon">↔</div>
        <div><strong>مسیر ارتباطی هنوز آماده نیست</strong><span>یک نود ایران و یک نود خارج اضافه کنید تا نقشهٔ ارتباط نمایش داده شود.</span></div>
        <button class="btn btn-secondary btn-sm" onclick="openAddNodeModal()">افزودن نود</button>
      </div>`;
    return;
  }

  const activeTunnels = STATE.tunnels.filter(t => t.status === 'running').length;
  const iranOnline = iranNode.status === 'online';
  const foreignOnline = kharejNode.status === 'online';
  const routeHealthy = iranOnline && foreignOnline;
  if (indicator) indicator.textContent = routeHealthy ? `${activeTunnels} تانل فعال` : 'نیازمند بررسی نودها';

  container.innerHTML = `
    <div class="topology-network">
      <div class="route-node ${iranOnline ? 'online' : 'offline'}">
        <div class="route-flag">${iranNode.flag || '🇮🇷'}</div>
        <div class="route-copy"><span class="route-label">نود ایران</span><strong>${iranNode.name}</strong><code>${iranNode.ip}</code></div>
        <span class="route-status"><i></i>${iranOnline ? 'متصل' : 'قطع'}</span>
      </div>
      <div class="route-connector ${routeHealthy ? 'healthy' : ''}">
        <span>${activeTunnels} تانل فعال</span><div><i></i><i></i><i></i></div><small>مسیر رمزگذاری‌شده</small>
      </div>
      <div class="route-node ${foreignOnline ? 'online' : 'offline'}">
        <div class="route-flag">${kharejNode.flag || '🌐'}</div>
        <div class="route-copy"><span class="route-label">نود خارج</span><strong>${kharejNode.name}</strong><code>${kharejNode.ip}</code></div>
        <span class="route-status"><i></i>${foreignOnline ? 'متصل' : 'قطع'}</span>
      </div>
    </div>
  `;
}

function renderDashboardNodeCards() {
  const container = document.getElementById('dashboard-nodes-grid');
  if (!container) return;
  container.innerHTML = '';

  if (STATE.nodes.length === 0) {
    container.innerHTML = '<div style="color: var(--text-muted); font-size: 13px;">هیچ نودی یافت نشد.</div>';
    return;
  }

  STATE.nodes.forEach(node => {
    const card = document.createElement('div');
    card.className = 'stat-card';
    card.style.flexDirection = 'column';
    card.style.alignItems = 'stretch';
    card.style.gap = '14px';

    const isOnline = node.status === 'online';
    const cpu = node.cpu_percent || 0.1;
    const ramU = node.ram_used_mb || 12;
    const ramT = node.ram_total_mb || 2048;

    card.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <div style="display: flex; align-items: center; gap: 10px;">
          <span style="font-size: 22px;">${node.flag || '🌐'}</span>
          <div>
            <div style="font-weight: 800; font-size: 14px;">${node.name}</div>
            <div style="font-size: 12px; color: var(--text-muted); font-family: 'JetBrains Mono';">${node.ip}</div>
          </div>
        </div>
        <div class="badge ${isOnline ? 'badge-online' : 'badge-offline'}">
          <span class="status-dot ${isOnline ? 'online' : 'offline'}"></span>
          ${isOnline ? 'آنلاین' : 'آفلاین'}
        </div>
      </div>

      <div style="display: flex; flex-direction: column; gap: 8px; font-size: 12px;">
        <div>
          <div style="display: flex; justify-content: space-between; color: var(--text-muted);">
            <span>مصرف پردازنده (CPU):</span>
            <span style="font-family: 'JetBrains Mono'; color: #f8fafc;">${cpu}%</span>
          </div>
          <div style="background: rgba(255,255,255,0.06); height: 4px; border-radius: 2px; margin-top: 4px; overflow: hidden;">
            <div style="width: ${Math.min(100, cpu * 3)}%; background: var(--accent-amber); height: 100%;"></div>
          </div>
        </div>

        <div>
          <div style="display: flex; justify-content: space-between; color: var(--text-muted);">
            <span>مصرف رم (RAM):</span>
            <span style="font-family: 'JetBrains Mono'; color: #f8fafc;">${ramU} MB / ${ramT} MB</span>
          </div>
          <div style="background: rgba(255,255,255,0.06); height: 4px; border-radius: 2px; margin-top: 4px; overflow: hidden;">
            <div style="width: ${Math.min(100, (ramU / ramT) * 100)}%; background: var(--accent-emerald); height: 100%;"></div>
          </div>
        </div>
      </div>
    `;
    container.appendChild(card);
  });
}

function renderNodes() {
  const tbody = document.getElementById('nodes-table-body');
  if (!tbody) return;
  tbody.innerHTML = '';

  STATE.nodes.forEach(node => {
    const tr = document.createElement('tr');
    const isOnline = node.status === 'online';

    tr.innerHTML = `
      <td style="font-weight: 800;">
        <span style="margin-left: 6px;">${node.flag || '🌐'}</span>
        ${node.name}
      </td>
      <td>${node.country_name || 'نامشخص'} (${node.country_code || 'XX'})</td>
      <td style="font-family: 'JetBrains Mono'; color: var(--accent-amber);">${node.ip}</td>
      <td>
        <div class="badge ${isOnline ? 'badge-online' : 'badge-offline'}">
          <span class="status-dot ${isOnline ? 'online' : 'offline'}"></span>
          ${isOnline ? 'آنلاین' : 'آفلاین'}
        </div>
      </td>
      <td style="font-family: 'JetBrains Mono'; font-size: 13px;">
        CPU: ${node.cpu_percent || 0}% | RAM: ${node.ram_used_mb || 0}MB
      </td>
      <td>
        <button class="btn btn-secondary btn-sm" onclick="showInstallModal('${node.token}', '${node.role}', '${node.name}')">
          دستور نصب 📋
        </button>
      </td>
      <td>
        <button class="btn btn-danger btn-sm" onclick="deleteNode('${node.id}')">حذف</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function renderTunnels() {
  const tbody = document.getElementById('tunnels-table-body');
  if (!tbody) return;
  tbody.innerHTML = '';

  STATE.tunnels.forEach(tun => {
    const tr = document.createElement('tr');
    let engineBadge = '<span style="color: #60a5fa; font-weight: 700;">🚀 Backhaul Core</span>';
    if (tun.core_type === 'hawal') {
      engineBadge = '<span style="color: var(--accent-amber); font-weight: 700;">⚡ هسته Go Stealth</span>';
    } else if (tun.core_type === 'paqet') {
      engineBadge = '<span style="color: #10b981; font-weight: 700;">🛡️ Paqet Raw KCP</span>';
    } else if (tun.core_type === 'gost') {
      engineBadge = '<span style="color: #7c3aed; font-weight: 700;">👻 GOST Relay</span>';
    }
    const isRunning = tun.status === 'running';
    const bIn = tun.bytes_in || 0;
    const bOut = tun.bytes_out || 0;

    let portsBadges = '';
    (tun.ports || []).forEach(p => {
      portsBadges += `<span class="badge badge-tag" style="margin-left: 4px;">${p}</span>`;
    });

    const testRes = STATE.tunnelTestResults[tun.id];
    let testBadgeHtml = '';
    if (testRes) {
      if (testRes.loading) {
        testBadgeHtml = '<span class="badge" style="background:rgba(245,158,11,0.2); color:#fde68a;">در حال تست... ⏳</span>';
      } else if (testRes.success) {
        testBadgeHtml = `<span class="badge badge-online">🟢 ${testRes.latency_avg_ms}ms • ${testRes.packet_loss}% Loss</span>`;
      } else {
        testBadgeHtml = '<span class="badge badge-offline">🔴 عدم اتصال</span>';
      }
    } else {
      testBadgeHtml = `<button class="btn btn-test btn-sm" onclick="testTunnel('${tun.id}')">⚡ تست پینگ و سلامت</button>`;
    }

    tr.innerHTML = `
      <td>
        <div style="font-weight: 800;">${tun.name}</div>
        <div style="font-size: 11px; margin-top: 2px;">
          ${engineBadge}
        </div>
      </td>
      <td style="font-family: 'JetBrains Mono'; font-size: 13px;">${tun.server_name || 'Iran Node'}</td>
      <td style="font-family: 'JetBrains Mono'; font-size: 13px;">${tun.client_name || 'Germany Node'}</td>
      <td style="font-family: 'JetBrains Mono'; color: var(--accent-amber); font-weight: 700;">${tun.core_port}</td>
      <td>${portsBadges}</td>
      <td>
        <div style="font-family: 'JetBrains Mono'; font-size: 12px; display: flex; flex-direction: column; gap: 2px;">
          <span style="color: #34d399;">📥 ${formatBytes(bIn)}</span>
          <span style="color: #38bdf8;">📤 ${formatBytes(bOut)}</span>
        </div>
      </td>
      <td>
        <div id="test-col-${tun.id}">${testBadgeHtml}</div>
      </td>
      <td>
        <div class="badge ${isRunning ? 'badge-online' : 'badge-offline'}">
          <span class="status-dot ${isRunning ? 'online' : 'offline'}"></span>
          ${isRunning ? 'فعال' : 'متوقف'}
        </div>
      </td>
      <td>
        <div style="display: flex; gap: 6px;">
          <button class="btn btn-edit btn-sm" onclick="openEditTunnelModal('${tun.id}')" title="ویرایش پورت‌ها و تنظیمات">
            ✏️ ویرایش
          </button>
          <button class="btn btn-secondary btn-sm" onclick="showDockerModal('${tun.id}')" title="فایل داکر">
            🐳
          </button>
          <button class="btn btn-danger btn-sm" onclick="deleteTunnel('${tun.id}')" title="حذف تانل">
            حذف
          </button>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

// -------------------------------------------------------------
// Live Tunnel Health & Ping Tester
// -------------------------------------------------------------
async function testTunnel(tunnelId) {
  STATE.tunnelTestResults[tunnelId] = { loading: true };
  renderTunnels();

  try {
    const res = await fetch(`/api/tunnels/${tunnelId}/test`, { method: 'POST' });
    const data = await res.json();
    STATE.tunnelTestResults[tunnelId] = data;
    renderTunnels();

    if (data.success) {
      showToast(`تست تانل موفق بود: تاخیر ${data.latency_avg_ms}ms روی پورت ${data.tested_port}`, 'success');
    } else {
      showToast(`خطا در ارتباط با تانل: ${data.error || 'پاسخ دریافت نشد'}`, 'error');
    }
  } catch (e) {
    STATE.tunnelTestResults[tunnelId] = { success: false, error: e.message };
    renderTunnels();
    showToast('خطا در اجرای تست پینگ تانل', 'error');
  }
}

// -------------------------------------------------------------
// Edit Tunnel Flow
// -------------------------------------------------------------
function openEditTunnelModal(tunnelId) {
  const tunnel = STATE.tunnels.find(t => t.id === tunnelId);
  if (!tunnel) return;

  document.getElementById('edit-tunnel-id').value = tunnel.id;
  document.getElementById('edit-tunnel-name').value = tunnel.name;
  document.getElementById('edit-tunnel-core-port').value = tunnel.core_port;
  
  const coreTypeSelect = document.getElementById('edit-tunnel-core-type');
  if (coreTypeSelect) coreTypeSelect.value = tunnel.core_type || 'hawal';
  handleEditCoreTypeChange();

  // Extract port numbers
  STATE.editPortTags = (tunnel.ports || []).map(rule => {
    const p = parseInt(rule.split('=')[0]);
    return isNaN(p) ? 80 : p;
  });

  renderEditPortChips();
  document.getElementById('modal-edit-tunnel').classList.add('active');
}

async function handleSaveEditTunnel(e) {
  e.preventDefault();
  const tunnelId = document.getElementById('edit-tunnel-id').value;
  const name = document.getElementById('edit-tunnel-name').value;
  const coreType = document.getElementById('edit-tunnel-core-type').value;
  const corePort = parseInt(document.getElementById('edit-tunnel-core-port').value);
  const transport = document.getElementById('edit-tunnel-transport').value;

  if (STATE.editPortTags.length === 0) {
    showToast('حداقل یک پورت باید برای تانل مشخص شود', 'error');
    return;
  }

  const ports = STATE.editPortTags.map(p => `${p}=127.0.0.1:${p}`);

  try {
    const res = await fetch(`/api/tunnels/${tunnelId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: jsonStringifySafe({
        name,
        core_type: coreType,
        core_port: corePort,
        transport,
        ports
      })
    });

    const data = await res.json();
    if (res.ok) {
      showToast('تنظیمات و پورت‌های تانل با موفقیت بروزرسانی شد', 'success');
      closeModal('modal-edit-tunnel');
      fetchData();
    } else {
      showToast(data.error || 'خطا در ویرایش تانل', 'error');
    }
  } catch (err) {
    showToast('خطا در برقراری ارتباط با سرور', 'error');
  }
}

function jsonStringifySafe(obj) {
  return JSON.stringify(obj);
}

// -------------------------------------------------------------
// Modals & Handlers
// -------------------------------------------------------------
function openAddTunnelModal() {
  document.getElementById('modal-add-tunnel').classList.add('active');
  const sSelect = document.getElementById('tunnel-server-node');
  const cSelect = document.getElementById('tunnel-client-node');
  if (sSelect && cSelect) {
    sSelect.innerHTML = '';
    cSelect.innerHTML = '';
    STATE.nodes.forEach(n => {
      sSelect.innerHTML += `<option value="${n.id}" ${n.role === 'iran' ? 'selected' : ''}>${n.flag || '🇮🇷'} ${n.name} (${n.ip})</option>`;
      cSelect.innerHTML += `<option value="${n.id}" ${n.role === 'kharej' ? 'selected' : ''}>${n.flag || '🌐'} ${n.name} (${n.ip})</option>`;
    });
  }
  renderPortChips();
}

function openAddNodeModal() {
  document.getElementById('modal-add-node').classList.add('active');
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove('active');
}

async function handleAddNode(e) {
  e.preventDefault();
  const name = document.getElementById('node-name').value;
  const ip = document.getElementById('node-ip').value;
  const role = document.getElementById('node-role').value;

  try {
    const res = await fetch('/api/nodes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, ip, role })
    });
    const data = await res.json();
    closeModal('modal-add-node');
    showInstallModal(data.token, role, name);
    showToast('نود جدید با موفقیت ایجاد شد', 'success');
    fetchData();
  } catch (err) {
    showToast('خطا در ساخت نود', 'error');
  }
}

async function handleAddTunnel(e) {
  e.preventDefault();
  const name = document.getElementById('tunnel-name').value;
  const coreType = document.getElementById('tunnel-core-type').value;
  const serverNodeId = document.getElementById('tunnel-server-node').value;
  const clientNodeId = document.getElementById('tunnel-client-node').value;
  const corePort = parseInt(document.getElementById('tunnel-core-port').value);
  const transport = document.getElementById('tunnel-transport').value;

  if (STATE.activePortTags.length === 0) {
    showToast('حداقل یک پورت باید اضافه شود', 'error');
    return;
  }

  const ports = STATE.activePortTags.map(p => `${p}=127.0.0.1:${p}`);

  try {
    const res = await fetch('/api/tunnels', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name,
        core_type: coreType,
        server_node_id: serverNodeId,
        client_node_id: clientNodeId,
        core_port: corePort,
        transport,
        ports
      })
    });
    const data = await res.json();
    if (res.ok) {
      showToast('تانل با موفقیت ایجاد و فعال شد', 'success');
      closeModal('modal-add-tunnel');
      fetchData();
    } else {
      showToast(data.error || 'خطا در ساخت تانل', 'error');
    }
  } catch (err) {
    showToast('خطا در برقراری ارتباط با سرور', 'error');
  }
}

async function deleteTunnel(tunnelId) {
  if (!confirm('آیا از حذف این تانل مطمئن هستید؟')) return;
  try {
    await fetch(`/api/tunnels/${tunnelId}`, { method: 'DELETE' });
    showToast('تانل با موفقیت حذف شد', 'info');
    fetchData();
  } catch (e) {
    showToast('خطا در حذف تانل', 'error');
  }
}

async function deleteNode(nodeId) {
  if (!confirm('آیا از حذف این نود مطمئن هستید؟')) return;
  try {
    await fetch(`/api/nodes/${nodeId}`, { method: 'DELETE' });
    showToast('نود با موفقیت حذف شد', 'info');
    fetchData();
  } catch (e) {
    showToast('خطا در حذف نود', 'error');
  }
}

function showInstallModal(token, role, name) {
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
  const origin = window.location.origin;
  const cmdBox = document.getElementById('install-command-text');
  if (!cmdBox) return;

  if (STATE.installerMode === 'native') {
    cmdBox.innerText = `curl -fsSL ${origin}/install.sh | bash -s -- --panel ${origin} --token ${STATE.currentInstallerToken}`;
  } else {
    cmdBox.innerText = `docker run -d --name hawal-agent --restart=always --network=host -e PANEL_URL="${origin}" -e AGENT_TOKEN="${STATE.currentInstallerToken}" ghcr.io/t4wroot/hawal-agent:latest`;
  }
}

function copyInstallCmd() {
  const text = document.getElementById('install-command-text').innerText;
  navigator.clipboard.writeText(text);
  showToast('دستور با موفقیت در کلیپ‌بورد کپی شد', 'success');
}

async function showDockerModal(tunnelId) {
  try {
    const res = await fetch(`/api/tunnels/${tunnelId}/docker`);
    const data = await res.json();
    document.getElementById('docker-compose-text').innerText = data.server_compose || '# Docker Compose File';
    document.getElementById('modal-tunnel-docker').classList.add('active');
  } catch (e) {
    showToast('خطا در بارگذاری اطلاعات داکر', 'error');
  }
}

function copyDockerCompose() {
  const text = document.getElementById('docker-compose-text').innerText;
  navigator.clipboard.writeText(text);
  showToast('فایل docker-compose کپی شد', 'success');
}

function renderPingSection() {
  const select = document.getElementById('ping-target-select');
  if (select) {
    select.innerHTML = '';
    STATE.nodes.forEach(n => {
      select.innerHTML += `<option value="${n.id}">${n.flag || '🌐'} ${n.name} (${n.ip})</option>`;
    });
  }

  const tbody = document.getElementById('ping-history-body');
  if (tbody) {
    tbody.innerHTML = '';
    STATE.pings.forEach(p => {
      const tr = document.createElement('tr');
      const d = new Date(p.created_at * 1000).toLocaleTimeString('fa-IR');
      tr.innerHTML = `
        <td style="font-family: 'JetBrains Mono'; font-size: 12px;">${d}</td>
        <td>${p.source_name}</td>
        <td>${p.target_name}</td>
        <td style="font-family: 'JetBrains Mono'; color: var(--accent-amber); font-weight: 700;">${p.latency_avg_ms} ms</td>
        <td style="font-family: 'JetBrains Mono'; color: ${p.packet_loss === 0 ? 'var(--accent-emerald)' : 'var(--accent-rose)'};">${p.packet_loss}%</td>
      `;
      tbody.appendChild(tr);
    });
  }
}

async function triggerPingTest() {
  const targetId = document.getElementById('ping-target-select').value;
  if (!targetId) return;

  showToast('در حال ارسال پکت‌های تست پینگ و پکت‌لاس...', 'info');

  try {
    const res = await fetch('/api/ping/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target_node_id: targetId })
    });
    const data = await res.json();
    
    document.getElementById('ping-result-container').style.display = 'block';
    document.getElementById('ping-res-avg').innerText = `${data.latency_avg_ms} ms`;
    document.getElementById('ping-res-min').innerText = `${data.latency_min_ms} ms`;
    document.getElementById('ping-res-max').innerText = `${data.latency_max_ms} ms`;
    document.getElementById('ping-res-loss').innerText = `${data.packet_loss}%`;

    showToast('تست پینگ با موفقیت انجام شد', 'success');
    fetchData();
  } catch (e) {
    showToast('خطا در اجرای تست پینگ', 'error');
  }
}

async function handleSaveSettings(e) {
  e.preventDefault();
  const panelPort = parseInt(document.getElementById('setting-panel-port').value);
  const defaultTransport = document.getElementById('setting-default-transport').value;
  const defaultMux = parseInt(document.getElementById('setting-default-mux').value);
  const mtuClamp = parseInt(document.getElementById('setting-mtu-clamp').value);

  try {
    const res = await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        panel_port: panelPort,
        default_transport: defaultTransport,
        default_mux: defaultMux,
        mtu_clamp: mtuClamp
      })
    });
    if (res.ok) {
      showToast('تنظیمات با موفقیت ذخیره شد', 'success');
    }
  } catch (e) {
    showToast('خطا در ذخیره تنظیمات', 'error');
  }
}

// -------------------------------------------------------------
// App Initialization
// -------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
  fetchData();
  connectWebSocket();
  renderPortChips();
});
