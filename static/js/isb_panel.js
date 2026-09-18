// ============================================================
//  ИСБ · ПАНЕЛЬ УПРАВЛЕНИЯ · JS
// ============================================================

// ============================================================
//  ЧАСЫ И СЕАНС
// ============================================================
const sessionStart = Date.now();

function pad(n) { return String(n).padStart(2, '0'); }

function updateClocks() {
    const now = new Date();
    document.getElementById('clockTime').textContent =
        `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;

    const days = ['ВС', 'ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ'];
    document.getElementById('clockDate').textContent =
        `${pad(now.getDate())}.${pad(now.getMonth() + 1)}.${now.getFullYear()} · ${days[now.getDay()]}`;

    const elapsed = Math.floor((Date.now() - sessionStart) / 1000);
    const h = Math.floor(elapsed / 3600);
    const m = Math.floor((elapsed % 3600) / 60);
    const s = elapsed % 60;
    document.getElementById('sessionTime').textContent = `${pad(h)}:${pad(m)}:${pad(s)}`;
}

setInterval(updateClocks, 1000);
updateClocks();


// ============================================================
//  УРОВЕНЬ ДОСТУПА
// ============================================================
let myAccess = { level: 1, name: '—' };

async function loadAccess() {
    try {
        const res = await fetch('/api/isb/me/access');
        if (!res.ok) return;
        const data = await res.json();
        myAccess = data.data || myAccess;

        const operatorBadge = document.querySelector('.isb-operator-badge');
        if (operatorBadge) {
            operatorBadge.title = `УРОВЕНЬ ДОСТУПА: ${myAccess.level} · ${myAccess.name}`;
        }

        updateVisibility();
    } catch (e) {
        console.error('Уровень:', e);
    }
}

function updateVisibility() {
    const graphsPanel = document.getElementById('graphsPanel');
    if (graphsPanel) {
        graphsPanel.style.display = myAccess.level >= 3 ? 'flex' : 'none';
    }

    const adminPanel = document.getElementById('adminPanel');
    if (adminPanel) {
        adminPanel.style.display = myAccess.level >= 4 ? 'flex' : 'none';
    }
}


// ============================================================
//  СТАТИСТИКА
// ============================================================
async function loadStats() {
    try {
        const res = await fetch('/api/admin/isb/employees');
        if (res.ok) {
            const data = await res.json();
            const employees = data.data || [];
            const active = employees.filter(e => e.is_active).length;
            document.getElementById('statEmployees').innerHTML =
                `${active} <small>чел.</small>`;
        }
    } catch (e) { console.error(e); }

    try {
        const res = await fetch('/api/admin/isb/awards/public');
        if (res.ok) {
            const data = await res.json();
            const awards = data.data || [];
            const totalGrants = awards.reduce((sum, a) => sum + (a.grants_count || 0), 0);
            document.getElementById('statAwards').innerHTML =
                `${totalGrants} <small>ед.</small>`;
        }
    } catch (e) { console.error(e); }

    document.getElementById('lastUpdate').textContent =
        'ОБНОВЛЕНО: ' + new Date().toLocaleTimeString('ru-RU');
}

loadStats();
setInterval(loadStats, 60000);


// ============================================================
//  СЕКТОРА
// ============================================================
async function loadSectors() {
    const grid = document.getElementById('sectorsGrid');
    if (!grid) return;
    try {
        const res = await fetch('/api/isb/sectors');
        if (!res.ok) {
            grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-muted);">ДОСТУП ЗАПРЕЩЁН</div>';
            return;
        }
        const data = await res.json();
        const sectors = data.data || [];
        document.getElementById('sectorsTotal').textContent = 'ВСЕГО: ' + sectors.length;

        if (sectors.length === 0) {
            grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-muted);">СЕКТОРА НЕ НАСТРОЕНЫ</div>';
            return;
        }

        grid.innerHTML = sectors.map(s => {
            const membersHtml = s.members.slice(0, 5).map(m =>
                m.avatar_url
                    ? `<img src="${m.avatar_url}" class="avatar-mini" alt="${m.username}">`
                    : `<div class="avatar-mini">👤</div>`
            ).join('') + (s.members_count > 5 ? `<span style="color: var(--text-muted); font-size: 10px;">+${s.members_count - 5}</span>` : '');

            return `
                <div class="isb-sector-card">
                    <div class="isb-sector-header">
                        <span class="isb-sector-number">S-${String(s.number).padStart(2, '0')}</span>
                        <span class="isb-sector-threat" data-level="${s.threat_level}">УР. ${s.threat_level}</span>
                    </div>
                    <div class="isb-sector-name">${s.name}</div>
                    <div class="isb-sector-desc">${s.description || '—'}</div>
                    <div class="isb-sector-footer">
                        <span>👥 ${s.members_count}</span>
                        <div class="isb-sector-members">${membersHtml || '—'}</div>
                    </div>
                </div>
            `;
        }).join('');
    } catch (e) {
        grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-muted);">ОШИБКА ЗАГРУЗКИ</div>';
    }
}

loadSectors();
setInterval(loadSectors, 30000);


// ============================================================
//  ЛОГИ
// ============================================================
async function loadLogs() {
    try {
        const res = await fetch('/api/isb/logs?limit=30');
        if (!res.ok) return;
        const data = await res.json();
        const items = data.data || [];
        const list = document.getElementById('logList');
        const SEV_LABELS = { critical: 'КРИТИЧ.', warning: 'ВНИМАНИЕ', info: 'ИНФО' };

        if (items.length === 0) {
            list.innerHTML = `
                <div class="isb-log-entry">
                    <span class="isb-log-time">--:--:--</span>
                    <span class="isb-log-severity info">ИНФО</span>
                    <span class="isb-log-message">ЖУРНАЛ ПУСТ</span>
                </div>
            `;
            return;
        }

        list.innerHTML = items.map(l => {
            const time = l.created_at ? new Date(l.created_at).toLocaleTimeString('ru-RU') : '--:--:--';
            const actor = l.actor ? `<strong>${l.actor}</strong> · ` : '';
            const sector = l.sector_number ? ` · S-${String(l.sector_number).padStart(2, '0')}` : '';

            return `
                <div class="isb-log-entry">
                    <span class="isb-log-time">${time}</span>
                    <span class="isb-log-severity ${l.severity}">${SEV_LABELS[l.severity] || l.severity}</span>
                    <span class="isb-log-message">${actor}${l.message}${sector}</span>
                </div>
            `;
        }).join('');
    } catch (e) {
        console.error(e);
    }
}

loadLogs();
setInterval(loadLogs, 10000);


// ============================================================
//  ГРАФИКИ
// ============================================================
let chartSectors = null, chartLogs = null, chartThreat = null;

const CHART_COLORS = {
    bg: 'rgba(160, 160, 160, 0.15)',
    border: '#a0a0a0',
    text: 'rgba(160, 160, 160, 0.8)',
    grid: 'rgba(255, 255, 255, 0.03)',
};

const CHART_OPTIONS = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
        x: {
            grid: { color: CHART_COLORS.grid, drawBorder: false },
            ticks: { color: CHART_COLORS.text, font: { size: 9 } }
        },
        y: {
            grid: { color: CHART_COLORS.grid, drawBorder: false },
            ticks: { color: CHART_COLORS.text, font: { size: 9 }, stepSize: 1 },
            beginAtZero: true,
        }
    }
};

async function loadGraphs() {
    try {
        // График 1
        const res1 = await fetch('/api/isb/graphs/sectors');
        const data1 = (await res1.json()).data || [];
        if (chartSectors) chartSectors.destroy();
        chartSectors = new Chart(document.getElementById('graphSectors'), {
            type: 'bar',
            data: {
                labels: data1.map(d => d.label),
                datasets: [{
                    data: data1.map(d => d.value),
                    backgroundColor: CHART_COLORS.bg,
                    borderColor: CHART_COLORS.border,
                    borderWidth: 1,
                }]
            },
            options: CHART_OPTIONS
        });

        // График 2
        const res2 = await fetch('/api/isb/graphs/logs-24h');
        const data2 = (await res2.json()).data || [];
        if (chartLogs) chartLogs.destroy();
        chartLogs = new Chart(document.getElementById('graphLogs'), {
            type: 'line',
            data: {
                labels: data2.map(d => d.hour),
                datasets: [{
                    data: data2.map(d => d.count),
                    borderColor: CHART_COLORS.border,
                    backgroundColor: 'rgba(160,160,160,0.05)',
                    borderWidth: 1.5,
                    fill: true,
                    tension: 0.3,
                    pointRadius: 2,
                    pointBackgroundColor: CHART_COLORS.border,
                }]
            },
            options: CHART_OPTIONS
        });

        // График 3
        const res3 = await fetch('/api/isb/graphs/threat');
        const data3 = (await res3.json()).data || [];
        if (chartThreat) chartThreat.destroy();
        chartThreat = new Chart(document.getElementById('graphThreat'), {
            type: 'bar',
            data: {
                labels: data3.map(d => d.label),
                datasets: [{
                    data: data3.map(d => d.value),
                    backgroundColor: 'rgba(200,100,100,0.15)',
                    borderColor: '#cc6666',
                    borderWidth: 1,
                }]
            },
            options: { ...CHART_OPTIONS, indexAxis: 'y' }
        });

        document.getElementById('graphsUpdate').textContent =
            new Date().toLocaleTimeString('ru-RU');
    } catch (e) {
        console.error('Графики:', e);
    }
}


// ============================================================
//  УПРАВЛЕНИЕ СОСТАВОМ
// ============================================================
let allEmployees = [];

async function loadEmployees() {
    const container = document.getElementById('employeesTable');
    if (!container) return;
    try {
        const res = await fetch('/api/admin/isb/employees');
        if (!res.ok) {
            container.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--text-muted);">ДОСТУП ЗАПРЕЩЁН</div>';
            return;
        }
        const data = await res.json();
        allEmployees = data.data || [];

        const ACCESS_NAMES = {
            1: 'РЯДОВОЙ', 2: 'ОФИЦЕР', 3: 'СТ. ОФИЦЕР', 4: 'КОМАНДУЮЩИЙ', 5: 'ВЕРХОВНЫЙ'
        };

        const headerHtml = `
            <div class="isb-emp-row header">
                <span></span>
                <span>№ СЛУЖБЫ</span>
                <span>СОТРУДНИК</span>
                <span>ЗВАНИЕ</span>
                <span>УР. ДОСТУПА</span>
                <span>СТАТУС</span>
                <span style="text-align: right;">ДЕЙСТВИЯ</span>
            </div>
        `;

        if (allEmployees.length === 0) {
            container.innerHTML = headerHtml +
                '<div style="text-align: center; padding: 40px; color: var(--text-muted);">НЕТ СОТРУДНИКОВ</div>';
            return;
        }

        const rowsHtml = allEmployees.map(e => {
            const avatarHtml = e.avatar_url
                ? `<div class="isb-emp-avatar"><img src="${e.avatar_url}" alt="${e.username}"></div>`
                : `<div class="isb-emp-avatar">👤</div>`;

            const statusClass = e.is_active ? 'active' : 'inactive';
            const statusText = e.is_active ? 'АКТИВЕН' : 'УВОЛЕН';

            const editBtn = e.is_active
                ? `<button class="isb-emp-action" onclick="openEditEmployeeModal(${e.id})">ПРАВКА</button>`
                : '';

            const fireBtn = e.is_active
                ? `<button class="isb-emp-action danger" onclick="fireEmployeeFromPanel(${e.id}, '${e.username}')">УВОЛИТЬ</button>`
                : '';

            return `
                <div class="isb-emp-row">
                    ${avatarHtml}
                    <span class="isb-emp-number">${e.service_number}</span>
                    <span class="isb-emp-username">${e.username}</span>
                    <span class="isb-emp-rank">${e.rank_name}</span>
                    <span class="isb-emp-access">${ACCESS_NAMES[e.access_level] || '—'}</span>
                    <span class="isb-emp-status ${statusClass}">${statusText}</span>
                    <div class="isb-emp-actions">
                        ${editBtn}
                        ${fireBtn}
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = headerHtml + rowsHtml;
    } catch (err) {
        container.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--text-muted);">ОШИБКА ЗАГРУЗКИ</div>';
        console.error(err);
    }
}

function fireEmployeeFromPanel(id, username) {
    if (!confirm(`УВОЛИТЬ СОТРУДНИКА: ${username}?`)) return;
    fetch(`/api/admin/isb/employees/${id}`, { method: 'DELETE' })
        .then(r => {
            if (r.ok) {
                loadEmployees();
                loadLogs();
            } else {
                alert('ОШИБКА УВОЛЬНЕНИЯ');
            }
        })
        .catch(() => alert('ОШИБКА СОЕДИНЕНИЯ'));
}

function openEditEmployeeModal(id) {
    const emp = allEmployees.find(e => e.id === id);
    if (!emp) return;
    alert(`РЕДАКТИРОВАНИЕ: ${emp.username}\nЗвание: ${emp.rank_name}\nСлужба: ${emp.service_number}\n\n(Модалка в разработке)`);
}

function openHireModal() {
    alert('МОДАЛКА ПРИЁМА В РАЗРАБОТКЕ\n\nПока используй /admin/isb через Swagger.');
}


// ============================================================
//  ПРОВЕРКА СИСТЕМ
// ============================================================
async function checkSystems() {
    try {
        const t = performance.now();
        const res = await fetch('/health');
        const dt = performance.now() - t;
        setStatus('sysAPI', res.ok, res.ok ? `ОК · ${dt.toFixed(0)} МС` : 'ОШИБКА');
    } catch (e) { setStatus('sysAPI', false, 'ОШИБКА'); }

    try {
        const res = await fetch('/api/stats');
        setStatus('sysDB', res.ok, res.ok ? 'ОК' : 'ОШИБКА');
    } catch (e) { setStatus('sysDB', false, 'ОШИБКА'); }

    try {
        const res = await fetch('/api/algorithms');
        const auth = res.status !== 401 && res.status !== 403;
        setStatus('sysAuth', auth, auth ? 'ОК' : 'ОТКАЗ');
    } catch (e) { setStatus('sysAuth', false, 'ОШИБКА'); }

    try {
        const res = await fetch('/api/search?q=test');
        setStatus('sysSearch', res.ok, res.ok ? 'ОК' : 'ОШИБКА');
    } catch (e) { setStatus('sysSearch', false, 'ОШИБКА'); }

    try {
        const res = await fetch('/api/algorithms');
        setStatus('sysAlgo', res.ok, res.ok ? 'ОК' : 'ОШИБКА');
    } catch (e) { setStatus('sysAlgo', false, 'ОШИБКА'); }

    const online = navigator.onLine;
    setStatus('sysConn', online, online ? 'АКТИВНО' : 'ОФЛАЙН');
}

function setStatus(id, ok, text) {
    const el = document.getElementById(id);
    const textEl = document.getElementById(id + 'Text');
    if (!el || !textEl) return;
    el.className = 'isb-indicator' + (ok ? '' : ' danger');
    textEl.textContent = text;
}

checkSystems();
setInterval(checkSystems, 15000);


// ============================================================
//  СТАРТ
// ============================================================
loadAccess();
setInterval(loadAccess, 30000);

setTimeout(() => {
    if (myAccess.level >= 3) {
        loadGraphs();
        setInterval(loadGraphs, 60000);
    }
    if (myAccess.level >= 4) {
        loadEmployees();
        setInterval(loadEmployees, 30000);
    }
}, 1500);