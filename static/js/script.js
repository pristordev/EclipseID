// ============================================================
//  ECLIPSEID · ОСНОВНОЙ СКРИПТ
// ============================================================

// ============================================
//  ГАМБУРГЕР-МЕНЮ
// ============================================
function toggleMenu() {
    const navLinks = document.getElementById('navLinks');
    const hamburger = document.querySelector('.hamburger');
    if (!navLinks || !hamburger) return;
    navLinks.classList.toggle('active');
    hamburger.classList.toggle('active');
}

function closeMenu() {
    const nav = document.getElementById('navLinks');
    const burger = document.querySelector('.hamburger');
    if (nav) nav.classList.remove('active');
    if (burger) burger.classList.remove('active');
}

// ============================================
//  АВАТАРКА: выпадающее меню
// ============================================
function toggleAvatarMenu(event) {
    if (event) event.stopPropagation();
    const menu = document.getElementById('avatarMenu');
    if (!menu) return;
    menu.classList.toggle('active');
}

// ============================================
//  ГЛОБАЛЬНЫЙ ПОИСК
// ============================================
let searchTimeout = null;

function toggleSearch() {
    const modal = document.getElementById('searchModal');
    if (!modal) return;

    if (modal.classList.contains('active')) {
        closeSearch();
    } else {
        modal.classList.add('active');
        setTimeout(() => {
            const input = document.getElementById('searchInput');
            if (input) input.focus();
        }, 100);
    }
}

function closeSearch() {
    const modal = document.getElementById('searchModal');
    if (modal) modal.classList.remove('active');
    const input = document.getElementById('searchInput');
    if (input) input.value = '';
    const results = document.getElementById('searchResults');
    if (results) results.innerHTML = '<div class="search-hint">Начните вводить запрос…</div>';
}

function doSearch(query) {
    if (searchTimeout) clearTimeout(searchTimeout);

    const results = document.getElementById('searchResults');
    if (!results) return;

    query = query.trim();
    if (query.length < 2) {
        results.innerHTML = '<div class="search-hint">Введите минимум 2 символа…</div>';
        return;
    }

    results.innerHTML = '<div class="search-loading">Поиск…</div>';

    searchTimeout = setTimeout(async () => {
        try {
            const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
            const data = await res.json();
            const items = data.results || [];

            if (items.length === 0) {
                results.innerHTML = '<div class="search-empty">Ничего не найдено 😔</div>';
                return;
            }

            const groups = {
                'citizen': { title: '👤 Граждане', items: [] },
                'isb':     { title: '🛡️ Сотрудники ИСБ', items: [] },
                'role':    { title: '🎖️ Роли', items: [] },
                'award':   { title: '🏅 Награды', items: [] },
            };

            items.forEach(item => {
                if (groups[item.type]) groups[item.type].items.push(item);
            });

            let html = '';
            Object.values(groups).forEach(group => {
                if (group.items.length === 0) return;
                html += `<div class="search-section-title">${group.title}</div>`;
                html += group.items.map(item => `
                    <a href="${item.url}" class="search-result">
                        <span class="icon">${item.icon}</span>
                        <div class="info">
                            <div class="title">${item.title}</div>
                            <div class="subtitle">${item.subtitle}</div>
                        </div>
                    </a>
                `).join('');
            });

            results.innerHTML = html;
        } catch (e) {
            results.innerHTML = '<div class="search-empty">Ошибка поиска</div>';
        }
    }, 250);
}

// ============================================
//  ГЛОБАЛЬНЫЕ СОБЫТИЯ
// ============================================
document.addEventListener('click', (e) => {
    // Закрыть меню аватарки при клике вне
    const menu = document.getElementById('avatarMenu');
    const wrap = document.querySelector('.avatar-menu-wrap');
    if (menu && wrap && !wrap.contains(e.target)) {
        menu.classList.remove('active');
    }
});

document.addEventListener('keydown', (e) => {
    // Esc — закрыть всё
    if (e.key === 'Escape') {
        const menu = document.getElementById('avatarMenu');
        if (menu) menu.classList.remove('active');
        closeSearch();
    }

    // Ctrl+K — открыть поиск
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        toggleSearch();
    }

    // "/" — открыть поиск (если не в input)
    if (e.key === '/' && !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) {
        e.preventDefault();
        toggleSearch();
    }
});

// ============================================
//  КНОПКА "ВЫЙТИ" В ГАМБУРГЕРЕ — закрыть меню
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.nav-links a').forEach(link => {
        link.addEventListener('click', () => {
            closeMenu();
        });
    });

    console.log('%c🚀 EclipseID · Система инициализирована', 'color: #00d4aa; font-size: 14px; font-weight: bold;');
});

// ============================================
//  НАСТРОЙКИ: тема и акцент
// ============================================

function toggleSettings(event) {
    if (event) event.stopPropagation();
    const menu = document.getElementById('settingsMenu');
    if (!menu) return;
    menu.classList.toggle('active');
    // закрыть меню аватарки
    const am = document.getElementById('avatarMenu');
    if (am) am.classList.remove('active');
}

function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    updateSettingsUI();
    // закрыть меню
    const menu = document.getElementById('settingsMenu');
    if (menu) menu.classList.remove('active');
}

function setAccent(accent) {
    document.documentElement.setAttribute('data-accent', accent);
    localStorage.setItem('accent', accent);
    updateSettingsUI();
    const menu = document.getElementById('settingsMenu');
    if (menu) menu.classList.remove('active');
}

function updateSettingsUI() {
    const theme = document.documentElement.getAttribute('data-theme') || 'dark';
    const accent = document.documentElement.getAttribute('data-accent') || 'mint';

    // Активная тема
    document.querySelectorAll('[data-theme-set]').forEach(el => {
        el.classList.toggle('active', el.getAttribute('data-theme-set') === theme);
    });

    // Активный акцент
    document.querySelectorAll('[data-accent-set]').forEach(el => {
        el.classList.toggle('active', el.getAttribute('data-accent-set') === accent);
    });
}

// Применяем сохранённые настройки при загрузке
(function() {
    const theme = localStorage.getItem('theme') || 'dark';
    const accent = localStorage.getItem('accent') || 'mint';
    document.documentElement.setAttribute('data-theme', theme);
    document.documentElement.setAttribute('data-accent', accent);
})();

document.addEventListener('DOMContentLoaded', updateSettingsUI);

// Закрытие при клике вне
document.addEventListener('click', (e) => {
    const menu = document.getElementById('settingsMenu');
    const btn = document.querySelector('.settings-btn');
    if (menu && btn && !menu.contains(e.target) && !btn.contains(e.target)) {
        menu.classList.remove('active');
    }
    // при клике на пустое место закрыть и меню аватарки
    const am = document.getElementById('avatarMenu');
    const ab = document.querySelector('.avatar-btn');
    if (am && ab && !am.contains(e.target) && !ab.contains(e.target)) {
        am.classList.remove('active');
    }
});