const API = '/api';

// ─── Auth / Token ───────────────────────────────────────────
const TOKEN_KEY = 'bmp_jwt';
function getToken()   { return localStorage.getItem(TOKEN_KEY); }
function setToken(t)  { localStorage.setItem(TOKEN_KEY, t); }
function removeToken(){ localStorage.removeItem(TOKEN_KEY); }
function decodeToken(t) {
    try { return JSON.parse(atob(t.split('.')[1].replace(/-/g,'+').replace(/_/g,'/'))); }
    catch { return null; }
}

function showLoginOverlay() {
    document.getElementById('login-overlay').style.display = 'flex';
    document.getElementById('login-pass').value = '';
}
function hideLoginOverlay() {
    document.getElementById('login-overlay').style.display = 'none';
}

function applyRoleUI(user) {
    document.getElementById('user-name').textContent =
        ((user.prenom || '') + ' ' + (user.nom || '')).trim();
    document.getElementById('user-role-badge').textContent = user.role;
    document.getElementById('user-info').style.display = 'flex';
    const adminNav = document.getElementById('nav-admin');
    if (adminNav) adminNav.style.display = user.role === 'admin' ? '' : 'none';
    loadModules();
}

async function doLogin() {
    const login = document.getElementById('login-user').value.trim();
    const pass  = document.getElementById('login-pass').value;
    const errEl = document.getElementById('login-error');
    errEl.style.display = 'none';
    if (!login || !pass) {
        errEl.textContent = 'Identifiant et mot de passe requis';
        errEl.style.display = 'block';
        return;
    }
    try {
        const res = await fetch(API + '/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ login, password: pass })
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
            errEl.textContent = data.error || 'Identifiants invalides';
            errEl.style.display = 'block';
            return;
        }
        setToken(data.token);
        _sessionExpired = false;
        hideLoginOverlay();
        applyRoleUI(data.user);
        initRefs().then(() => { loadDashboard(); loadNotifications(); });
    } catch (e) {
        errEl.textContent = e.message;
        errEl.style.display = 'block';
    }
}

function doLogout() {
    removeToken();
    document.getElementById('user-name').textContent = '';
    document.getElementById('user-info').style.display = 'none';
    showLoginOverlay();
}

// ─── Déconnexion automatique après 30 min d'inactivité ───
let inactivityTimeout;

function resetInactivityTimer() {
    clearTimeout(inactivityTimeout);
    inactivityTimeout = setTimeout(doLogout, 30 * 60 * 1000); // 30 minutes
}

['mousemove', 'keydown', 'mousedown', 'touchstart'].forEach(event => {
    window.addEventListener(event, resetInactivityTimer);
});

resetInactivityTimer();

// ─── État global ───────────────────────────────────────────
let _currentBudgetId  = null;   // pour modal voter
let _currentBcId      = null;   // pour modal imputer / valider
let _currentContratId = null;   // pour modal reconduire
let _refs  = { fournisseurs: [], entites: [], projets: [], lignes: [], contrats: [] };
let _cache = { projets: [], taches: [], contrats: [], contacts: [], fournisseurs: [] };

// ─── Utilitaires ───────────────────────────────────────────

function showMsg(text, ok = true) {
    const el = document.getElementById('msg');
    el.textContent = text;
    el.style.background = ok ? '#27ae60' : '#c0392b';
    el.style.display = 'block';
    setTimeout(() => { el.style.display = 'none'; }, 3000);
}

// ── Sécurité : échappement HTML systématique pour innerHTML ──────────────
// Utiliser _h() pour toute donnée utilisateur insérée dans le DOM via innerHTML.
const _hDiv = document.createElement('div');
function _h(s) {
    if (s == null) return '';
    _hDiv.textContent = String(s);
    return _hDiv.innerHTML;
}

function fmt(n) {
    if (n == null || n === '') return '-';
    return Number(n).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtDate(d) {
    if (!d) return '-';
    const iso = _toISODate(d);
    if (!iso) return '-';
    const [y, m, j] = iso.split('-');
    return `${j}/${m}/${y}`;
}

function _toISODate(v) {
    if (!v) return '';
    const s = String(v);
    if (/^\d{4}-\d{2}-\d{2}/.test(s)) return s.substring(0, 10);
    const dt = new Date(s);
    if (!isNaN(dt.getTime())) return dt.toISOString().substring(0, 10);
    return '';
}

function badge(statut) {
    if (!statut) return '<span class="badge bg-default">-</span>';
    const map = {
        'BROUILLON':  'bg-brouillon',
        'EN_ATTENTE': 'bg-en-attente',
        'VALIDE':     'bg-valide',
        'IMPUTE':     'bg-impute',
        'SOLDE':      'bg-solde',
        'ANNULE':     'bg-annule',
        'REFUSE':     'bg-refuse',
        'ACTIF':      'bg-actif',
        'RECONDUIT':  'bg-valide',
        'EXPIRE':     'bg-expire',
        'RESILIE':    'bg-annule',
        'TERMINE':    'bg-solde',
        'VOTE':       'bg-vote',
        'En cours':   'bg-en-cours',
        'Terminé':    'bg-termine',
        'Planifié':   'bg-en-attente',
        'Suspendu':   'bg-annule',
        'A faire':    'bg-brouillon',
        'Bloqué':     'bg-annule',
        'En attente': 'bg-en-attente',
        'HAUTE':      'bg-expire',
        'NORMALE':    'bg-valide',
        'BASSE':      'bg-impute',
    };
    const cls = map[statut] || 'bg-default';
    return `<span class="badge ${cls}">${statut}</span>`;
}

function alerteBadge(niveau) {
    const map = {
        'EXPIRE':    'bg-expire',
        'CRITIQUE':  'bg-critique',
        'ATTENTION': 'bg-attention',
        'INFO':      'bg-info',
        'OK':        'bg-ok',
    };
    return `<span class="badge ${map[niveau] || 'bg-default'}">${niveau || 'OK'}</span>`;
}

function progressBar(val, max) {
    if (!max || max == 0) return '-';
    const pct = Math.min(Math.round(val / max * 100), 100);
    const cls = pct >= 80 ? 'alert' : (pct >= 60 ? 'warning' : '');
    return `<div class="progress-bar-wrap" title="${pct}%">
        <div class="progress-bar-fill ${cls}" style="width:${pct}%"></div>
    </div><small>${pct}%</small>`;
}

let _sessionExpired = false; // évite les déconnexions multiples simultanées
let _quillRapport = null;   // instance Quill pour rapport de réunion

async function apiFetch(path, opts = {}) {
    const token = getToken();
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = 'Bearer ' + token;
    const res = await fetch(API + path, { headers, ...opts });
    if (res.status === 401) {
        if (!_sessionExpired) {
            _sessionExpired = true;
            removeToken();
            showLoginOverlay();
        }
        throw new Error('Session expirée, veuillez vous reconnecter');
    }
    if (res.status === 403) {
        throw new Error('Accès interdit — droits insuffisants');
    }
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || `HTTP ${res.status}`);
    }
    return res.json();
}

function openModal(id)  { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }

// ─── Échap ferme les modals ────────────────────────────────
document.addEventListener('keydown', e => {
    if (e.key !== 'Escape') return;
    const open = document.querySelector('.modal-overlay.open');
    if (open) open.classList.remove('open');
});

// ─── Tri des colonnes ──────────────────────────────────────
const _sort = {};

function _sortedData(arr, tableId) {
    const s = _sort[tableId];
    if (!s || !s.field) return arr;
    return [...arr].sort((a, b) => {
        let va = a[s.field] ?? '';
        let vb = b[s.field] ?? '';
        const fa = parseFloat(va), fb = parseFloat(vb);
        if (!isNaN(fa) && !isNaN(fb)) return s.asc ? fa - fb : fb - fa;
        return s.asc
            ? String(va).localeCompare(String(vb), 'fr', { sensitivity: 'base' })
            : String(vb).localeCompare(String(va), 'fr', { sensitivity: 'base' });
    });
}

function _updateSortHeaders(tableId) {
    const s = _sort[tableId];
    document.querySelectorAll(`[data-table="${tableId}"] th[data-sort]`).forEach(th => {
        th.classList.remove('th-asc', 'th-desc');
        if (s && th.dataset.sort === s.field)
            th.classList.add(s.asc ? 'th-asc' : 'th-desc');
    });
}

function sortTable(tableId, field) {
    const cur = _sort[tableId] || {};
    _sort[tableId] = { field, asc: cur.field === field ? !cur.asc : true };
    const renders = { bc: _renderBcRows, contrats: _renderContratsRows, lignes: _renderLignesRows };
    if (renders[tableId]) renders[tableId]();
}

// ─── Filtres persistants ───────────────────────────────────
const _FP = 'bmp_flt_';
function _saveFilter(id) {
    const el = document.getElementById(id);
    if (el) localStorage.setItem(_FP + id, el.value);
}
function _restoreFilter(id) {
    const el = document.getElementById(id);
    if (el) { const v = localStorage.getItem(_FP + id); if (v !== null) el.value = v; }
}
function _restoreFilters(...ids) { ids.forEach(_restoreFilter); }
function _clearFilters(...ids) {
    ids.forEach(id => {
        localStorage.removeItem(_FP + id);
        const el = document.getElementById(id);
        if (el) { if (el.tagName === 'SELECT') el.selectedIndex = 0; else el.value = ''; }
    });
}

function resetBcFilters() {
    _clearFilters('bc-filter-statut', 'bc-filter-entite', 'bc-search');
    loadBC();
}
function resetContratsFilters() {
    _clearFilters('contrat-filter-statut', 'contrat-search');
    loadContrats();
}
function resetLignesFilters() {
    _clearFilters('lignes-filter-budget', 'lignes-search');
    loadAllLignes();
}

// ─── Pagination ────────────────────────────────────────────
const _pagination = {}; // { tableId: { page, perPage } }
const _PER_PAGE   = 25;

function _paginate(arr, tableId) {
    const p = _pagination[tableId] || (_pagination[tableId] = { page: 1, perPage: _PER_PAGE });
    const start = (p.page - 1) * p.perPage;
    return arr.slice(start, start + p.perPage);
}

function _renderPagination(tableId, totalCount) {
    const containerId = tableId + '-pagination';
    const el = document.getElementById(containerId);
    if (!el) return;
    const p = _pagination[tableId] || { page: 1, perPage: _PER_PAGE };
    const totalPages = Math.ceil(totalCount / p.perPage);
    if (totalPages <= 1) { el.innerHTML = ''; return; }
    el.innerHTML =
        `<button onclick="_goPage('${tableId}',${p.page - 1})" ${p.page <= 1 ? 'disabled' : ''}>&#9664; Préc.</button>` +
        `<span class="pg-info">Page <strong>${p.page}</strong> / ${totalPages} &nbsp;(${totalCount} résultats)</span>` +
        `<button onclick="_goPage('${tableId}',${p.page + 1})" ${p.page >= totalPages ? 'disabled' : ''}>Suiv. &#9654;</button>`;
}

function _goPage(tableId, page) {
    if (!_pagination[tableId]) _pagination[tableId] = { page: 1, perPage: _PER_PAGE };
    _pagination[tableId].page = page;
    const renders = { bc: _renderBcRows, contrats: _renderContratsRows };
    if (renders[tableId]) renders[tableId]();
}

function _resetPage(tableId) {
    if (_pagination[tableId]) _pagination[tableId].page = 1;
}

function fillSelect(selId, items, valKey, labelFn) {
    const sel = document.getElementById(selId);
    if (!sel) return;
    const first = sel.options[0];
    sel.innerHTML = '';
    sel.appendChild(first);
    (items || []).forEach(item => {
        const opt = document.createElement('option');
        opt.value = item[valKey];
        opt.textContent = typeof labelFn === 'function' ? labelFn(item) : item[labelFn];
        sel.appendChild(opt);
    });
}

// ─── Navigation ────────────────────────────────────────────

const loaders = {
    dashboard:     loadDashboard,
    budget:        loadBudget,
    bc:            loadBC,
    contrats:      loadContrats,
    projets:       loadProjets,
    taches:        loadTaches,
    kanban:        loadKanban,
    fournisseurs:  loadFournisseurs,
    contacts:      loadContacts,
    services:      loadServices,
    etp:           loadETP,
    gantt:         loadGantt,
    notifications: loadNotifications,
    tpe:           loadTpe,
    admin:         loadAdminUsers,
};

function showView(name) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.querySelectorAll('nav button').forEach(b => b.classList.remove('active'));
    const view = document.getElementById('view-' + name);
    if (view) {
        view.classList.add('active');
        // Restaurer les filtres depuis localStorage
        view.querySelectorAll('.toolbar input[id], .toolbar select[id]').forEach(el => _restoreFilter(el.id));
        // Masquer les bandeaux d'info temporaires
        view.querySelectorAll('[id$="-pdf-info"], [id$="-info-msg"]').forEach(el => {
            el.style.display = 'none';
        });
    }
    const navBtns = document.querySelectorAll('nav button');
    const idx = Object.keys(loaders).indexOf(name);
    if (idx >= 0 && navBtns[idx]) navBtns[idx].classList.add('active');
    if (loaders[name]) loaders[name]();
}

// ─── Init (références pour les selects) ────────────────────

async function initRefs() {
    try {
        const data = await apiFetch('/referentiels');
        _refs.fournisseurs  = data.fournisseurs  || [];
        _refs.entites       = data.entites       || [];
        _refs.projets       = data.projets       || [];
        _refs.lignes        = data.lignes        || [];
        _refs.applications  = data.applications  || [];
        _refs.contrats      = data.contrats      || [];

        const fLabel = f => f.nom;
        const eLabel = e => e.code ? `${e.code} – ${e.nom}` : e.nom;
        const pLabel = p => p.code ? `${p.code} – ${p.nom}` : p.nom;
        const lLabel = l => {
            const solde = fmt(l.montant_solde || 0);
            return `${l.libelle || 'Ligne #' + l.id} — Solde: ${solde} €`;
        };
        const cLabel = c => c.numero_contrat ? `${c.numero_contrat}${c.objet ? ' – ' + c.objet : ''}` : `Contrat #${c.id}`;

        fillSelect('budget-entite',        _refs.entites,      'id', eLabel);
        fillSelect('bc-fournisseur',       _refs.fournisseurs, 'id', fLabel);
        fillSelect('bc-entite',            _refs.entites,      'id', eLabel);
        fillSelect('bc-filter-entite',     _refs.entites,      'id', eLabel);
        fillSelect('bc-ligne',             _refs.lignes,       'id', lLabel);
        fillSelect('contrat-fournisseur',  _refs.fournisseurs, 'id', fLabel);
        fillSelect('tache-projet',           _refs.projets,      'id', pLabel);
        fillSelect('tache-filter-projet',    _refs.projets,      'id', pLabel);
        fillSelect('kanban-filter-projet',   _refs.projets,      'id', pLabel);
        fillSelect('edit-tache-projet',        _refs.projets,      'id', pLabel);
        fillSelect('edit-contrat-fournisseur', _refs.fournisseurs, 'id', fLabel);

        // Selects du modal édition BC
        fillSelect('edit-bc-fournisseur', _refs.fournisseurs, 'id', fLabel);
        fillSelect('edit-bc-entite',      _refs.entites,      'id', eLabel);
        fillSelect('edit-bc-ligne',       _refs.lignes,       'id', lLabel);
        fillSelect('edit-bc-projet',      _refs.projets,      'id', pLabel);
        fillSelect('edit-bc-contrat',     _refs.contrats,     'id', cLabel);

        // Services pour les selects projet
        const services = data.services || [];
        const sLabel = s => s.code ? `${s.code} – ${s.nom}` : s.nom;
        fillSelect('projet-service',       services, 'id', sLabel);
        fillSelect('edit-projet-service',  services, 'id', sLabel);

        // Lignes budgétaires pour l'imputation
        fillSelect('imputer-ligne', _refs.lignes, 'id', lLabel);
    } catch (e) {
        console.warn('initRefs:', e);
    }
}

// ─── DASHBOARD ─────────────────────────────────────────────

let _chartNature = null;
let _chartEntite = null;

async function loadDashboard() {
    try {
        const d = await apiFetch('/dashboard');
        document.getElementById('kpi-projets').textContent    = d.kpi_projets ?? '-';
        document.getElementById('kpi-budget').textContent     = fmt(d.kpi_budget);
        document.getElementById('kpi-bc').textContent         = d.kpi_bons_commande ?? '-';
        document.getElementById('kpi-montant-bc').textContent = fmt(d.kpi_montant_bc);
        document.getElementById('kpi-contrats').textContent   = d.kpi_contrats ?? '-';
        document.getElementById('kpi-alertes').textContent    = d.kpi_alertes_contrats ?? '-';
        document.getElementById('kpi-bc-attente').textContent = d.kpi_bc_attente ?? '-';
        const kpiLignesEl = document.getElementById('kpi-alertes-lignes');
        if (kpiLignesEl) {
            kpiLignesEl.textContent = d.kpi_alertes_lignes ?? '-';
            kpiLignesEl.closest('.kpi-card')?.classList.toggle('alert', (d.kpi_alertes_lignes || 0) > 0);
        }

        const tbody = document.getElementById('dashboard-alertes-tbody');
        tbody.innerHTML = (d.alertes_contrats || []).map(c => `
            <tr class="alerte-${(c.niveau_alerte||'ok').toLowerCase()}">
                <td>${c.numero_contrat || '-'}</td>
                <td>${c.objet || '-'}</td>
                <td>${c.fournisseur_nom || '-'}</td>
                <td>${fmtDate(c.date_fin)}</td>
                <td>${c.jours_restants != null ? c.jours_restants + ' j.' : '-'}</td>
                <td>${alerteBadge(c.niveau_alerte)}</td>
            </tr>`).join('');

        // ── Charts ──────────────────────────────────────────
        if (typeof Chart === 'undefined') return;

        // Doughnut: répartition par nature
        const natData = d.repartition_nature || [];
        if (_chartNature) _chartNature.destroy();
        const ctxN = document.getElementById('chart-nature');
        if (ctxN && natData.length) {
            const colors = ['#2563a8', '#27ae60', '#f39c12', '#8e44ad', '#e74c3c'];
            _chartNature = new Chart(ctxN, {
                type: 'doughnut',
                data: {
                    labels: natData.map(n => n.nature),
                    datasets: [{
                        data: natData.map(n => n.vote),
                        backgroundColor: natData.map((_, i) => colors[i % colors.length]),
                    }]
                },
                options: {
                    plugins: {
                        legend: { position: 'bottom', labels: { font: { size: 11 } } },
                        tooltip: { callbacks: { label: ctx => ` ${ctx.label}: ${fmt(ctx.raw)} €` } }
                    },
                    cutout: '60%',
                }
            });
        }

        // Bar: engagement par entité
        const entData = d.engagement_entite || [];
        if (_chartEntite) _chartEntite.destroy();
        const ctxE = document.getElementById('chart-entite');
        if (ctxE && entData.length) {
            _chartEntite = new Chart(ctxE, {
                type: 'bar',
                data: {
                    labels: entData.map(e => e.entite),
                    datasets: [
                        { label: 'Voté', data: entData.map(e => e.vote),   backgroundColor: '#bfdbfe' },
                        { label: 'Engagé', data: entData.map(e => e.engage), backgroundColor: '#2563a8' },
                    ]
                },
                options: {
                    indexAxis: 'y',
                    plugins: {
                        legend: { position: 'bottom', labels: { font: { size: 11 } } },
                        tooltip: { callbacks: { label: ctx => ` ${ctx.dataset.label}: ${fmt(ctx.raw)} €` } }
                    },
                    scales: {
                        x: { ticks: { callback: v => fmt(v) + ' €', font: { size: 10 } } },
                        y: { ticks: { font: { size: 11 } } }
                    },
                }
            });
        }
    } catch (e) { console.error('Dashboard:', e); }
}

// ─── BUDGETS ───────────────────────────────────────────────

let _lignesSelectId = null; // ligne sélectionnée dans la vue lignes

function exportBudget() {
    const exercice = document.getElementById('export-exercice')?.value || new Date().getFullYear();
    const token = getToken();
    fetch(`/api/export/budget?exercice=${exercice}`, {
        headers: { 'Authorization': 'Bearer ' + token }
    })
    .then(res => {
        if (!res.ok) throw new Error('Erreur export');
        return res.blob();
    })
    .then(blob => {
        const url  = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href  = url;
        link.download = `Budget_DSI_${exercice}_${new Date().toISOString().slice(0,10)}.xlsx`;
        link.click();
        URL.revokeObjectURL(url);
    })
    .catch(e => showMsg(e.message || 'Erreur export', false));
}

function switchBudgetSubTab(tab) {
    document.querySelectorAll('.budget-subtab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.budget-subview').forEach(v => v.classList.remove('active'));
    const idx = tab === 'lignes' ? 1 : 0;
    document.querySelectorAll('.budget-subtab')[idx].classList.add('active');
    document.getElementById(`budget-sub-${tab}`).classList.add('active');
    if (tab === 'lignes') loadAllLignes();
}

function _renderLignesRows() {
    const search = (document.getElementById('lignes-search')?.value || '').toLowerCase();
    let lignes = _lignesCache;
    if (search) {
        lignes = lignes.filter(l =>
            (l.libelle || '').toLowerCase().includes(search) ||
            (l.application_nom || '').toLowerCase().includes(search) ||
            (l.fournisseur_nom || '').toLowerCase().includes(search)
        );
    }
    lignes = _sortedData(lignes, 'lignes');

    // Bandeau alerte
    const banner = document.getElementById('lignes-alerte-banner');
    if (banner) {
        const nb100 = _lignesCache.filter(l => (l.taux_engagement || 0) > 100).length;
        const nb90  = _lignesCache.filter(l => (l.taux_engagement || 0) >= 90 && (l.taux_engagement || 0) <= 100).length;
        if (nb100 > 0) {
            banner.className = 'alert-banner danger';
            banner.textContent = `${nb100} ligne(s) en DÉPASSEMENT budgétaire (>100%)${nb90 > 0 ? ` — ${nb90} ligne(s) proche(s) du seuil (≥90%)` : ''}`;
            banner.style.display = '';
        } else if (nb90 > 0) {
            banner.className = 'alert-banner';
            banner.textContent = `${nb90} ligne(s) proche(s) du seuil (≥90% engagé)`;
            banner.style.display = '';
        } else {
            banner.style.display = 'none';
        }
    }

    const tbody = document.getElementById('lignes-tbody');
    if (!tbody) return;
    if (!lignes.length) {
        tbody.innerHTML = '<tr><td colspan="12" style="text-align:center;color:#999;font-style:italic;padding:18px;">Aucune ligne trouvée.</td></tr>';
        return;
    }
    tbody.innerHTML = lignes.map((l, i) => {
        const taux = l.taux_engagement || 0;
        const alerte = l.alerte
            ? '<span style="color:#e74c3c;font-weight:bold;">⚠ SEUIL</span>'
            : '<span style="color:#27ae60;font-weight:bold;">✓ OK</span>';
        const solde = parseFloat(l.montant_solde || 0);
        const soldeColor = solde < 0 ? 'color:#e74c3c;font-weight:bold;' : 'color:#27ae60;';
        const engageCls = taux > 100 ? 'row-depasse' : taux >= 90 ? 'row-alerte' : taux > 0 ? 'row-ok' : '';
        const selCls = _lignesSelectId === l.id ? ' selected' : '';
        return `<tr class="ligne-row${selCls} ${engageCls}" data-id="${l.id}" onclick="selectLigne(${l.id}, '${(l.libelle||'Ligne #'+l.id).replace(/['\u2018\u2019]/g,"&#39;")}')">
            <td>${i+1}</td>
            <td>${l.libelle || '-'}</td>
            <td>${l.application_nom || '-'}</td>
            <td>${l.fournisseur_nom || '-'}</td>
            <td style="text-align:right;">${fmt(l.montant_vote)}</td>
            <td style="text-align:right;">${fmt(l.montant_engage)}</td>
            <td style="text-align:right;${soldeColor}">${fmt(solde)}</td>
            <td style="text-align:center;">${taux} %</td>
            <td style="text-align:center;">${alerte}</td>
            <td style="font-size:.82em;color:#2563a8;font-weight:600;">${l.note || ''}</td>
            <td style="font-size:.78em;color:#666;">${l.budget_label || '-'}</td>
            <td style="text-align:center;" onclick="event.stopPropagation()">
                <button class="btn btn-warning btn-sm" onclick="editLigne(${l.id})">&#9998; Modifier</button>
            </td>
        </tr>`;
    }).join('');
    _updateSortHeaders('lignes');
    // Remettre la sélection si toujours présente
    if (_lignesSelectId) selectLigne(_lignesSelectId, null, true);
}

async function loadAllLignes() {
    try {
        _saveFilter('lignes-filter-budget'); _saveFilter('lignes-search');
        const budgetId = document.getElementById('lignes-filter-budget')?.value || '';
        const url = budgetId ? `/lignes?budget_id=${budgetId}` : '/lignes';
        const data = await apiFetch(url);
        _lignesCache = data.list || [];
        _renderLignesRows();
    } catch (e) { showMsg('Erreur chargement lignes', false); }
}

async function selectLigne(ligneId, libelle, silent) {
    _lignesSelectId = ligneId;
    // Highlight via data-id
    document.querySelectorAll('.ligne-row').forEach(r =>
        r.classList.toggle('selected', r.dataset.id == ligneId)
    );
    // Titre panneau
    if (libelle) document.getElementById('lignes-bc-titre').textContent = `BCs imputés — ${libelle}`;
    const btn = document.getElementById('lignes-bc-ouvrir-btn');
    try {
        const data = await apiFetch(`/ligne/${ligneId}/bcs`);
        const bcs = data.bcs || [];
        btn.style.display = bcs.length ? '' : 'none';
        btn.dataset.ligneId = ligneId;
        const tbody = document.getElementById('lignes-bc-tbody');
        if (!bcs.length) {
            tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;color:#555;padding:14px;font-style:italic;">Aucun BC imputé sur cette ligne.</td></tr>';
            return;
        }
        tbody.innerHTML = bcs.map(b => `<tr>
            <td style="font-weight:bold;">${b.numero_bc || '-'}</td>
            <td>${b.objet || '-'}</td>
            <td>${b.fournisseur_nom || '-'}</td>
            <td style="text-align:right;">${fmt(b.montant_ttc)} €</td>
            <td>${fmtDate(b.date_imputation) || '-'}</td>
            <td>${fmtDate(b.date_solde) || '-'}</td>
            <td>${badge(b.statut)}</td>
            <td style="color:#aaa;">${b.projet_nom || '-'}</td>
            <td style="color:#2980b9;">${b.contrat_numero ? '&#128196; ' + b.contrat_numero : '<span style="color:#555">-</span>'}</td>
        </tr>`).join('');
    } catch (e) { if (!silent) showMsg('Erreur chargement BCs de la ligne', false); }
}

function ouvrirBCdeLigne() {
    showView('bc');
}

let _lignesCache = [];   // cache des lignes chargées pour editLigne()
let _budgetsList  = [];  // cache des budgets pour le select modal

function _fillLigneModal(data) {
    // Remplir le select budget
    const sel = document.getElementById('edit-ligne-budget');
    sel.innerHTML = '<option value="">-- Sélectionner un budget --</option>';
    _budgetsList.forEach(b => {
        const opt = document.createElement('option');
        opt.value = b.id;
        opt.textContent = `${b.entite_code || b.entite_nom || '?'} — ${b.nature || '?'} ${b.exercice || '?'}`;
        if (data && data.budget_id == b.id) opt.selected = true;
        sel.appendChild(opt);
    });
    // Remplir select application
    const appSel = document.getElementById('edit-ligne-application');
    appSel.innerHTML = '<option value="">-- Aucune --</option>';
    (_refs.applications || []).forEach(a => {
        const opt = document.createElement('option');
        opt.value = a.id;
        opt.textContent = a.nom;
        if (data && data.application_id == a.id) opt.selected = true;
        appSel.appendChild(opt);
    });
    // Remplir select fournisseur
    fillSelect('edit-ligne-fournisseur', _refs.fournisseurs, 'id', f => f.nom);
    if (data) {
        document.getElementById('edit-ligne-id').value              = data.id || '';
        document.getElementById('edit-ligne-libelle').value         = data.libelle || '';
        document.getElementById('edit-ligne-montant-prevu').value   = data.montant_prevu || '';
        document.getElementById('edit-ligne-montant-vote').value    = data.montant_vote || '';
        document.getElementById('edit-ligne-note').value            = data.note || '';
        document.getElementById('edit-ligne-nature').value          = data.nature || 'FONCTIONNEMENT';
        document.getElementById('edit-ligne-statut').value          = data.statut || 'ACTIF';
        document.getElementById('edit-ligne-fournisseur').value     = data.fournisseur_id || '';
    } else {
        document.getElementById('edit-ligne-id').value = '';
        document.getElementById('edit-ligne-libelle').value = '';
        document.getElementById('edit-ligne-montant-prevu').value = '';
        document.getElementById('edit-ligne-montant-vote').value = '';
        document.getElementById('edit-ligne-note').value = '';
        document.getElementById('edit-ligne-nature').value = 'FONCTIONNEMENT';
        document.getElementById('edit-ligne-statut').value = 'ACTIF';
        document.getElementById('edit-ligne-fournisseur').value = '';
        // Pré-sélectionner le budget du filtre actif
        const filterBudget = document.getElementById('lignes-filter-budget').value;
        if (filterBudget) document.getElementById('edit-ligne-budget').value = filterBudget;
    }
}

function openAddLigne() {
    document.getElementById('edit-ligne-titre').textContent = 'Nouvelle ligne budgétaire';
    _fillLigneModal(null);
    openModal('modal-edit-ligne');
}

function editLigne(ligneId) {
    const data = _lignesCache.find(l => l.id === ligneId);
    if (!data) { showMsg('Rechargez la liste avant de modifier', false); return; }
    document.getElementById('edit-ligne-titre').textContent = `Modifier — ${data.libelle || 'Ligne #' + ligneId}`;
    _fillLigneModal(data);
    openModal('modal-edit-ligne');
}

async function saveLigne() {
    const id       = document.getElementById('edit-ligne-id').value;
    const budgetId = document.getElementById('edit-ligne-budget').value;
    const libelle  = document.getElementById('edit-ligne-libelle').value.trim();
    if (!budgetId) { showMsg('Sélectionnez un budget', false); return; }
    if (!libelle)  { showMsg('Le libellé est obligatoire', false); return; }
    const body = {
        budget_id:        parseInt(budgetId),
        libelle,
        application_id:   document.getElementById('edit-ligne-application').value || null,
        fournisseur_id:   document.getElementById('edit-ligne-fournisseur').value || null,
        montant_prevu:    parseFloat(document.getElementById('edit-ligne-montant-prevu').value) || 0,
        montant_vote:     parseFloat(document.getElementById('edit-ligne-montant-vote').value) || 0,
        nature:           document.getElementById('edit-ligne-nature').value,
        note:             document.getElementById('edit-ligne-note').value.trim() || null,
        statut:           document.getElementById('edit-ligne-statut').value,
    };
    const url    = id ? `/ligne/${id}` : '/ligne';
    const method = id ? 'PUT' : 'POST';
    const res = await apiFetch(url, { method, body: JSON.stringify(body) });
    if (res.success) {
        showMsg(id ? 'Ligne mise à jour' : 'Ligne créée');
        closeModal('modal-edit-ligne');
        loadAllLignes();
        loadBudget(); // recalculer les agrégats budget
    } else {
        showMsg(res.error || 'Erreur lors de l\'enregistrement', false);
    }
}

let _currentBudgetPermId = null;

function _currentUserRole() {
    const p = decodeToken(getToken());
    return p ? p.role : 'lecteur';
}
function _currentUserId() {
    const p = decodeToken(getToken());
    return p ? p.sub : null;
}

async function loadBudget() {
    try {
        const exercice = document.getElementById('export-exercice')?.value || new Date().getFullYear();
        const data = await apiFetch(`/budget?exercice=${exercice}`);
        _budgetsList = data.details || [];
        const userRole = _currentUserRole();

        // Zone "Faire budget N+1" visible pour admin seulement
        const zoneDup = document.getElementById('zone-dupliquer-budget');
        if (zoneDup) zoneDup.style.display = userRole === 'admin' ? 'flex' : 'none';

        // Afficher/masquer le formulaire "Nouveau budget"
        const newCard = document.getElementById('budget-new-card');
        if (newCard) newCard.style.display = userRole === 'lecteur' ? 'none' : '';

        // Afficher message vide si aucun budget et non-admin
        const emptyMsg  = document.getElementById('budget-empty-msg');
        const tableWrap = document.getElementById('budget-table-wrap');
        const isEmpty = _budgetsList.length === 0;
        if (emptyMsg)  emptyMsg.style.display  = isEmpty ? '' : 'none';
        if (tableWrap) tableWrap.style.display  = isEmpty ? 'none' : '';

        // Alimenter le filtre budget de la vue lignes (reset + repeupler)
        const filterSel = document.getElementById('lignes-filter-budget');
        if (filterSel) {
            filterSel.innerHTML = '<option value="">-- Tous les budgets --</option>';
            _budgetsList.forEach(b => {
                const opt = document.createElement('option');
                opt.value = b.id;
                opt.textContent = `${b.entite_code || b.entite_nom || '?'} — ${b.nature || '?'} ${b.exercice || '?'}`;
                filterSel.appendChild(opt);
            });
        }

        const tbody = document.getElementById('budget-tbody');
        tbody.innerHTML = _budgetsList.map(b => {
            const vote     = b.montant_vote   || 0;
            const engage   = b.montant_engage || 0;
            const label    = `${b.entite_code || b.entite_nom || '?'} — ${b.exercice || '?'} (${b.nature || '?'})`;
            const labelEsc = label.replace(/['\u2018\u2019]/g, "\\'");
            const canWrite = userRole === 'admin' || b.user_perm === 'gestionnaire';
            const canPerms = userRole === 'admin' || b.user_perm === 'gestionnaire';
            const taux = vote > 0 ? engage / vote * 100 : 0;
            const rowCls = taux > 100 ? 'row-depasse' : taux >= 90 ? 'row-alerte' : vote > 0 ? 'row-ok' : '';
            return `<tr class="${rowCls}">
                <td>${b.id}</td>
                <td>${b.entite_code || b.entite_nom || '-'}</td>
                <td>${b.exercice || '-'}</td>
                <td>${b.nature || '-'}</td>
                <td>${fmt(b.montant_previsionnel)}</td>
                <td>${fmt(vote)}</td>
                <td>${fmt(engage)}</td>
                <td>${fmt(b.montant_paye)}</td>
                <td>${progressBar(engage, vote)}</td>
                <td>${badge(b.statut)}</td>
                <td style="text-align:center;">
                    <button class="btn btn-info btn-sm" onclick="openBudgetDetail(${b.id}, '${labelEsc}')">Lignes &amp; BC</button>
                </td>
                <td style="white-space:nowrap;">
                    ${canPerms ? `<button class="btn btn-sm" style="background:#6c757d;color:#fff;" onclick="openBudgetPerms(${b.id}, '${labelEsc}')">&#128274; Accès</button>` : ''}
                    ${canWrite ? `<button class="btn btn-success btn-sm" onclick="openVoterBudget(${b.id}, ${vote})">Voter</button>` : ''}
                    ${userRole === 'admin' ? `<button class="btn btn-danger btn-sm" onclick="deleteBudget(${b.id})">Suppr.</button>` : ''}
                </td>
            </tr>`;
        }).join('');
    } catch (e) { showMsg('Erreur chargement budgets', false); }
}

async function dupliquerBudget() {
    const exercice = parseInt(document.getElementById('export-exercice')?.value || new Date().getFullYear());
    const target = exercice + 1;
    const taux = parseFloat(document.getElementById('syntec-taux')?.value ?? 3.5);
    if (!confirm(`Créer le budget ${target} en dupliquant la structure ${exercice} ?\n\nIndice Syntec appliqué : +${taux}%\nMontants prévisionnels = engagé réel ${exercice} × (1 + ${taux}%)`)) return;
    try {
        const res = await apiFetch('/budget/dupliquer', {
            method: 'POST',
            body: JSON.stringify({ source_exercice: exercice, target_exercice: target, taux_revalorisation: taux })
        });
        if (res.success) {
            showMsg(`Budget ${target} créé : ${res.budgets_crees} budget(s), ${res.lignes_creees} ligne(s)`);
            document.getElementById('export-exercice').value = target;
            loadBudget();
        } else {
            showMsg(res.error || 'Erreur', false);
        }
    } catch (e) { showMsg(e.message || 'Erreur', false); }
}

async function openBudgetPerms(budgetId, budgetLabel) {
    _currentBudgetPermId = budgetId;
    document.getElementById('budget-perms-titre').textContent = `Accès — ${budgetLabel}`;
    openModal('modal-budget-perms');
    await _refreshBudgetPerms();
    // Peupler le select utilisateurs
    const users = await _loadUsersActifs();
    const sel = document.getElementById('perm-user-select');
    sel.innerHTML = '<option value="">-- Sélectionner un utilisateur --</option>';
    users.forEach(u => {
        const opt = document.createElement('option');
        opt.value = u.id;
        opt.textContent = `${u.nom} ${u.prenom || ''}${u.service_nom ? ' — ' + u.service_nom : ''}`;
        sel.appendChild(opt);
    });
}

async function _refreshBudgetPerms() {
    const tbody = document.getElementById('budget-perms-tbody');
    try {
        const data = await apiFetch(`/budget/${_currentBudgetPermId}/permissions`);
        const list = data.list || [];
        if (!list.length) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:#999;padding:12px;font-style:italic;">Aucun accès accordé.</td></tr>';
            return;
        }
        tbody.innerHTML = list.map(p => `<tr>
            <td style="padding:5px 8px;">${p.nom || ''} ${p.prenom || ''}<br><small style="color:#888;">${p.login}</small></td>
            <td style="padding:5px 8px;color:#555;font-size:.87em;">${p.service_nom || '-'}</td>
            <td style="padding:5px 8px;text-align:center;">
                <span style="background:${p.role==='gestionnaire'?'#2563a8':'#6c757d'};color:#fff;padding:2px 8px;border-radius:10px;font-size:.82em;">${p.role}</span>
            </td>
            <td style="padding:5px 8px;text-align:center;">
                <button class="btn btn-danger btn-sm" onclick="removeBudgetPerm(${p.user_id})">Révoquer</button>
            </td>
        </tr>`).join('');
    } catch(e) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:#e74c3c;padding:12px;">Erreur de chargement.</td></tr>';
    }
}

async function addBudgetPerm() {
    const userId = document.getElementById('perm-user-select').value;
    const role   = document.getElementById('perm-role-select').value;
    if (!userId) { showMsg('Sélectionner un utilisateur', false); return; }
    try {
        await apiFetch(`/budget/${_currentBudgetPermId}/permissions`, {
            method: 'POST', body: JSON.stringify({ user_id: parseInt(userId), role })
        });
        showMsg('Accès accordé');
        await _refreshBudgetPerms();
        document.getElementById('perm-user-select').value = '';
    } catch(e) { showMsg(e.message, false); }
}

async function removeBudgetPerm(userId) {
    if (!confirm('Révoquer cet accès ?')) return;
    try {
        await apiFetch(`/budget/${_currentBudgetPermId}/permissions/${userId}`, { method: 'DELETE' });
        showMsg('Accès révoqué');
        await _refreshBudgetPerms();
    } catch(e) { showMsg(e.message, false); }
}

async function addBudget() {
    const body = {
        entite_id:            document.getElementById('budget-entite').value || null,
        exercice:             document.getElementById('budget-exercice').value,
        nature:               document.getElementById('budget-nature').value,
        montant_previsionnel: document.getElementById('budget-montant-prev').value || 0,
        statut:               document.getElementById('budget-statut').value,
    };
    if (!body.exercice) { showMsg("L'exercice est obligatoire", false); return; }
    try {
        const res = await apiFetch('/budget', { method: 'POST', body: JSON.stringify(body) });
        if (res.success) { showMsg('Budget ajouté'); loadBudget(); }
        else showMsg(res.error || 'Erreur', false);
    } catch (e) { showMsg(e.message, false); }
}

function openVoterBudget(id, montantActuel) {
    _currentBudgetId = id;
    document.getElementById('voter-montant').value = montantActuel || '';
    openModal('modal-voter-budget');
}

async function confirmVoterBudget() {
    const montant = parseFloat(document.getElementById('voter-montant').value);
    if (!montant || montant <= 0) { showMsg('Montant invalide', false); return; }
    try {
        const res = await apiFetch(`/budget/${_currentBudgetId}/voter`, {
            method: 'POST', body: JSON.stringify({ montant_vote: montant })
        });
        if (res.success) { showMsg('Budget voté'); closeModal('modal-voter-budget'); loadBudget(); }
        else showMsg(res.error || 'Erreur', false);
    } catch (e) { showMsg(e.message, false); }
}

async function deleteBudget(id) {
    if (!confirm('Supprimer ce budget ?')) return;
    try {
        const res = await apiFetch(`/budget/${id}`, { method: 'DELETE' });
        if (res.success) { showMsg('Budget supprimé'); loadBudget(); }
        else showMsg(res.error || 'Erreur', false);
    } catch (e) { showMsg(e.message, false); }
}

// ─── BONS DE COMMANDE ──────────────────────────────────────

let _bcCache = [];

function _renderBcRows() {
    const userRole = _currentUserRole();
    const tbody = document.getElementById('bc-tbody');
    if (!tbody) return;
    const sorted = _sortedData(_bcCache, 'bc');
    const page   = _paginate(sorted, 'bc');
    tbody.innerHTML = page.map(b => `
        <tr>
            <td>${b.id}</td>
            <td><strong>${b.numero_bc || '-'}</strong></td>
            <td>${b.objet || '-'}</td>
            <td>${b.fournisseur_nom || '-'}</td>
            <td>${b.entite_code || '-'}</td>
            <td>${fmt(b.montant_ht)}</td>
            <td>${fmt(b.montant_ttc)}</td>
            <td>${badge(b.statut)}</td>
            <td style="font-size:.78em;color:#555;">${b.createur_nom ? b.createur_nom.trim() : '<span style="color:#bbb">—</span>'}</td>
            <td style="white-space:nowrap;">
                <button class="btn btn-info btn-sm" onclick="ficheBc(${b.id})">Fiche</button>
                <button class="btn btn-sm" style="background:#6c757d;color:#fff;" onclick="editBC(${b.id})">Modifier</button>
                ${['BROUILLON','EN_ATTENTE'].includes(b.statut)
                    ? `<button class="btn btn-warning btn-sm" onclick="validerBc(${b.id})">Valider</button>` : ''}
                ${b.statut === 'EN_ATTENTE' && ['admin','gestionnaire'].includes(userRole)
                    ? `<button class="btn btn-danger btn-sm" onclick="openRefuserBc(${b.id})">Refuser</button>` : ''}
                ${b.statut === 'VALIDE'
                    ? `<button class="btn btn-success btn-sm" onclick="openImputer(${b.id})">Imputer</button>` : ''}
                ${!['IMPUTE','SOLDE'].includes(b.statut)
                    ? `<button class="btn btn-danger btn-sm" onclick="deleteBC(${b.id})">Suppr.</button>` : ''}
            </td>
        </tr>`).join('');
    _updateSortHeaders('bc');
    _renderPagination('bc', sorted.length);
}

async function loadBC() {
    const params = new URLSearchParams();
    const statut  = document.getElementById('bc-filter-statut')?.value;
    const entite  = document.getElementById('bc-filter-entite')?.value;
    const search  = document.getElementById('bc-search')?.value;
    // Sauvegarder les filtres
    _saveFilter('bc-filter-statut'); _saveFilter('bc-filter-entite'); _saveFilter('bc-search');
    if (statut) params.set('statut', statut);
    if (entite) params.set('entite_id', entite);
    if (search) params.set('search', search);

    try {
        const [data, stats] = await Promise.all([
            apiFetch('/bon_commande?' + params),
            apiFetch('/bon_commande/stats')
        ]);

        // KPI bar
        const kpiEl = document.getElementById('bc-kpi-bar');
        const t = stats._total || {};
        const statutKeys = ['BROUILLON','EN_ATTENTE','VALIDE','IMPUTE','SOLDE','ANNULE'];
        kpiEl.innerHTML =
            `<span>Total: <strong class="kpi-num">${t.count || 0}</strong></span>` +
            statutKeys.map(s => {
                const v = stats[s] || {};
                return v.count ? `<span>${s}: <strong class="kpi-num">${v.count}</strong></span>` : '';
            }).join('') +
            `<span>Montant total: <strong class="kpi-num">${fmt(t.total || 0)} €</strong></span>`;

        _bcCache = data.list || [];
        _resetPage('bc');
        _renderBcRows();
    } catch (e) { showMsg('Erreur chargement BC', false); }
}

async function importBCfromPDF(input) {
    const file = input.files[0];
    if (!file) return;
    const info = document.getElementById('bc-pdf-info');
    info.style.display = '';
    info.textContent = '⏳ Analyse du PDF en cours…';
    try {
        const formData = new FormData();
        formData.append('file', file);
        const token = getToken();
        const resp = await fetch('/api/bon_commande/parse_pdf', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + token },
            body: formData
        });
        const res = await resp.json();
        if (!resp.ok || !res.success) {
            info.style.background = '#fef2f2'; info.style.borderColor = '#fecaca'; info.style.color = '#dc2626';
            info.textContent = '❌ ' + (res.error || 'Erreur analyse PDF');
            input.value = '';
            return;
        }
        const d = res.data;
        const set = (id, val) => { const el = document.getElementById(id); if (el && val !== undefined && val !== null) el.value = val; };
        set('bc-numero',     d.numero_bc);
        set('bc-objet',      d.objet);
        set('bc-montant-ht', d.montant_ht);
        if (d.fournisseur_id) set('bc-fournisseur', d.fournisseur_id);
        if (d.ligne_budgetaire_id) set('bc-ligne', d.ligne_budgetaire_id);

        const extraits = [];
        if (d.numero_bc)         extraits.push(`N° BC : ${d.numero_bc}`);
        if (d.montant_ht)        extraits.push(`HT : ${d.montant_ht} €`);
        if (d.montant_ttc)       extraits.push(`TTC : ${d.montant_ttc} €`);
        if (d.tva)               extraits.push(`TVA : ${d.tva}%`);
        if (d.fournisseur_nom)   extraits.push(`Fournisseur : ${d.fournisseur_nom}`);
        else if (d.fournisseur_nom_brut) extraits.push(`Fournisseur non trouvé (texte: "${d.fournisseur_nom_brut}")`);
        if (d.ligne_libelle)     extraits.push(`Ligne suggérée : ${d.ligne_libelle}`);

        info.style.background = '#eff6ff'; info.style.borderColor = '#bfdbfe'; info.style.color = '#1e40af';
        info.innerHTML = '✅ PDF analysé — Vérifiez et complétez les champs :<br><small>' + extraits.join(' &nbsp;|&nbsp; ') + '</small>';
    } catch (e) {
        info.style.background = '#fef2f2'; info.style.borderColor = '#fecaca'; info.style.color = '#dc2626';
        info.textContent = '❌ Erreur : ' + e.message;
    }
    input.value = '';
}

async function addBC() {
    const montant_ht = parseFloat(document.getElementById('bc-montant-ht').value) || 0;
    const body = {
        numero_bc:           document.getElementById('bc-numero').value,
        objet:               document.getElementById('bc-objet').value,
        fournisseur_id:      document.getElementById('bc-fournisseur').value || null,
        entite_id:           document.getElementById('bc-entite').value || null,
        ligne_budgetaire_id: document.getElementById('bc-ligne').value || null,
        montant_ht,
        montant_ttc:         Math.round(montant_ht * 1.2 * 100) / 100,
        statut:              document.getElementById('bc-statut').value,
    };
    if (!body.numero_bc) { showMsg('Le N° BC est obligatoire', false); return; }
    if (!body.objet)     { showMsg("L'objet est obligatoire", false); return; }
    try {
        const res = await apiFetch('/bon_commande', { method: 'POST', body: JSON.stringify(body) });
        if (res.success) { showMsg('BC ajouté'); loadBC(); }
        else showMsg(res.error || 'Erreur', false);
    } catch (e) { showMsg(e.message, false); }
}

async function validerBc(id) {
    try {
        const res = await apiFetch(`/bon_commande/${id}/valider`, { method: 'POST', body: '{}' });
        if (res.success) { showMsg(`BC → ${res.statut}`); loadBC(); }
        else showMsg(res.error || 'Erreur', false);
    } catch (e) { showMsg(e.message, false); }
}

async function ficheBc(id) {
    try {
        const bc = await apiFetch(`/bon_commande/${id}`);
        document.getElementById('modal-bc-titre').textContent = `Fiche BC — ${bc.numero_bc || '#' + id}`;
        document.getElementById('modal-bc-content').innerHTML = `
            <div class="modal-grid">
                <div class="modal-section"><label>N° BC</label><div class="val">${bc.numero_bc || '-'}</div></div>
                <div class="modal-section"><label>Statut</label><div>${badge(bc.statut)}</div></div>
                <div class="modal-section"><label>Objet</label><div class="val">${bc.objet || '-'}</div></div>
                <div class="modal-section"><label>Entité</label><div class="val">${bc.entite_code || '-'} ${bc.entite_nom ? '– ' + bc.entite_nom : ''}</div></div>
                <div class="modal-section"><label>Fournisseur</label><div class="val">${bc.fournisseur_nom || '-'}</div></div>
                <div class="modal-section"><label>Email fournisseur</label><div class="val">${bc.fournisseur_email || '-'}</div></div>
                <div class="modal-section"><label>Montant HT</label><div class="val">${fmt(bc.montant_ht)} €</div></div>
                <div class="modal-section"><label>Montant TTC</label><div class="val">${fmt(bc.montant_ttc)} €</div></div>
                <div class="modal-section"><label>Contrat lié</label><div class="val">${bc.numero_contrat || '-'}</div></div>
                <div class="modal-section"><label>Ligne budgétaire</label><div class="val">${bc.ligne_libelle || '-'}</div></div>
                ${bc.ligne_vote != null ? `
                <div class="modal-section"><label>Ligne — Voté</label><div class="val">${fmt(bc.ligne_vote)} €</div></div>
                <div class="modal-section"><label>Ligne — Engagé</label><div class="val">${fmt(bc.ligne_engage)} €</div></div>
                <div class="modal-section"><label>Ligne — Solde</label><div class="val">${fmt(bc.ligne_solde)} €</div></div>` : ''}
                <div class="modal-section"><label>Date création</label><div class="val">${fmtDate(bc.date_creation)}</div></div>
                <div class="modal-section"><label>Date validation</label><div class="val">${fmtDate(bc.date_validation)}</div></div>
                <div class="modal-section"><label>Date imputation</label><div class="val">${fmtDate(bc.date_imputation)}</div></div>
            </div>`;
        openModal('modal-bc-fiche');
    } catch (e) { showMsg('Erreur chargement fiche BC', false); }
}

function openImputer(bcId) {
    _currentBcId = bcId;
    document.getElementById('imputer-ligne').value = '';
    document.getElementById('imputer-info').textContent = '';
    openModal('modal-imputer-bc');
}

function _fillLignesSelectByEntite(selectId, entiteId, currentLigneId) {
    const sel = document.getElementById(selectId);
    if (!sel) return;
    const filtered = entiteId
        ? _refs.lignes.filter(l => String(l.entite_id) === String(entiteId))
        : _refs.lignes;
    const lLabel = l => {
        const solde = fmt(l.montant_solde || 0);
        return `${l.libelle || 'Ligne #' + l.id} — Solde: ${solde} €`;
    };
    sel.innerHTML = '<option value="">-- Ligne budgétaire --</option>';
    filtered.forEach(l => {
        const opt = document.createElement('option');
        opt.value = l.id;
        opt.textContent = lLabel(l);
        if (currentLigneId && String(l.id) === String(currentLigneId)) opt.selected = true;
        sel.appendChild(opt);
    });
}

document.addEventListener('change', e => {
    if (e.target.id === 'imputer-ligne') {
        const ligneId = e.target.value;
        const ligne = _refs.lignes.find(l => String(l.id) === String(ligneId));
        const info = document.getElementById('imputer-info');
        if (ligne) {
            info.innerHTML = `Voté: <strong>${fmt(ligne.montant_vote)} €</strong> —
                Engagé: <strong>${fmt(ligne.montant_engage)} €</strong> —
                Solde: <strong>${fmt(ligne.montant_solde)} €</strong>`;
        } else { info.textContent = ''; }
    }
    if (e.target.id === 'edit-bc-entite') {
        _fillLignesSelectByEntite('edit-bc-ligne', e.target.value, null);
        const info = document.getElementById('edit-bc-ligne-info');
        if (info) info.textContent = '';
    }
    if (e.target.id === 'bc-entite') {
        _fillLignesSelectByEntite('bc-ligne', e.target.value, null);
    }
    if (e.target.id === 'edit-bc-ligne') {
        const ligneId = e.target.value;
        const ligne = _refs.lignes.find(l => String(l.id) === String(ligneId));
        const info = document.getElementById('edit-bc-ligne-info');
        if (ligne) {
            info.innerHTML = `Voté: <strong>${fmt(ligne.montant_vote)} €</strong> — ` +
                `Engagé: <strong>${fmt(ligne.montant_engage)} €</strong> — ` +
                `Solde: <strong>${fmt(ligne.montant_solde)} €</strong>`;
        } else { info.textContent = ''; }
    }
});

async function confirmImputer() {
    const ligneId = document.getElementById('imputer-ligne').value;
    if (!ligneId) { showMsg('Sélectionnez une ligne budgétaire', false); return; }
    try {
        const res = await apiFetch(`/bon_commande/${_currentBcId}/imputer`, {
            method: 'POST', body: JSON.stringify({ ligne_id: parseInt(ligneId) })
        });
        if (res.success) { showMsg('BC imputé sur la ligne budgétaire'); closeModal('modal-imputer-bc'); loadBC(); initRefs(); }
        else showMsg(res.error || 'Erreur', false);
    } catch (e) { showMsg(e.message, false); }
}

function openRefuserBc(id) {
    document.getElementById('refus-bc-id').value = id;
    document.getElementById('refus-bc-motif').value = '';
    openModal('modal-refus-bc');
}

async function confirmRefuserBc() {
    const id    = parseInt(document.getElementById('refus-bc-id').value);
    const motif = document.getElementById('refus-bc-motif').value.trim();
    try {
        const res = await apiFetch(`/bon_commande/${id}/refuser`, {
            method: 'POST', body: JSON.stringify({ motif })
        });
        if (res.success) {
            showMsg('BC refusé');
            closeModal('modal-refus-bc');
            loadBC();
        } else showMsg(res.error || 'Erreur', false);
    } catch (e) { showMsg(e.message, false); }
}

async function deleteBC(id) {
    if (!confirm('Supprimer ce bon de commande ?')) return;
    try {
        const res = await apiFetch(`/bon_commande/${id}`, { method: 'DELETE' });
        if (res.success) { showMsg('BC supprimé'); loadBC(); }
        else showMsg(res.error || 'Erreur', false);
    } catch (e) { showMsg(e.message, false); }
}

function updateTtcPreview() {
    const ht  = parseFloat(document.getElementById('edit-bc-montant-ht').value) || 0;
    const tva = parseFloat(document.getElementById('edit-bc-tva').value) || 0;
    const ttc = Math.round(ht * (1 + tva / 100) * 100) / 100;
    document.getElementById('edit-bc-ttc-preview').textContent = ttc.toLocaleString('fr-FR', { minimumFractionDigits: 2 }) + ' €';
    document.getElementById('edit-bc-montant-ttc').value = ttc;
}

async function editBC(id) {
    try {
        const bc = await apiFetch(`/bon_commande/${id}`);
        document.getElementById('edit-bc-id').value      = bc.id;
        document.getElementById('edit-bc-numero').value  = bc.numero_bc || '';
        document.getElementById('edit-bc-statut').value  = bc.statut || 'BROUILLON';
        document.getElementById('edit-bc-objet').value   = bc.objet || '';
        document.getElementById('edit-bc-montant-ht').value = bc.montant_ht || '';
        // Calcul TVA depuis montant_ht et montant_ttc
        const ht  = parseFloat(bc.montant_ht) || 0;
        const ttc = parseFloat(bc.montant_ttc) || 0;
        const tva = ht > 0 ? Math.round((ttc / ht - 1) * 1000) / 10 : 20;
        document.getElementById('edit-bc-tva').value = tva;
        document.getElementById('edit-bc-montant-ttc').value = ttc;
        document.getElementById('edit-bc-ttc-preview').textContent =
            ttc.toLocaleString('fr-FR', { minimumFractionDigits: 2 }) + ' €';
        // Selects
        const setVal = (id, val) => { const el = document.getElementById(id); if (el) el.value = val || ''; };
        setVal('edit-bc-fournisseur', bc.fournisseur_id);
        setVal('edit-bc-entite',      bc.entite_id);
        // Filtrer les lignes selon l'entité sélectionnée
        _fillLignesSelectByEntite('edit-bc-ligne', bc.entite_id, bc.ligne_budgetaire_id);
        setVal('edit-bc-projet',      bc.projet_id);
        setVal('edit-bc-contrat',     bc.contrat_id);
        // Info ligne
        const ligneInfo = document.getElementById('edit-bc-ligne-info');
        if (bc.ligne_budgetaire_id && bc.ligne_libelle) {
            ligneInfo.textContent = `Ligne : ${bc.ligne_libelle}`;
        } else { ligneInfo.textContent = ''; }
        document.getElementById('edit-bc-titre').textContent = `Modifier le BC — ${bc.numero_bc || '#' + id}`;
        openModal('modal-edit-bc');
    } catch (e) { showMsg('Erreur chargement BC', false); }
}

async function saveBC() {
    const id = parseInt(document.getElementById('edit-bc-id').value);
    const ht  = parseFloat(document.getElementById('edit-bc-montant-ht').value) || 0;
    const tva = parseFloat(document.getElementById('edit-bc-tva').value) || 20;
    const ttc = Math.round(ht * (1 + tva / 100) * 100) / 100;
    const body = {
        numero_bc:          document.getElementById('edit-bc-numero').value,
        objet:              document.getElementById('edit-bc-objet').value,
        statut:             document.getElementById('edit-bc-statut').value,
        fournisseur_id:     document.getElementById('edit-bc-fournisseur').value || null,
        entite_id:          document.getElementById('edit-bc-entite').value || null,
        ligne_budgetaire_id: document.getElementById('edit-bc-ligne').value || null,
        projet_id:          document.getElementById('edit-bc-projet').value || null,
        contrat_id:         document.getElementById('edit-bc-contrat').value || null,
        montant_ht:         ht,
        montant_ttc:        ttc,
    };
    if (!body.numero_bc) { showMsg('Le N° BC est obligatoire', false); return; }
    if (!body.objet)     { showMsg("L'objet est obligatoire", false); return; }
    try {
        const res = await apiFetch(`/bon_commande/${id}`, { method: 'PUT', body: JSON.stringify(body) });
        if (res.success) {
            showMsg('BC mis à jour');
            closeModal('modal-edit-bc');
            loadBC();
            initRefs();
        } else showMsg(res.error || 'Erreur', false);
    } catch (e) { showMsg(e.message, false); }
}

// ─── CONTRATS ──────────────────────────────────────────────

function _renderContratsRows() {
    const filterStatut = document.getElementById('contrat-filter-statut')?.value || '';
    const search = (document.getElementById('contrat-search')?.value || '').toLowerCase();
    let list = _cache.contrats || [];
    if (filterStatut) list = list.filter(c => c.statut === filterStatut);
    if (search) list = list.filter(c =>
        (c.numero_contrat || '').toLowerCase().includes(search) ||
        (c.objet || '').toLowerCase().includes(search) ||
        (c.fournisseur_nom || '').toLowerCase().includes(search)
    );
    const sorted = _sortedData(list, 'contrats');
    const page   = _paginate(sorted, 'contrats');
    const tbody = document.getElementById('contrats-tbody');
    if (!tbody) return;
    tbody.innerHTML = page.map(c => {
        const niveau = c.niveau_alerte || 'OK';
        const rowCls = niveau === 'EXPIRE' ? 'alerte-expire'
            : niveau === 'CRITIQUE' ? 'alerte-critique'
            : niveau === 'ATTENTION' ? 'alerte-attention'
            : niveau === 'INFO' ? 'alerte-info' : '';
        const jours = c.jours_restants != null
            ? (c.jours_restants < 0 ? `<span style="color:#c0392b">${c.jours_restants} j.</span>` : `${c.jours_restants} j.`)
            : '-';
        return `<tr class="${rowCls}">
            <td>${c.id}</td>
            <td><strong>${c.numero_contrat || '-'}</strong></td>
            <td>${c.objet || '-'}</td>
            <td>${c.fournisseur_nom || '-'}</td>
            <td>${fmt(c.montant_total_ht)}</td>
            <td>${fmtDate(c.date_debut)}</td>
            <td>${fmtDate(c.date_fin)}</td>
            <td>${jours}</td>
            <td>${badge(c.statut)}</td>
            <td style="font-size:.78em;">${{MARCHE_PUBLIC:'Marché public',MAPA:'MAPA',ACCORD_CADRE:'Accord-cadre',CONVENTION:'Convention',DSP:'DSP'}[c.type_marche] || c.type_marche || '-'}</td>
            <td>${alerteBadge(niveau)}</td>
            <td style="font-size:.78em;color:#555;">${c.createur_nom ? c.createur_nom.trim() : '<span style="color:#bbb">—</span>'}</td>
            <td style="white-space:nowrap;">
                <button class="btn btn-info btn-sm" onclick="ficheContrat(${c.id})">Fiche</button>
                <button class="btn btn-warning btn-sm" onclick="editContrat(${c.id})">Éditer</button>
                ${['ACTIF','RECONDUIT'].includes(c.statut)
                    ? `<button class="btn btn-sm" style="background:#6c757d;color:#fff;" onclick="openReconduire(${c.id})">Reconduire</button>` : ''}
                <button class="btn btn-danger btn-sm" onclick="deleteContrat(${c.id})">Suppr.</button>
            </td>
        </tr>`;
    }).join('');
    _updateSortHeaders('contrats');
    _renderPagination('contrats', sorted.length);
}

async function loadContrats() {
    try {
        _saveFilter('contrat-filter-statut'); _saveFilter('contrat-search');
        const data = await apiFetch('/contrat');
        _cache.contrats = data.list || [];
        _resetPage('contrats');
        _renderContratsRows();
    } catch (e) { showMsg('Erreur chargement contrats', false); }
}

async function addContrat() {
    const montant_ht = parseFloat(document.getElementById('contrat-montant').value) || 0;
    const body = {
        numero_contrat:  document.getElementById('contrat-numero').value,
        objet:           document.getElementById('contrat-objet').value,
        fournisseur_id:  document.getElementById('contrat-fournisseur').value || null,
        montant_total_ht: montant_ht,
        date_debut:      document.getElementById('contrat-date-debut').value || null,
        date_fin:        document.getElementById('contrat-date-fin').value || null,
        statut:          document.getElementById('contrat-statut').value,
    };
    if (!body.numero_contrat) { showMsg('Le N° contrat est obligatoire', false); return; }
    if (!body.objet)          { showMsg("L'objet est obligatoire", false); return; }
    try {
        const res = await apiFetch('/contrat', { method: 'POST', body: JSON.stringify(body) });
        if (res.success) { showMsg('Contrat ajouté'); loadContrats(); }
        else showMsg(res.error || 'Erreur', false);
    } catch (e) { showMsg(e.message, false); }
}

function openReconduire(id) {
    _currentContratId = id;
    document.getElementById('reconduire-date').value = '';
    openModal('modal-reconduire');
}

async function confirmReconduire() {
    const date = document.getElementById('reconduire-date').value;
    if (!date) { showMsg('Date requise', false); return; }
    try {
        const res = await apiFetch(`/contrat/${_currentContratId}/reconduire`, {
            method: 'POST', body: JSON.stringify({ nouvelle_date_fin: date })
        });
        if (res.success) { showMsg('Contrat reconduit'); closeModal('modal-reconduire'); loadContrats(); }
        else showMsg(res.error || 'Erreur', false);
    } catch (e) { showMsg(e.message, false); }
}

async function deleteContrat(id) {
    if (!confirm('Supprimer ce contrat ?')) return;
    try {
        const res = await apiFetch(`/contrat/${id}`, { method: 'DELETE' });
        if (res.success) { showMsg('Contrat supprimé'); loadContrats(); }
        else showMsg(res.error || 'Erreur', false);
    } catch (e) { showMsg(e.message, false); }
}

async function ficheContrat(id) {
    try {
        const c = await apiFetch(`/contrat/${id}`);
        document.getElementById('fiche-contrat-titre').textContent =
            `${c.numero_contrat || '#' + id} — ${c.objet || ''}`;

        const alerteColor = { EXPIRE:'#c0392b', CRITIQUE:'#e67e22', ATTENTION:'#f39c12', INFO:'#2980b9', OK:'#27ae60' };
        const aColor = alerteColor[c.niveau_alerte] || '#555';
        const joursStr = c.jours_restants != null
            ? (c.jours_restants < 0
                ? `<span style="color:#c0392b;font-weight:bold;">Expiré de ${Math.abs(c.jours_restants)} j.</span>`
                : `<span style="color:${aColor};font-weight:bold;">${c.jours_restants} j. restants</span>`)
            : '-';

        const bcsHtml = (c.bons_commande || []).length === 0
            ? '<p style="color:#aaa;font-style:italic;margin:8px 0;">Aucun BC lié à ce contrat.</p>'
            : `<table style="width:100%;border-collapse:collapse;font-size:.82em;margin-top:6px;">
                <thead><tr style="background:#1a3c5e;color:#fff;">
                    <th style="padding:6px;">N° BC</th><th>Objet</th><th>Montant HT</th>
                    <th>Montant TTC</th><th>Ligne budgétaire</th><th>Statut</th><th>Date</th>
                </tr></thead><tbody>
                ${(c.bons_commande || []).map(b => `<tr style="border-bottom:1px solid #eee;">
                    <td style="padding:5px;">${b.numero_bc || '-'}</td>
                    <td>${b.objet || '-'}</td>
                    <td style="text-align:right;">${fmt(b.montant_ht)} €</td>
                    <td style="text-align:right;">${fmt(b.montant_ttc)} €</td>
                    <td style="font-size:.85em;">${b.ligne_libelle || '-'}</td>
                    <td>${badge(b.statut)}</td>
                    <td>${fmtDate(b.date_creation)}</td>
                </tr>`).join('')}
                </tbody></table>
                <div style="text-align:right;margin-top:6px;font-weight:bold;font-size:.88em;">
                    Total TTC : ${fmt(c.montant_bc_total)} €
                </div>`;

        document.getElementById('fiche-contrat-content').innerHTML = `
            <div class="proj-tabs">
                <span class="proj-tab active" id="ctab-btn-general" onclick="switchContratTab('general')">Général</span>
                <span class="proj-tab" id="ctab-btn-fournisseur" onclick="switchContratTab('fournisseur')">Fournisseur</span>
                <span class="proj-tab" id="ctab-btn-bc" onclick="switchContratTab('bc')">BCs liés (${(c.bons_commande||[]).length})</span>
            </div>

            <!-- Général -->
            <div class="proj-tab-content active" id="ctab-general">
                <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:12px;">
                    <div style="flex:1;min-width:200px;background:#f0f4ff;border-radius:8px;padding:12px;">
                        <div style="font-size:.75em;font-weight:bold;color:#2563a8;margin-bottom:8px;text-transform:uppercase;">Identification</div>
                        <div class="modal-grid">
                            <div class="modal-section"><label>N° Contrat</label><div class="val">${c.numero_contrat || '-'}</div></div>
                            <div class="modal-section"><label>Statut</label><div>${badge(c.statut)}</div></div>
                            <div class="modal-section" style="grid-column:span 2;"><label>Objet</label><div class="val">${c.objet || '-'}</div></div>
                            <div class="modal-section"><label>Type</label><div class="val">${c.type_contrat || '-'}</div></div>
                            <div class="modal-section"><label>Reconductions</label><div class="val">${c.nombre_reconductions || 0}</div></div>
                        </div>
                    </div>
                    <div style="flex:1;min-width:200px;background:#f0fff4;border-radius:8px;padding:12px;">
                        <div style="font-size:.75em;font-weight:bold;color:#27ae60;margin-bottom:8px;text-transform:uppercase;">Calendrier</div>
                        <div class="modal-grid">
                            <div class="modal-section"><label>Date début</label><div class="val">${fmtDate(c.date_debut)}</div></div>
                            <div class="modal-section"><label>Date fin</label><div class="val">${fmtDate(c.date_fin)}</div></div>
                            <div class="modal-section" style="grid-column:span 2;"><label>Délai</label><div>${joursStr}</div></div>
                            <div class="modal-section" style="grid-column:span 2;"><label>Alerte</label><div>${alerteBadge(c.niveau_alerte)}</div></div>
                        </div>
                    </div>
                    <div style="flex:1;min-width:200px;background:#fff8e1;border-radius:8px;padding:12px;">
                        <div style="font-size:.75em;font-weight:bold;color:#f39c12;margin-bottom:8px;text-transform:uppercase;">Montants</div>
                        <div class="modal-grid">
                            <div class="modal-section"><label>Montant initial HT</label><div class="val">${fmt(c.montant_initial_ht)} €</div></div>
                            <div class="modal-section"><label>Montant total HT</label><div class="val">${fmt(c.montant_total_ht)} €</div></div>
                            <div class="modal-section"><label>Montant TTC</label><div class="val">${fmt(c.montant_ttc)} €</div></div>
                            <div class="modal-section"><label>Engagé (BC)</label><div class="val">${fmt(c.montant_bc_total)} €</div></div>
                            ${c.montant_total_ht && c.montant_bc_total != null ? `
                            <div class="modal-section" style="grid-column:span 2;">
                                <label>Taux engagement</label>
                                <div>${progressBar(c.montant_bc_total, c.montant_ttc || c.montant_total_ht)}</div>
                            </div>` : ''}
                        </div>
                    </div>
                </div>
            </div>

            <!-- Fournisseur -->
            <div class="proj-tab-content" id="ctab-fournisseur">
                <div style="background:#f8f9fb;border-radius:8px;padding:16px;">
                    <div class="modal-grid">
                        <div class="modal-section"><label>Nom</label><div class="val">${c.fournisseur_nom || '-'}</div></div>
                        <div class="modal-section"><label>Contact</label><div class="val">${c.fournisseur_contact || '-'}</div></div>
                        <div class="modal-section"><label>Email</label><div class="val">${c.fournisseur_email
                            ? `<a href="mailto:${c.fournisseur_email}">${c.fournisseur_email}</a>` : '-'}</div></div>
                        <div class="modal-section"><label>Téléphone</label><div class="val">${c.fournisseur_telephone || '-'}</div></div>
                        <div class="modal-section"><label>Adresse</label><div class="val">${c.fournisseur_adresse || '-'}</div></div>
                        <div class="modal-section"><label>Ville</label><div class="val">${c.fournisseur_ville || '-'}</div></div>
                    </div>
                </div>
            </div>

            <!-- BCs liés -->
            <div class="proj-tab-content" id="ctab-bc">${bcsHtml}</div>

            <div class="modal-footer" style="margin-top:14px;">
                <button class="btn btn-warning" onclick="closeModal('modal-fiche-contrat');editContrat(${c.id})">Éditer</button>
                ${['ACTIF','RECONDUIT'].includes(c.statut)
                    ? `<button class="btn" style="background:#6c757d;color:#fff;" onclick="closeModal('modal-fiche-contrat');openReconduire(${c.id})">Reconduire</button>` : ''}
                <button class="btn btn-danger" onclick="closeModal('modal-fiche-contrat')">Fermer</button>
            </div>`;
        openModal('modal-fiche-contrat');
    } catch (e) { showMsg('Erreur chargement fiche contrat', false); }
}

function switchContratTab(tabId) {
    document.querySelectorAll('#fiche-contrat-content .proj-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('#fiche-contrat-content .proj-tab-content').forEach(c => c.classList.remove('active'));
    document.getElementById('ctab-btn-' + tabId).classList.add('active');
    document.getElementById('ctab-' + tabId).classList.add('active');
}

async function openBudgetDetail(budgetId, label) {
    try {
        document.getElementById('budget-detail-titre').textContent = `Lignes budgétaires — ${label}`;
        document.getElementById('budget-detail-content').innerHTML =
            '<p style="color:#888;padding:20px;">Chargement...</p>';
        openModal('modal-budget-detail');
        const data = await apiFetch(`/budget/${budgetId}/detail`);
        const lignes = data.lignes || [];
        if (!lignes.length) {
            document.getElementById('budget-detail-content').innerHTML =
                '<p style="color:#aaa;font-style:italic;margin:16px 0;">Aucune ligne budgétaire pour ce budget.</p>';
            return;
        }
        document.getElementById('budget-detail-content').innerHTML = lignes.map(l => {
            const bcs = l.bons_commande || [];
            const bcsHtml = bcs.length === 0
                ? '<p style="color:#aaa;font-size:.82em;font-style:italic;margin:4px 0 0;">Aucun BC imputé.</p>'
                : bcs.map(b => `<div style="display:flex;gap:8px;align-items:center;padding:4px 0;border-bottom:1px solid #f0f0f0;font-size:.8em;">
                    <span style="flex:1;font-weight:bold;">${b.numero_bc || '-'}</span>
                    <span style="flex:2;color:#555;">${b.objet || '-'}</span>
                    <span style="min-width:80px;text-align:right;">${fmt(b.montant_ttc)} €</span>
                    <span>${badge(b.statut)}</span>
                    <span style="color:#888;min-width:80px;">${b.fournisseur_nom || '-'}</span>
                    <span style="color:#2980b9;min-width:120px;" title="${b.contrat_objet || ''}">${b.contrat_numero ? '&#128196; ' + b.contrat_numero : '<span style="color:#ccc">Sans contrat</span>'}</span>
                </div>`).join('');
            const alertStyle = l.alerte ? 'border-left:3px solid #e74c3c;' : 'border-left:3px solid #27ae60;';
            return `<div style="background:#fff;border-radius:8px;padding:14px;margin-bottom:12px;
                                box-shadow:0 1px 4px rgba(0,0,0,.06);${alertStyle}">
                <div style="display:flex;gap:16px;flex-wrap:wrap;align-items:baseline;margin-bottom:6px;">
                    <div style="font-weight:bold;font-size:.95em;flex:2;min-width:160px;">${l.libelle || 'Ligne #' + l.id}</div>
                    <div style="font-size:.82em;color:#666;">
                        Voté : <strong>${fmt(l.montant_vote)} €</strong> &nbsp;|&nbsp;
                        Engagé : <strong style="color:${l.alerte?'#e74c3c':'inherit'}">${fmt(l.montant_engage)} €</strong> &nbsp;|&nbsp;
                        Solde : <strong style="color:#27ae60;">${fmt(l.montant_solde)} €</strong>
                    </div>
                    <div style="min-width:150px;">${progressBar(l.montant_engage, l.montant_vote)}</div>
                </div>
                <div style="font-size:.8em;font-weight:bold;color:#555;margin-bottom:4px;">
                    BC imputés (${bcs.length}) — Total TTC : ${fmt(bcs.reduce((s,b) => s + (parseFloat(b.montant_ttc)||0), 0))} €
                </div>
                ${bcsHtml}
            </div>`;
        }).join('');
    } catch (e) { showMsg('Erreur chargement détail budget', false); }
}

function editContrat(id) {
    const data = _cache.contrats.find(c => c.id === id);
    if (!data) { showMsg('Données non chargées, rechargez', false); return; }
    document.getElementById('edit-contrat-id').value       = data.id;
    document.getElementById('edit-contrat-numero').value   = data.numero_contrat || '';
    document.getElementById('edit-contrat-objet').value    = data.objet || '';
    document.getElementById('edit-contrat-fournisseur').value = data.fournisseur_id || '';
    document.getElementById('edit-contrat-montant').value  = data.montant_total_ht || '';
    document.getElementById('edit-contrat-debut').value    = _toISODate(data.date_debut);
    document.getElementById('edit-contrat-fin').value      = _toISODate(data.date_fin);
    document.getElementById('edit-contrat-type').value     = data.type_marche || '';
    document.getElementById('edit-contrat-statut').value   = data.statut || 'ACTIF';
    openModal('modal-edit-contrat');
}

async function saveContrat() {
    const id = document.getElementById('edit-contrat-id').value;
    const body = {
        numero_contrat:   document.getElementById('edit-contrat-numero').value,
        objet:            document.getElementById('edit-contrat-objet').value,
        fournisseur_id:   document.getElementById('edit-contrat-fournisseur').value || null,
        montant_total_ht: document.getElementById('edit-contrat-montant').value || null,
        date_debut:       document.getElementById('edit-contrat-debut').value || null,
        date_fin:         document.getElementById('edit-contrat-fin').value || null,
        type_marche:      document.getElementById('edit-contrat-type').value || null,
        statut:           document.getElementById('edit-contrat-statut').value,
    };
    if (!body.numero_contrat) { showMsg('Le N° contrat est obligatoire', false); return; }
    if (!body.objet)          { showMsg("L'objet est obligatoire", false); return; }
    try {
        const res = await apiFetch(`/contrat/${id}`, { method: 'PUT', body: JSON.stringify(body) });
        if (res.success) { showMsg('Contrat mis à jour'); closeModal('modal-edit-contrat'); loadContrats(); }
        else showMsg(res.error || 'Erreur', false);
    } catch (e) { showMsg(e.message, false); }
}

// ─── PROJETS ───────────────────────────────────────────────

function _ragDot(rag) {
    const map = { ROUGE: ['🔴','#e74c3c'], AMBER: ['🟡','#f39c12'], VERT: ['🟢','#27ae60'] };
    const [icon] = map[rag] || map['VERT'];
    return `<span title="${rag || 'VERT'}" style="font-size:1.1em;cursor:default;">${icon}</span>`;
}

function _renderProjets(list) {
    const tbody = document.getElementById('projets-tbody');
    if (!tbody) return;
    tbody.innerHTML = list.map(p => `
        <tr>
            <td style="text-align:center;">${_ragDot(p.statut_rag)}</td>
            <td>${_h(p.code) || '-'}</td>
            <td><strong>${_h(p.nom) || '-'}</strong></td>
            <td style="font-size:.8em;">${_h(p.type_projet) || '-'}</td>
            <td style="font-size:.8em;">${_h(p.phase) || '-'}</td>
            <td>${badge(p.statut)}</td>
            <td>${badge(p.priorite)}</td>
            <td style="font-size:.8em;">${_h(p.service_code || p.service_nom) || '-'}</td>
            <td>${fmt(p.budget_estime)}</td>
            <td>${p.avancement != null ? p.avancement + ' %' : '-'}</td>
            <td>${fmtDate(p.date_debut)}</td>
            <td>${fmtDate(p.date_fin_prevue)}</td>
            <td style="white-space:nowrap;">
                <button class="btn btn-sm" style="background:#6f42c1;color:#fff;" onclick="openProjetDashboard(${p.id})">📊</button>
                <button class="btn btn-info btn-sm" onclick="ficheProjet(${p.id})">Fiche</button>
                <button class="btn btn-warning btn-sm" onclick="editProjet(${p.id})">Éditer</button>
                <button class="btn btn-danger btn-sm" onclick="deleteProjet(${p.id})">Suppr.</button>
            </td>
        </tr>`).join('');
}

// ── Tableau de bord projet ─────────────────────────────────────────────────
let _dashProjetId = null;

async function openProjetDashboard(projetId) {
    _dashProjetId = projetId;
    const p = await apiFetch(`/projet/${projetId}`);
    if (!p || p.error) { showMsg('Projet introuvable', false); return; }
    _cache._dashProjet = p;

    document.getElementById('dash-projet-titre').textContent =
        `${p.code || '#' + projetId} — ${p.nom || ''}`;

    _renderDashSynthese(p);
    switchDashTab('synthese');
    _highlightRagBtn(p.statut_rag || 'VERT');
    await loadJalons(projetId);
    await loadJournal(projetId);
    openModal('modal-projet-dashboard');
}

function switchDashTab(tab) {
    ['synthese','jalons','journal'].forEach(t => {
        const el = document.getElementById('dtab-' + t);
        const btn = document.getElementById('dtab-btn-' + t);
        if (el) el.style.display = t === tab ? '' : 'none';
        if (btn) {
            btn.style.color = t === tab ? '#2563a8' : '#555';
            btn.style.borderBottom = t === tab ? '2px solid #2563a8' : '2px solid transparent';
            btn.style.fontWeight   = t === tab ? '700' : '400';
        }
    });
}

function _renderDashSynthese(p) {
    const taches    = p.taches || [];
    const total     = taches.length;
    const terminees = taches.filter(t => t.statut === 'Terminé').length;
    const now       = new Date(); now.setHours(0,0,0,0);
    const enRetard  = taches.filter(t => {
        if (t.statut === 'Terminé') return false;
        return t.date_echeance && new Date(t.date_echeance) < now;
    }).length;

    const av = p.avancement || 0;
    const avColor = av >= 80 ? '#27ae60' : av >= 40 ? '#f39c12' : '#e74c3c';

    const budgetPrev = parseFloat(p.budget_estime || p.budget_initial || 0);
    const budgetCons = parseFloat(p.budget_consomme_calcule || 0);

    const finDate = p.date_fin_prevue ? new Date(p.date_fin_prevue) : null;
    const joursRestants = finDate ? Math.ceil((finDate - now) / 86400000) : null;
    const joursStyle = joursRestants !== null && joursRestants < 0 ? 'color:#e74c3c;font-weight:bold;' : '';

    const _kpi = (val, label, cls='', style='') =>
        `<div class="kpi-card ${cls}" style="min-width:120px;${style}">
            <div class="kpi-value">${val}</div>
            <div class="kpi-label">${label}</div>
        </div>`;

    document.getElementById('dash-kpis').innerHTML =
        _kpi(av + '%', 'Avancement', '', `--kpi-color:${avColor}`) +
        _kpi(terminees + '/' + total, 'Tâches terminées') +
        (enRetard > 0 ? _kpi(enRetard, 'Tâches en retard', 'alert') : '') +
        _kpi(fmt(budgetCons), 'Budget consommé') +
        _kpi(fmt(budgetPrev), 'Budget prévu') +
        (joursRestants !== null ? _kpi(
            joursRestants < 0 ? `${-joursRestants}j de retard` : `${joursRestants}j`,
            'Fin prévue',
            joursRestants < 0 ? 'alert' : ''
        ) : '');

    const avBar = `<div style="background:#e0e0e0;border-radius:4px;height:14px;margin:6px 0 12px;">
        <div style="width:${av}%;background:${avColor};height:14px;border-radius:4px;"></div></div>`;

    const tacheRetardHtml = enRetard > 0
        ? `<div style="background:#fde8e8;border-left:4px solid #e74c3c;padding:8px 12px;border-radius:4px;margin-bottom:10px;font-size:.85em;">
            ⚠ ${enRetard} tâche${enRetard>1?'s':''} en retard (échéance dépassée)
           </div>` : '';

    const chefNom = p.chef_projet_nom || p.chef_projet || '';
    const respNom = p.responsable_nom || p.responsable || '';

    document.getElementById('dash-details').innerHTML = `
        <div style="margin-bottom:10px;">
            <div style="font-size:.78em;color:#666;font-weight:bold;text-transform:uppercase;margin-bottom:3px;">Avancement global</div>
            ${avBar}
        </div>
        ${tacheRetardHtml}
        <div style="display:flex;gap:16px;flex-wrap:wrap;font-size:.85em;">
            <div><label style="color:#666;font-size:.82em;display:block;">Phase</label>${badge(p.phase) || '-'}</div>
            <div><label style="color:#666;font-size:.82em;display:block;">Statut</label>${badge(p.statut) || '-'}</div>
            <div><label style="color:#666;font-size:.82em;display:block;">Priorité</label>${badge(p.priorite) || '-'}</div>
            <div><label style="color:#666;font-size:.82em;display:block;">Chef de projet</label>${chefNom || '-'}</div>
            <div><label style="color:#666;font-size:.82em;display:block;">Responsable</label>${respNom || '-'}</div>
            <div><label style="color:#666;font-size:.82em;display:block;">Début</label>${fmtDate(p.date_debut) || '-'}</div>
            <div><label style="color:#666;font-size:.82em;display:block;">Fin prévue</label><span style="${joursStyle}">${fmtDate(p.date_fin_prevue) || '-'}</span></div>
        </div>`;
}

function _highlightRagBtn(rag) {
    ['VERT','AMBER','ROUGE'].forEach(r => {
        const btn = document.getElementById('rag-btn-' + r);
        if (!btn) return;
        btn.style.opacity = r === rag ? '1' : '0.45';
        btn.style.fontWeight = r === rag ? '700' : '400';
    });
}

async function setRag(rag) {
    if (!_dashProjetId) return;
    const res = await apiFetch(`/projet/${_dashProjetId}/rag`, {
        method: 'PUT', body: JSON.stringify({ statut_rag: rag })
    });
    if (res.success) {
        _highlightRagBtn(rag);
        // Mettre à jour le cache local
        const cached = (_cache.projets || []).find(p => p.id === _dashProjetId);
        if (cached) cached.statut_rag = rag;
        _renderProjets(_cache.projets || []);
        _renderPortfolio(_cache.projets || []);
    }
}

// ── Jalons ────────────────────────────────────────────────────────────────
let _jalons = [];

async function loadJalons(projetId) {
    const data = await apiFetch(`/projet/${projetId}/jalons`);
    _jalons = data.list || [];
    _renderJalons();
}

function _renderJalons() {
    const el = document.getElementById('jalons-list');
    if (!el) return;
    const now = new Date(); now.setHours(0,0,0,0);
    const STATUT_STYLE = {
        'A_VENIR':  ['background:#e3f2fd;color:#1565C0;','À venir'],
        'ATTEINT':  ['background:#d4edda;color:#155724;','Atteint ✓'],
        'EN_RETARD':['background:#fde8e8;color:#721c24;','En retard ⚠'],
        'REPORTE':  ['background:#fff3cd;color:#856404;','Reporté'],
    };
    if (!_jalons.length) {
        el.innerHTML = '<p style="color:#aaa;font-style:italic;font-size:.85em;">Aucun jalon défini.</p>';
        return;
    }
    el.innerHTML = `<table style="width:100%;border-collapse:collapse;font-size:.85em;">
        <thead><tr style="background:#1a3c5e;color:#fff;">
            <th style="padding:6px 8px;">Titre</th>
            <th style="padding:6px 8px;">Échéance</th>
            <th style="padding:6px 8px;">Statut</th>
            <th style="padding:6px 8px;width:60px;"></th>
        </tr></thead>
        <tbody>${_jalons.map(j => {
            const [st, stLbl] = STATUT_STYLE[j.statut] || ['background:#eee;',''];
            const echeance = j.date_echeance ? new Date(j.date_echeance) : null;
            const isLate = echeance && echeance < now && j.statut === 'A_VENIR';
            const dateStr = echeance ? echeance.toLocaleDateString('fr-FR') : '-';
            return `<tr style="border-bottom:1px solid #eee;${isLate?'background:#fff5f5;':''}">
                <td style="padding:6px 8px;">${_h(j.titre)}</td>
                <td style="padding:6px 8px;white-space:nowrap;">${_h(dateStr)}</td>
                <td style="padding:6px 8px;"><span style="border-radius:10px;padding:2px 8px;font-size:.8em;font-weight:bold;${st}">${stLbl}</span></td>
                <td style="padding:6px 8px;text-align:center;">
                    <button class="btn btn-danger btn-sm" onclick="deleteJalon(${j.id})">✕</button>
                </td>
            </tr>`;
        }).join('')}</tbody>
    </table>`;
}

async function addJalon() {
    const titre  = document.getElementById('jalon-titre')?.value.trim();
    const date   = document.getElementById('jalon-date')?.value;
    const statut = document.getElementById('jalon-statut')?.value || 'A_VENIR';
    if (!titre) { showMsg('Le titre du jalon est obligatoire', false); return; }
    const res = await apiFetch(`/projet/${_dashProjetId}/jalons`, {
        method: 'POST',
        body: JSON.stringify({ titre, date_echeance: date || null, statut })
    });
    if (res.success) {
        document.getElementById('jalon-titre').value = '';
        document.getElementById('jalon-date').value  = '';
        await loadJalons(_dashProjetId);
    } else { showMsg('Erreur : ' + (res.error || ''), false); }
}

async function deleteJalon(jalonId) {
    if (!confirm('Supprimer ce jalon ?')) return;
    const res = await apiFetch(`/projet/${_dashProjetId}/jalons/${jalonId}`, { method: 'DELETE' });
    if (res.success) await loadJalons(_dashProjetId);
}

// ── Journal de bord ───────────────────────────────────────────────────────
let _journal = [];

async function loadJournal(projetId) {
    const data = await apiFetch(`/projet/${projetId}/journal`);
    _journal = data.list || [];
    _renderJournal();
}

function _renderJournal() {
    const el = document.getElementById('journal-list');
    if (!el) return;
    const TYPE_STYLE = {
        'DECISION': ['background:#e3f2fd;color:#1565C0;border-left:3px solid #1565C0;','Décision'],
        'EVENEMENT':['background:#f5f5f5;color:#333;border-left:3px solid #999;','Événement'],
        'COPIL':    ['background:#e8f5e9;color:#155724;border-left:3px solid #27ae60;','COPIL'],
        'RISQUE':   ['background:#fde8e8;color:#721c24;border-left:3px solid #e74c3c;','Risque'],
        'AUTRE':    ['background:#fff8e1;color:#795548;border-left:3px solid #f39c12;','Autre'],
    };
    if (!_journal.length) {
        el.innerHTML = '<p style="color:#aaa;font-style:italic;font-size:.85em;">Aucune entrée dans le journal.</p>';
        return;
    }
    el.innerHTML = _journal.map(e => {
        const [st, stLbl] = TYPE_STYLE[e.type_entree] || TYPE_STYLE['AUTRE'];
        const dt = e.date_entree ? new Date(e.date_entree).toLocaleString('fr-FR', {day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'}) : '';
        return `<div style="padding:8px 12px;border-radius:4px;margin-bottom:8px;${st}">
            <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:4px;">
                <span style="font-size:.75em;font-weight:bold;text-transform:uppercase;">${_h(stLbl)}</span>
                <span style="font-size:.72em;opacity:.7;">${_h(dt)}${e.auteur ? ' — ' + _h(e.auteur) : ''}</span>
                <button onclick="deleteJournalEntry(${e.id})" style="background:none;border:none;cursor:pointer;opacity:.5;font-size:.9em;padding:0 2px;">✕</button>
            </div>
            <div style="font-size:.85em;white-space:pre-wrap;">${_h(e.contenu)}</div>
        </div>`;
    }).join('');
}

async function addJournalEntry() {
    const type    = document.getElementById('journal-type')?.value || 'EVENEMENT';
    const contenu = document.getElementById('journal-contenu')?.value.trim();
    if (!contenu) { showMsg('Le contenu est obligatoire', false); return; }
    const res = await apiFetch(`/projet/${_dashProjetId}/journal`, {
        method: 'POST',
        body: JSON.stringify({ type_entree: type, contenu })
    });
    if (res.success) {
        document.getElementById('journal-contenu').value = '';
        await loadJournal(_dashProjetId);
    } else { showMsg('Erreur : ' + (res.error || ''), false); }
}

async function deleteJournalEntry(entryId) {
    if (!confirm('Supprimer cette entrée ?')) return;
    const res = await apiFetch(`/projet/${_dashProjetId}/journal/${entryId}`, { method: 'DELETE' });
    if (res.success) await loadJournal(_dashProjetId);
}

// ── Portfolio (vue multi-projets dans le dashboard global) ─────────────────
function _renderPortfolio(list) {
    const tbody = document.getElementById('portfolio-tbody');
    if (!tbody) return;
    const now = new Date(); now.setHours(0,0,0,0);
    const actifs = list.filter(p => p.statut === 'ACTIF' || p.statut === 'EN_ATTENTE');
    if (!actifs.length) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:#aaa;padding:12px;">Aucun projet actif</td></tr>';
        return;
    }
    tbody.innerHTML = actifs.map(p => {
        const av = p.avancement || 0;
        const avColor = av >= 80 ? '#27ae60' : av >= 40 ? '#f39c12' : '#e74c3c';
        const avBar = `<div style="background:#e0e0e0;border-radius:3px;height:8px;min-width:60px;">
            <div style="width:${av}%;background:${avColor};height:8px;border-radius:3px;"></div></div>
            <span style="font-size:.75em;">${av}%</span>`;
        const finDate = p.date_fin_prevue ? new Date(p.date_fin_prevue) : null;
        const isLate = finDate && finDate < now && p.statut === 'ACTIF';
        const finStr = finDate ? `<span style="${isLate?'color:#e74c3c;font-weight:bold;':''}">${finDate.toLocaleDateString('fr-FR')}</span>` : '-';
        return `<tr>
            <td style="text-align:center;">${_ragDot(p.statut_rag)}</td>
            <td style="font-size:.8em;">${p.code || '-'}</td>
            <td><button onclick="openProjetDashboard(${p.id})" style="background:none;border:none;cursor:pointer;text-align:left;font-size:.85em;font-weight:600;color:#2563a8;padding:0;">${_h(p.nom) || '-'}</button></td>
            <td style="font-size:.78em;">${_h(p.phase) || '-'}</td>
            <td style="min-width:90px;">${avBar}</td>
            <td style="font-size:.8em;">${fmt(p.budget_estime || 0)}</td>
            <td style="font-size:.78em;text-align:center;">-</td>
            <td style="font-size:.78em;">${finStr}</td>
        </tr>`;
    }).join('');
}

function applyProjetFilters() {
    const statut  = document.getElementById('proj-filter-statut')?.value  || '';
    const service = document.getElementById('proj-filter-service')?.value || '';
    const search  = (document.getElementById('proj-filter-search')?.value || '').toLowerCase();
    let list = _cache.projets || [];
    if (statut)  list = list.filter(p => p.statut === statut);
    if (service) list = list.filter(p => String(p.service_id) === service);
    if (search)  list = list.filter(p =>
        (p.nom  || '').toLowerCase().includes(search) ||
        (p.code || '').toLowerCase().includes(search)
    );
    _renderProjets(list);
}

function resetProjetFilters() {
    const els = ['proj-filter-statut', 'proj-filter-service', 'proj-filter-search'];
    els.forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
    _renderProjets(_cache.projets || []);
}

async function loadProjets() {
    try {
        const [data, servData] = await Promise.all([
            apiFetch('/projet'),
            apiFetch('/service_org')
        ]);
        _cache.projets = data.list || [];

        // Populate service filter
        const serviceSel = document.getElementById('proj-filter-service');
        if (serviceSel) {
            const services = servData.list || [];
            const parents  = services.filter(s => !s.parent_id);
            serviceSel.innerHTML = '<option value="">Tous les services</option>';
            parents.forEach(p => {
                const grp = document.createElement('optgroup');
                grp.label = `${p.code ? p.code + ' - ' : ''}${p.nom}`;
                const pOpt = document.createElement('option');
                pOpt.value = p.id; pOpt.textContent = p.nom;
                grp.appendChild(pOpt);
                services.filter(c => c.parent_id === p.id).forEach(c => {
                    const opt = document.createElement('option');
                    opt.value = c.id; opt.textContent = `└─ ${c.nom}`;
                    grp.appendChild(opt);
                });
                serviceSel.appendChild(grp);
            });
            // Orphans
            const parentIds = new Set(parents.map(p => p.id));
            services.filter(s => s.parent_id && !parentIds.has(s.parent_id)).forEach(s => {
                const opt = document.createElement('option');
                opt.value = s.id; opt.textContent = s.nom;
                serviceSel.appendChild(opt);
            });
        }

        applyProjetFilters();
        _renderPortfolio(_cache.projets || []);
    } catch (e) { showMsg('Erreur chargement projets', false); }
}

function switchProjTab(tabId) {
    // Chercher le contenu cible
    const target = document.getElementById('ptab-' + tabId);
    if (!target) return;
    // Désactiver tous les onglets et contenus dans la même fiche
    const container = target.closest('#fiche-projet-content');
    if (!container) return;
    container.querySelectorAll('.proj-tab').forEach(t => t.classList.remove('active'));
    container.querySelectorAll('.proj-tab-content').forEach(c => c.classList.remove('active'));
    // Activer l'onglet cliqué (le btn qui appelle switchProjTab avec ce tabId)
    container.querySelectorAll('.proj-tab').forEach(t => {
        if (t.getAttribute('onclick') === `switchProjTab('${tabId}')`) t.classList.add('active');
    });
    target.classList.add('active');
}

function printFicheProjet() {
    const titre  = document.getElementById('fiche-projet-titre').textContent;
    const content = document.getElementById('fiche-projet-content').innerHTML;
    const html = `<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8">
        <title>${titre}</title>
        <style>
            body{font-family:Arial,sans-serif;font-size:13px;color:#222;margin:24px;}
            h2{color:#1a3c5e;margin-bottom:4px;}
            label{font-size:.78em;color:#666;display:block;}
            .val{font-weight:bold;}
            table{width:100%;border-collapse:collapse;font-size:.82em;margin-top:6px;}
            th{background:#1a3c5e;color:#fff;padding:5px;text-align:left;}
            td{padding:4px 6px;border-bottom:1px solid #eee;}
            .proj-tabs{display:none;}
            .proj-tab-content{display:block!important;}
            .modal-footer{display:none;}
            @media print{body{margin:10px;}}
        </style></head><body>
        <h2>${titre}</h2>${content}</body></html>`;
    const blob = new Blob([html], { type: 'text/html' });
    const url  = URL.createObjectURL(blob);
    const w    = window.open(url, '_blank');
    w.addEventListener('load', () => { w.print(); URL.revokeObjectURL(url); });
}

async function exportFicheWord(projet_id) {
    try {
        const token = getToken();
        showMsg('Génération de la fiche Word en cours…', true);
        const res = await fetch(`/api/projet/${projet_id}/fiche_word`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            showMsg(err.error || 'Erreur génération fiche Word', false);
            return;
        }
        const blob = await res.blob();
        const url  = URL.createObjectURL(blob);
        const a    = document.createElement('a');
        const cd   = res.headers.get('Content-Disposition') || '';
        const match = cd.match(/filename="?([^"]+)"?/);
        a.download = match ? match[1] : `fiche_projet_${projet_id}.docx`;
        a.href = url;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showMsg('Fiche Word téléchargée', true);
    } catch (e) {
        showMsg('Erreur export Word : ' + e.message, false);
    }
}

// ── Viewer fiche projet HTML ─────────────────────────────────────────────────
async function openFicheHtml(projet_id, titre) {
    try {
        const token = getToken();
        showMsg('Chargement de la fiche…', true);
        const res = await fetch(`/api/projet/${projet_id}/fiche_html`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            showMsg(err.error || 'Erreur chargement fiche HTML', false);
            return;
        }
        let html = await res.text();
        html = html.replace('__BMP_TOKEN__', token);
        html = html.replace('__PROJET_ID__', projet_id);
        html = html.replace(
            'id="btn-word-dl"',
            `id="btn-word-dl" onclick="window.parent.exportFicheWord(${projet_id})"`
        );
        const iframe = document.getElementById('fiche-html-iframe');
        iframe.srcdoc = html;
        const viewer = document.getElementById('fiche-html-viewer');
        const vTitle = document.getElementById('fiche-html-viewer-title');
        if (vTitle) vTitle.textContent = titre ? `Fiche Projet — ${titre}` : 'Fiche Projet';
        viewer.dataset.projetId    = projet_id;
        viewer.dataset.projetTitre = titre || '';
        const wordBtn = document.getElementById('fiche-html-word-btn');
        if (wordBtn) wordBtn.onclick = () => exportFicheWord(projet_id);
        viewer.style.display = 'flex';
        document.body.style.overflow = 'hidden';
        showMsg('', true);
    } catch (e) {
        showMsg('Erreur : ' + e.message, false);
    }
}

function closeFicheViewer() {
    document.getElementById('fiche-html-viewer').style.display = 'none';
    document.body.style.overflow = '';
}

function printFicheHtml() {
    const iframe = document.getElementById('fiche-html-iframe');
    if (iframe && iframe.contentWindow) {
        iframe.contentWindow.print();
    }
}

// Écouter les messages depuis l'iframe fiche projet
window.addEventListener('message', function(e) {
    if (e.data === 'closeFicheViewer') { closeFicheViewer(); return; }
    if (e.data && e.data.type === 'ficheReload') {
        const viewer = document.getElementById('fiche-html-viewer');
        const pid   = e.data.id || viewer.dataset.projetId;
        const titre = viewer.dataset.projetTitre;
        if (pid) openFicheHtml(pid, titre || '');
    }
});

async function ficheProjet(id) {
    // Ouverture directe de la fiche HTML plein écran
    const cached = (_cache.projets || []).find(p => p.id === id);
    openFicheHtml(id, cached ? (cached.code || '') : '');
}

async function _ficheProjetModal(id) {
    try {
        const p = await apiFetch(`/projet/${id}`);
        document.getElementById('fiche-projet-titre').textContent =
            `${p.code || '#' + id} — ${p.nom || ''}`;

        const avPct = p.avancement || 0;
        const avCls = avPct >= 80 ? 'alert' : avPct >= 50 ? 'warning' : '';

        const oppField = (label, val) => val
            ? `<div class="opp-field"><label>${label}</label><p class="opp-val">${val}</p></div>` : '';

        const budgetRow = (label, val, highlight) => val != null && val !== ''
            ? `<div class="modal-section"><label>${label}</label><div class="val" ${highlight ? 'style="color:#e74c3c;"' : ''}>${fmt(val)} €</div></div>` : '';

        const infoRow = (label, val) => `<div class="modal-section"><label>${label}</label><div class="val">${val || '-'}</div></div>`;

        // ── Stats tâches ────────────────────────────────────────────────────
        const stats = p.taches_stats || {};
        const statColors = {'A faire':'#95a5a6','En cours':'#f39c12','En attente':'#9b59b6','Bloqué':'#e74c3c','Terminé':'#27ae60'};
        const tacheStatsHtml = Object.keys(statColors)
            .filter(s => stats[s])
            .map(s => `<span style="background:${statColors[s]};color:#fff;border-radius:12px;padding:2px 10px;font-size:.75em;font-weight:bold;margin-right:4px;">${s} : ${stats[s]}</span>`)
            .join('') || '<span style="color:#aaa;font-size:.82em;">Aucune tâche</span>';

        const tachesHtml = `
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                <span style="font-size:.72em;font-weight:bold;color:#1a3c5e;text-transform:uppercase;">Tâches (${(p.taches||[]).length})</span>
                <button onclick="showAddTacheProjet(${p.id})" style="background:#27ae60;color:#fff;border:none;border-radius:4px;padding:4px 10px;font-size:.78em;cursor:pointer;">+ Nouvelle tâche</button>
            </div>
            ${(p.taches || []).length === 0
                ? '<p style="color:#888;font-style:italic;margin:8px 0;">Aucune tâche liée.</p>'
                : `<table style="width:100%;border-collapse:collapse;font-size:.82em;">
                    <thead><tr style="background:#1a3c5e;color:#fff;">
                        <th style="padding:6px;">Titre</th><th>Statut</th><th>Priorité</th><th>Échéance</th><th>H.est.</th><th>Av.</th><th></th>
                    </tr></thead><tbody>
                    ${(p.taches || []).map(t => `<tr style="border-bottom:1px solid #eee;">
                        <td style="padding:5px;">${t.titre || '-'}</td>
                        <td>${badge(t.statut)}</td><td>${badge(t.priorite)}</td>
                        <td>${fmtDate(t.date_echeance)}</td>
                        <td>${t.estimation_heures != null ? t.estimation_heures + ' h' : '-'}</td>
                        <td>${t.avancement != null ? t.avancement + '%' : '-'}</td>
                        <td><button class="btn btn-warning btn-sm" onclick="editTache(${t.id})">Éditer</button></td>
                    </tr>`).join('')}
                    </tbody></table>
                    <div style="font-size:.78em;color:#666;margin-top:6px;">
                        Heures estimées : <strong>${p.heures_estimees || 0} h</strong> ·
                        Heures réelles : <strong>${p.heures_reelles || 0} h</strong>
                    </div>`}
            <div id="add-tache-form-${p.id}" style="display:none;margin-top:10px;padding:10px;background:#f0f4ff;border-radius:6px;border:1px solid #c5d5f5;">
                <div style="font-size:.78em;font-weight:bold;color:#2563a8;margin-bottom:8px;">Nouvelle tâche liée au projet</div>
                <input id="ntf-titre-${p.id}" type="text" placeholder="Titre *" style="width:100%;padding:6px 8px;border:1px solid #ccc;border-radius:4px;font-size:.85em;box-sizing:border-box;margin-bottom:4px;">
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:4px;">
                    <select id="ntf-statut-${p.id}" style="padding:6px 8px;border:1px solid #ccc;border-radius:4px;font-size:.85em;">
                        <option value="A faire">À faire</option>
                        <option value="En cours">En cours</option>
                        <option value="Terminé">Terminé</option>
                    </select>
                    <select id="ntf-priorite-${p.id}" style="padding:6px 8px;border:1px solid #ccc;border-radius:4px;font-size:.85em;">
                        <option value="NORMALE">Normale</option>
                        <option value="HAUTE">Haute</option>
                        <option value="BASSE">Basse</option>
                    </select>
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:6px;">
                    <div><label style="font-size:.75em;color:#666;">Échéance</label>
                        <input id="ntf-echeance-${p.id}" type="date" style="width:100%;padding:5px 8px;border:1px solid #ccc;border-radius:4px;font-size:.85em;box-sizing:border-box;">
                    </div>
                    <div><label style="font-size:.75em;color:#666;">Heures estimées</label>
                        <input id="ntf-heures-${p.id}" type="number" min="0" step="0.5" placeholder="0" style="width:100%;padding:5px 8px;border:1px solid #ccc;border-radius:4px;font-size:.85em;box-sizing:border-box;">
                    </div>
                </div>
                <div style="display:flex;gap:6px;">
                    <button onclick="saveNewTacheProjet(${p.id})" style="background:#27ae60;color:#fff;border:none;border-radius:4px;padding:5px 14px;cursor:pointer;font-size:.82em;">Créer</button>
                    <button onclick="document.getElementById('add-tache-form-${p.id}').style.display='none'" style="background:#95a5a6;color:#fff;border:none;border-radius:4px;padding:5px 14px;cursor:pointer;font-size:.82em;">Annuler</button>
                </div>
            </div>`;

        const bcsHtml = (p.bons_commande || []).length === 0
            ? '<p style="color:#888;font-style:italic;margin:8px 0;">Aucun BC lié.</p>'
            : `<table style="width:100%;border-collapse:collapse;font-size:.82em;margin-top:6px;">
                <thead><tr style="background:#1a3c5e;color:#fff;">
                    <th style="padding:6px;">N° BC</th><th>Objet</th><th>Fournisseur</th><th>Montant TTC</th><th>Statut</th>
                </tr></thead><tbody>
                ${(p.bons_commande || []).map(b => `<tr style="border-bottom:1px solid #eee;">
                    <td style="padding:5px;">${b.numero_bc || '-'}</td>
                    <td>${b.objet || '-'}</td>
                    <td style="color:#666;">${b.fournisseur_nom || '-'}</td>
                    <td style="text-align:right;">${fmt(b.montant_ttc)} €</td>
                    <td>${badge(b.statut)}</td>
                </tr>`).join('')}
                </tbody></table>`;

        // ── Opportunité : registre risques ───────────────────────────────────
        let registreHtml = '';
        if (p.registre_risques) {
            try {
                const risques = typeof p.registre_risques === 'string'
                    ? JSON.parse(p.registre_risques) : p.registre_risques;
                if (Array.isArray(risques) && risques.length) {
                    const critColor = c => c >= 12 ? '#e74c3c' : c >= 6 ? '#e67e22' : c >= 3 ? '#f1c40f' : '#27ae60';
                    registreHtml = `
                    <div style="margin-top:16px;background:#fff;border-radius:8px;padding:12px;border:1px solid #eee;">
                        <div style="font-size:.75em;font-weight:bold;color:#c0392b;margin-bottom:8px;text-transform:uppercase;">⚠ Registre des risques (${risques.length})</div>
                        <table style="width:100%;border-collapse:collapse;font-size:.8em;">
                            <thead><tr style="background:#2c3e50;color:#fff;">
                                <th style="padding:5px 8px;">Description</th>
                                <th style="padding:5px 4px;">Catégorie</th>
                                <th style="padding:5px 4px;text-align:center;">P</th>
                                <th style="padding:5px 4px;text-align:center;">I</th>
                                <th style="padding:5px 4px;text-align:center;">Criticité</th>
                                <th style="padding:5px 8px;">Action corrective</th>
                                <th style="padding:5px 4px;">Statut</th>
                            </tr></thead><tbody>
                            ${risques.map(r => {
                                const crit = (parseInt(r.proba)||1) * (parseInt(r.impact)||1);
                                return `<tr style="border-bottom:1px solid #eee;">
                                    <td style="padding:4px 8px;">${r.description || '-'}</td>
                                    <td style="padding:4px;">${r.categorie || '-'}</td>
                                    <td style="text-align:center;">${r.proba || 1}</td>
                                    <td style="text-align:center;">${r.impact || 1}</td>
                                    <td style="text-align:center;">
                                        <span style="background:${critColor(crit)};color:#fff;border-radius:10px;padding:1px 8px;font-weight:bold;">${crit}</span>
                                    </td>
                                    <td style="padding:4px 8px;color:#555;">${r.action || '-'}</td>
                                    <td>${badge(r.statut)}</td>
                                </tr>`;
                            }).join('')}
                            </tbody></table>
                    </div>`;
                }
            } catch(e) {}
        }

        // ── Opportunité : 6 contraintes ─────────────────────────────────────
        let contraintes6Html = '';
        if (p.contraintes_6axes) {
            try {
                const c6 = typeof p.contraintes_6axes === 'string'
                    ? JSON.parse(p.contraintes_6axes) : p.contraintes_6axes;
                const axes = [
                    ['🎯 Portée', c6.portee], ['💰 Coûts', c6.couts], ['⏱ Délais', c6.delais],
                    ['⚡ Ressources', c6.ressources], ['🔍 Qualité', c6.qualite], ['🎲 Risques', c6.risques]
                ].filter(([,v]) => v);
                if (axes.length) {
                    contraintes6Html = `
                    <div style="margin-top:16px;background:#fff;border-radius:8px;padding:12px;border:1px solid #eee;">
                        <div style="font-size:.75em;font-weight:bold;color:#2980b9;margin-bottom:8px;text-transform:uppercase;">🔗 6 Contraintes du projet</div>
                        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
                            ${axes.map(([label, val]) => `<div style="background:#f8f9fa;border-radius:6px;padding:10px;">
                                <div style="font-size:.78em;font-weight:bold;color:#444;margin-bottom:4px;">${label}</div>
                                <div style="font-size:.82em;white-space:pre-wrap;color:#333;">${val}</div>
                            </div>`).join('')}
                        </div>
                    </div>`;
                }
            } catch(e) {}
        }

        // ── Triangle d'Or ───────────────────────────────────────────────────
        let triangleHtml = '';
        if (p.triangle_tensions) {
            try {
                const tt = typeof p.triangle_tensions === 'string'
                    ? JSON.parse(p.triangle_tensions) : p.triangle_tensions;
                const axes = [
                    ['🎯 Portée', tt.tension_portee || tt.portee],
                    ['💰 Coûts',  tt.tension_couts  || tt.couts],
                    ['⏱ Délais', tt.tension_delais  || tt.delais]
                ];
                const anySet = axes.some(([,v]) => v);
                if (anySet) {
                    triangleHtml = `
                    <div style="margin-top:16px;background:#fff;border-radius:8px;padding:12px;border:1px solid #eee;">
                        <div style="font-size:.75em;font-weight:bold;color:#8e44ad;margin-bottom:8px;text-transform:uppercase;">🔺 Triangle d'Or — Tensions</div>
                        <div style="display:flex;gap:16px;flex-wrap:wrap;">
                            ${axes.map(([label, val]) => {
                                const v = parseInt(val) || 1; const pct = v / 5 * 100;
                                const col = v >= 4 ? '#e74c3c' : v >= 3 ? '#e67e22' : '#27ae60';
                                return `<div style="flex:1;min-width:140px;text-align:center;">
                                    <div style="font-size:.82em;font-weight:bold;margin-bottom:4px;">${label}</div>
                                    <div style="font-size:1.8em;font-weight:bold;color:${col};">${v}<span style="font-size:.5em;color:#999;">/5</span></div>
                                    <div style="background:#eee;border-radius:4px;height:8px;margin:4px 0;">
                                        <div style="background:${col};width:${pct}%;height:8px;border-radius:4px;"></div>
                                    </div>
                                </div>`;
                            }).join('')}
                        </div>
                        ${tt.arbitrage ? `<div style="margin-top:8px;font-size:.82em;color:#555;font-style:italic;">💬 Arbitrage : ${tt.arbitrage}</div>` : ''}
                    </div>`;
                }
            } catch(e) {}
        }
        if (p.arbitrage && !triangleHtml) {
            triangleHtml = `<div style="margin-top:12px;background:#fff;border-radius:8px;padding:10px;border:1px solid #eee;">
                <div style="font-size:.75em;font-weight:bold;color:#555;margin-bottom:4px;">ARBITRAGE</div>
                <div style="font-size:.85em;white-space:pre-wrap;">${p.arbitrage}</div>
            </div>`;
        }

        // ── Équipe HTML ─────────────────────────────────────────────────────
        const mkContact = (nom, email, tel) =>
            `${nom || '-'}${email ? ` <span style="color:#2563a8;font-size:.85em;">✉ ${email}</span>` : ''}${tel ? ` <span style="color:#555;font-size:.85em;">📞 ${tel}</span>` : ''}`;

        const equipeHtml = (() => {
            const parts = [];
            if (p.responsable_nom || p.chef_projet_nom) {
                parts.push(`<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px;">
                    <div style="background:#eef;border-radius:8px;padding:12px;">
                        <div style="font-size:.72em;font-weight:bold;color:#2563a8;text-transform:uppercase;margin-bottom:6px;">👤 Responsable projet</div>
                        <div style="font-size:.88em;">${mkContact(p.responsable_nom, p.responsable_nom_email, p.responsable_nom_tel)}</div>
                    </div>
                    <div style="background:#efe;border-radius:8px;padding:12px;">
                        <div style="font-size:.72em;font-weight:bold;color:#27ae60;text-transform:uppercase;margin-bottom:6px;">👤 Chef de projet</div>
                        <div style="font-size:.88em;">${mkContact(p.chef_projet_nom, p.chef_projet_nom_email, p.chef_projet_nom_tel)}</div>
                    </div>
                </div>`);
            }
            const membreRows = (p.equipe || []).map(m => `<tr style="border-bottom:1px solid #eee;">
                <td style="padding:4px 8px;font-weight:bold;">${m.nom_complet || '-'}</td>
                <td style="color:#666;">${m.fonction || '-'}</td>
                <td style="color:#2563a8;">${m.email || '-'}</td>
                <td style="color:#555;">${m.telephone || '-'}</td>
                <td style="text-align:center;"><button onclick="deleteMembreEquipe(${id},${m.membre_id})" style="background:none;border:none;color:#e74c3c;cursor:pointer;font-size:1.1em;line-height:1;" title="Retirer">×</button></td>
            </tr>`).join('');
            parts.push(`<div style="background:#fff;border-radius:8px;padding:12px;border:1px solid #eee;margin-bottom:10px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                    <div style="font-size:.75em;font-weight:bold;color:#555;text-transform:uppercase;">👥 Membres de l'équipe (${(p.equipe||[]).length})</div>
                    <button onclick="showAddMembreForm(${id})" style="background:#2563a8;color:#fff;border:none;border-radius:4px;padding:4px 10px;font-size:.78em;cursor:pointer;">+ Ajouter</button>
                </div>
                ${(p.equipe||[]).length ? `<table style="width:100%;border-collapse:collapse;font-size:.82em;">
                    <thead><tr style="background:#2c3e50;color:#fff;">
                        <th style="padding:5px 8px;">Nom</th><th>Fonction</th><th>Email</th><th>Tél.</th><th></th>
                    </tr></thead><tbody>${membreRows}</tbody></table>`
                : '<p style="color:#aaa;font-size:.85em;font-style:italic;margin:4px 0 8px;">Aucun membre.</p>'}
                <div id="add-membre-form-${id}" style="display:none;margin-top:10px;padding:10px;background:#f0f4ff;border-radius:6px;border:1px solid #c5d5f5;">
                    <div style="font-size:.78em;font-weight:bold;color:#2563a8;margin-bottom:6px;">Nouveau membre</div>
                    <select onchange="loadContactsForSelect(document.getElementById('new-membre-select-${id}'),this.value)" style="width:100%;padding:5px 8px;border:1px solid #ccc;border-radius:4px;font-size:.8em;box-sizing:border-box;margin-bottom:4px;">
                        <option value="">— Tous types de contact —</option>
                        <option value="Élu">Élu</option>
                        <option value="Direction">Direction</option>
                        <option value="Service">Service</option>
                        <option value="Prestataire">Prestataire</option>
                        <option value="AMO">AMO</option>
                    </select>
                    <select id="new-membre-select-${id}" style="width:100%;padding:6px 8px;border:1px solid #ccc;border-radius:4px;font-size:.85em;box-sizing:border-box;margin-bottom:4px;">
                        <option value="">-- Sélectionner un contact --</option>
                    </select>
                    <select id="new-service-select-${id}" style="width:100%;padding:6px 8px;border:1px solid #ccc;border-radius:4px;font-size:.85em;box-sizing:border-box;margin-bottom:4px;">
                        <option value="">-- Ou sélectionner un service --</option>
                    </select>
                    <input id="new-membre-label-${id}" type="text" placeholder="Ou saisir un nom libre" style="width:100%;padding:6px 8px;border:1px solid #ccc;border-radius:4px;font-size:.85em;box-sizing:border-box;margin-bottom:6px;">
                    <div style="display:flex;gap:6px;">
                        <button onclick="saveMembreEquipe(${id})" style="background:#27ae60;color:#fff;border:none;border-radius:4px;padding:5px 14px;cursor:pointer;font-size:.82em;">Ajouter</button>
                        <button onclick="document.getElementById('add-membre-form-${id}').style.display='none'" style="background:#95a5a6;color:#fff;border:none;border-radius:4px;padding:5px 14px;cursor:pointer;font-size:.82em;">Annuler</button>
                    </div>
                </div>
            </div>`);
            if ((p.prestataires || []).length) {
                parts.push(`<div style="background:#fff;border-radius:8px;padding:12px;border:1px solid #eee;">
                    <div style="font-size:.75em;font-weight:bold;color:#555;margin-bottom:8px;text-transform:uppercase;">🏢 Prestataires / Fournisseurs (${p.prestataires.length})</div>
                    <table style="width:100%;border-collapse:collapse;font-size:.82em;">
                        <thead><tr style="background:#2c3e50;color:#fff;">
                            <th style="padding:5px 8px;">Fournisseur</th><th>Contact principal</th><th>Email</th><th>Tél.</th>
                        </tr></thead><tbody>
                        ${p.prestataires.map(pr => `<tr style="border-bottom:1px solid #eee;">
                            <td style="padding:4px 8px;font-weight:bold;">${pr.fournisseur_nom || '-'}</td>
                            <td>${pr.contact_principal || '-'}</td>
                            <td style="color:#2563a8;">${pr.email || '-'}</td>
                            <td>${pr.telephone || '-'}</td>
                        </tr>`).join('')}
                        </tbody></table>
                </div>`);
            }
            return parts.length ? parts.join('') : `<div style="background:#fff;border-radius:8px;padding:12px;border:1px solid #eee;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                    <div style="font-size:.75em;font-weight:bold;color:#555;text-transform:uppercase;">👥 Membres de l'équipe (0)</div>
                    <button onclick="showAddMembreForm(${id})" style="background:#2563a8;color:#fff;border:none;border-radius:4px;padding:4px 10px;font-size:.78em;cursor:pointer;">+ Ajouter</button>
                </div>
                <p style="color:#aaa;font-size:.85em;font-style:italic;margin:4px 0 8px;">Aucun membre d'équipe renseigné.</p>
                <div id="add-membre-form-${id}" style="display:none;margin-top:10px;padding:10px;background:#f0f4ff;border-radius:6px;border:1px solid #c5d5f5;">
                    <div style="font-size:.78em;font-weight:bold;color:#2563a8;margin-bottom:6px;">Nouveau membre</div>
                    <select onchange="loadContactsForSelect(document.getElementById('new-membre-select-${id}'),this.value)" style="width:100%;padding:5px 8px;border:1px solid #ccc;border-radius:4px;font-size:.8em;box-sizing:border-box;margin-bottom:4px;">
                        <option value="">— Tous types de contact —</option>
                        <option value="Élu">Élu</option>
                        <option value="Direction">Direction</option>
                        <option value="Service">Service</option>
                        <option value="Prestataire">Prestataire</option>
                        <option value="AMO">AMO</option>
                    </select>
                    <select id="new-membre-select-${id}" style="width:100%;padding:6px 8px;border:1px solid #ccc;border-radius:4px;font-size:.85em;box-sizing:border-box;margin-bottom:4px;">
                        <option value="">-- Sélectionner un contact --</option>
                    </select>
                    <select id="new-service-select-${id}" style="width:100%;padding:6px 8px;border:1px solid #ccc;border-radius:4px;font-size:.85em;box-sizing:border-box;margin-bottom:4px;">
                        <option value="">-- Ou sélectionner un service --</option>
                    </select>
                    <input id="new-membre-label-${id}" type="text" placeholder="Ou saisir un nom libre" style="width:100%;padding:6px 8px;border:1px solid #ccc;border-radius:4px;font-size:.85em;box-sizing:border-box;margin-bottom:6px;">
                    <div style="display:flex;gap:6px;">
                        <button onclick="saveMembreEquipe(${id})" style="background:#27ae60;color:#fff;border:none;border-radius:4px;padding:5px 14px;cursor:pointer;font-size:.82em;">Ajouter</button>
                        <button onclick="document.getElementById('add-membre-form-${id}').style.display='none'" style="background:#95a5a6;color:#fff;border:none;border-radius:4px;padding:5px 14px;cursor:pointer;font-size:.82em;">Annuler</button>
                    </div>
                </div>
            </div>`;
        })();

        // ── Contacts HTML ───────────────────────────────────────────────────
        const contactRows = (p.contacts_externes || []).map(c => {
            const delBtn = c.contact_id
                ? `onclick="deleteProjetContact(${id},${c.contact_id},null)"`
                : `onclick="deleteProjetContact(${id},null,'${(c.nom_affiche||'').replace(/['\u2018\u2019]/g,"\\'")}')"`;
            return `<tr style="border-bottom:1px solid #eee;">
                    <td style="padding:5px;font-weight:bold;color:#2563a8;">${c.role || '-'}</td>
                    <td>${c.nom_affiche || (c.prenom + ' ' + c.nom).trim() || '-'}</td>
                    <td style="color:#666;">${c.organisation || '-'}</td>
                    <td style="color:#2563a8;">${c.email || '-'}</td>
                    <td>${c.telephone || '-'}</td>
                    <td style="text-align:center;"><button ${delBtn} style="background:none;border:none;color:#e74c3c;cursor:pointer;font-size:1.1em;line-height:1;" title="Retirer">×</button></td>
                </tr>`;
        }).join('');
        const contactsHtml = `<div style="background:#fff;border-radius:8px;padding:12px;border:1px solid #eee;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <div style="font-size:.75em;font-weight:bold;color:#555;text-transform:uppercase;">📞 Contacts externes (${(p.contacts_externes||[]).length})</div>
                <button onclick="showAddContactForm(${id})" style="background:#2563a8;color:#fff;border:none;border-radius:4px;padding:4px 10px;font-size:.78em;cursor:pointer;">+ Ajouter</button>
            </div>
            ${(p.contacts_externes||[]).length ? `<table style="width:100%;border-collapse:collapse;font-size:.82em;">
                <thead><tr style="background:#1a3c5e;color:#fff;">
                    <th style="padding:6px;">Rôle</th><th>Nom</th><th>Organisation</th><th>Email</th><th>Tél.</th><th></th>
                </tr></thead><tbody>${contactRows}</tbody></table>`
            : '<p style="color:#aaa;font-size:.85em;font-style:italic;margin:4px 0 8px;">Aucun contact externe lié.</p>'}
            <div id="add-contact-form-${id}" style="display:none;margin-top:10px;padding:10px;background:#f0f4ff;border-radius:6px;border:1px solid #c5d5f5;">
                <div style="font-size:.78em;font-weight:bold;color:#2563a8;margin-bottom:6px;">Lier un contact</div>
                <select onchange="loadContactsIdForSelect(document.getElementById('new-contact-id-${id}'),this.value,document.getElementById('new-contact-search-${id}'))" style="width:100%;padding:5px 8px;border:1px solid #ccc;border-radius:4px;font-size:.8em;box-sizing:border-box;margin-bottom:4px;">
                    <option value="">— Tous types de contact —</option>
                    <option value="Élu">Élu</option>
                    <option value="Direction">Direction</option>
                    <option value="Service">Service</option>
                    <option value="Prestataire">Prestataire</option>
                    <option value="AMO">AMO</option>
                </select>
                <input id="new-contact-search-${id}" type="text" placeholder="🔍 Rechercher par nom..." oninput="filterContactSelect(this,'new-contact-id-${id}')" style="width:100%;padding:6px 8px;border:1px solid #ccc;border-radius:4px;font-size:.85em;box-sizing:border-box;margin-bottom:4px;">
                <select id="new-contact-id-${id}" size="5" style="width:100%;padding:4px;border:1px solid #ccc;border-radius:4px;font-size:.85em;box-sizing:border-box;margin-bottom:4px;">
                    <option value="">-- Sélectionner un contact --</option>
                </select>
                <input id="new-contact-libre-${id}" type="text" placeholder="Ou saisir un nom libre (si absent de la liste)" style="width:100%;padding:6px 8px;border:1px solid #ccc;border-radius:4px;font-size:.85em;box-sizing:border-box;margin-bottom:6px;">
                <input id="new-contact-role-${id}" type="text" placeholder="Rôle (ex: Chef de projet, Référent...)" style="width:100%;padding:6px 8px;border:1px solid #ccc;border-radius:4px;font-size:.85em;box-sizing:border-box;margin-bottom:6px;">
                <div style="display:flex;gap:6px;">
                    <button onclick="saveProjetContact(${id})" style="background:#27ae60;color:#fff;border:none;border-radius:4px;padding:5px 14px;cursor:pointer;font-size:.82em;">Ajouter</button>
                    <button onclick="document.getElementById('add-contact-form-${id}').style.display='none'" style="background:#95a5a6;color:#fff;border:none;border-radius:4px;padding:5px 14px;cursor:pointer;font-size:.82em;">Annuler</button>
                </div>
            </div>
        </div>`;

        // ── Documents HTML ──────────────────────────────────────────────────
        const documentsHtml = (p.documents || []).length === 0
            ? '<p style="color:#aaa;font-style:italic;margin:12px 0;">Aucun document attaché.</p>'
            : `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px;margin-top:6px;">
                ${p.documents.map(d => `<div style="background:#f8f9fa;border:1px solid #ddd;border-radius:8px;padding:10px;">
                    <div style="font-size:.78em;font-weight:bold;color:#2563a8;margin-bottom:4px;">📄 ${d.type_document || 'Document'}</div>
                    <div style="font-size:.82em;word-break:break-all;">${d.nom_fichier || '-'}</div>
                    <div style="font-size:.72em;color:#888;margin-top:4px;">
                        ${d.taille ? Math.round(d.taille/1024) + ' Ko · ' : ''}${fmtDate(d.date_ajout)}
                    </div>
                </div>`).join('')}
            </div>`;

        const nEquipe = (p.equipe||[]).length + (p.prestataires||[]).length + (p.responsable_nom ? 1 : 0);
        const hasOpp  = p.objectifs || p.enjeux || p.gains || p.risques || p.contraintes || p.solutions || p.registre_risques || p.triangle_tensions;

        document.getElementById('fiche-projet-content').innerHTML = `
            <div class="proj-tabs">
                <span class="proj-tab active" onclick="switchProjTab('general')">📋 Général</span>
                <span class="proj-tab" onclick="switchProjTab('opportunite')">🎯 Opportunité${p.registre_risques ? ' ⚠' : ''}</span>
                <span class="proj-tab" onclick="switchProjTab('budget')">💰 Budget</span>
                <span class="proj-tab" onclick="switchProjTab('equipe')">👥 Équipe${nEquipe ? ' ('+nEquipe+')' : ''}</span>
                <span class="proj-tab" onclick="switchProjTab('contacts')">📞 Contacts (${(p.contacts_externes||[]).length})</span>
                <span class="proj-tab" onclick="switchProjTab('documents')">📄 Documents (${(p.documents||[]).length})</span>
                <span class="proj-tab" onclick="switchProjTab('taches')">✓ Tâches (${(p.taches||[]).length})</span>
                <span class="proj-tab" onclick="switchProjTab('bc')">🛒 BC (${(p.bons_commande||[]).length})</span>
                <span class="proj-tab" onclick="switchProjTab('gantt-proj');loadProjetGantt(${p.id})">📊 Gantt</span>
            </div>

            <!-- ── Général ── -->
            <div class="proj-tab-content active" id="ptab-general">
                <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:12px;">
                    <div style="flex:1;min-width:200px;background:#f0f4ff;border-radius:8px;padding:12px;">
                        <div style="font-size:.72em;font-weight:bold;color:#2563a8;margin-bottom:8px;text-transform:uppercase;">Identification</div>
                        <div class="modal-grid">
                            ${infoRow('Statut', badge(p.statut))}
                            ${infoRow('Priorité', badge(p.priorite))}
                            ${infoRow('Type', p.type_projet)}
                            ${infoRow('Phase', p.phase)}
                            <div class="modal-section" style="grid-column:span 2;">${infoRow('Service', p.service_code ? p.service_code + ' – ' + p.service_nom : p.service_nom)}</div>
                            ${infoRow('Créé le', fmtDate(p.date_creation))}
                        </div>
                    </div>
                    <div style="flex:1;min-width:200px;background:#f0fff4;border-radius:8px;padding:12px;">
                        <div style="font-size:.72em;font-weight:bold;color:#27ae60;margin-bottom:8px;text-transform:uppercase;">Calendrier</div>
                        <div class="modal-grid">
                            ${infoRow('Début', fmtDate(p.date_debut))}
                            ${infoRow('Fin prévue', fmtDate(p.date_fin_prevue))}
                            ${infoRow('Fin réelle', fmtDate(p.date_fin_reelle))}
                            <div class="modal-section" style="grid-column:span 2;">
                                <label>Avancement — ${avPct}%</label>
                                <div class="progress-bar-wrap" style="height:12px;margin-top:4px;">
                                    <div class="progress-bar-fill ${avCls}" style="width:${avPct}%;height:12px;"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div style="background:#fff;border-radius:8px;padding:10px;margin-top:8px;border:1px solid #eee;">
                    <div style="font-size:.72em;font-weight:bold;color:#555;margin-bottom:6px;text-transform:uppercase;">Tâches — Répartition</div>
                    <div>${tacheStatsHtml}</div>
                </div>
                ${p.description ? `<div style="background:#fff;border-radius:8px;padding:12px;margin-top:8px;border:1px solid #eee;">
                    <div style="font-size:.72em;font-weight:bold;color:#555;margin-bottom:6px;text-transform:uppercase;">Description</div>
                    <div style="font-size:.88em;white-space:pre-wrap;">${p.description}</div>
                </div>` : ''}
            </div>

            <!-- ── Opportunité ── -->
            <div class="proj-tab-content" id="ptab-opportunite">
                ${hasOpp ? `
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                    ${oppField('Objectifs métier', p.objectifs)}
                    ${oppField('Enjeux stratégiques', p.enjeux)}
                    ${oppField('Gains / Bénéfices', p.gains)}
                    ${oppField('Risques si non réalisation', p.risques)}
                    ${oppField('Contraintes', p.contraintes)}
                    ${oppField('Solutions envisagées', p.solutions)}
                </div>
                ${registreHtml}
                ${contraintes6Html}
                ${triangleHtml}
                ` : '<p style="color:#aaa;font-style:italic;margin:12px 0;">Aucune information saisie. Cliquez sur Éditer pour compléter.</p>'}
            </div>

            <!-- ── Budget ── -->
            <div class="proj-tab-content" id="ptab-budget">
                <div style="background:#fff8e1;border-radius:8px;padding:16px;margin-bottom:10px;">
                    <div class="modal-grid">
                        ${budgetRow('Budget prévisionnel', p.budget_initial)}
                        ${budgetRow('Budget estimé', p.budget_estime)}
                        ${budgetRow('Budget voté', p.budget_actuel)}
                        ${budgetRow('Consommé (BCs validés)', p.budget_consomme_calcule,
                            p.budget_actuel && p.budget_consomme_calcule > p.budget_actuel)}
                        ${budgetRow('Total BCs liés (TTC)', p.montant_bc_total)}
                    </div>
                    ${p.budget_actuel && p.budget_consomme_calcule != null ? `
                    <div style="margin-top:12px;">
                        <label style="font-size:.82em;color:#666;">Taux de consommation</label>
                        <div>${progressBar(p.budget_consomme_calcule, p.budget_actuel)}</div>
                    </div>` : ''}
                    ${!p.budget_initial && !p.budget_estime && !p.budget_actuel
                        ? '<p style="color:#aaa;font-style:italic;">Aucun budget renseigné.</p>' : ''}
                </div>
                <div style="background:#fff;border-radius:8px;padding:12px;border:1px solid #eee;">
                    <div style="font-size:.72em;font-weight:bold;color:#1a3c5e;margin-bottom:8px;text-transform:uppercase;">
                        Bons de commande liés (${(p.bons_commande||[]).length})
                    </div>
                    ${bcsHtml}
                </div>
            </div>

            <!-- ── Équipe ── -->
            <div class="proj-tab-content" id="ptab-equipe">${equipeHtml}</div>

            <!-- ── Contacts ── -->
            <div class="proj-tab-content" id="ptab-contacts">${contactsHtml}</div>

            <!-- ── Documents ── -->
            <div class="proj-tab-content" id="ptab-documents">${documentsHtml}</div>

            <!-- ── Tâches ── -->
            <div class="proj-tab-content" id="ptab-taches">${tachesHtml}</div>

            <!-- ── BC ── -->
            <div class="proj-tab-content" id="ptab-bc">${bcsHtml}</div>

            <!-- ── Gantt projet ── -->
            <div class="proj-tab-content" id="ptab-gantt-proj" style="padding:10px 0;">
                <div class="gantt-filter-bar" style="padding:8px 0 12px;">
                    <select id="gantt-proj-view-mode" class="form-control" style="width:auto;" onchange="updateProjetGanttViewMode()">
                        <option value="Week">Semaine</option>
                        <option value="Month">Mois</option>
                        <option value="Day">Jour</option>
                    </select>
                </div>
                <div class="gantt-wrap"><svg id="gantt-projet-svg"></svg></div>
                <p id="gantt-proj-empty" style="color:#aaa;font-style:italic;display:none;">Aucune tâche avec date début + date échéance renseignées.</p>
            </div>

            <div class="modal-footer" style="margin-top:14px;">
                <button class="btn" style="background:#0d6efd;color:#fff;" onclick="closeModal('modal-fiche-projet');openFicheHtml(${p.id},'${(p.code||'').replace(/'/g,"\\'")}')">&#128196; Voir la fiche</button>
                <button class="btn" style="background:#198754;color:#fff;" onclick="exportFicheWord(${p.id})">&#11015; Télécharger Word</button>
                <button class="btn btn-warning" onclick="closeModal('modal-fiche-projet');editProjet(${p.id})">&#9998; Éditer le projet</button>
                <button class="btn btn-danger" onclick="closeModal('modal-fiche-projet')">Fermer</button>
            </div>`;
        openModal('modal-fiche-projet');
    } catch (e) { showMsg('Erreur chargement fiche projet', false); }
}

async function addProjet() {
    const body = {
        code:          document.getElementById('projet-code').value,
        nom:           document.getElementById('projet-nom').value,
        type_projet:   document.getElementById('projet-type').value || null,
        phase:         document.getElementById('projet-phase').value || null,
        statut:        document.getElementById('projet-statut').value,
        priorite:      document.getElementById('projet-priorite').value || null,
        service_id:    document.getElementById('projet-service').value || null,
        budget_estime: document.getElementById('projet-budget').value || null,
        date_debut:    document.getElementById('projet-debut').value || null,
        date_fin_prevue: document.getElementById('projet-fin').value || null,
        avancement:    0,
    };
    if (!body.nom) { showMsg('Le nom est obligatoire', false); return; }
    try {
        const res = await apiFetch('/projet', { method: 'POST', body: JSON.stringify(body) });
        if (res.success) { showMsg('Projet ajouté'); loadProjets(); initRefs(); }
        else showMsg(res.error || 'Erreur', false);
    } catch (e) { showMsg(e.message, false); }
}

function editProjet(id) {
    const data = _cache.projets?.find(p => p.id === id);
    if (!data) { showMsg('Données projet non chargées, rechargez', false); return; }
    const d2 = _toISODate;
    document.getElementById('edit-projet-id').value                = data.id;
    document.getElementById('edit-projet-code').value             = data.code || '';
    document.getElementById('edit-projet-nom').value              = data.nom || '';
    document.getElementById('edit-projet-description').value      = data.description || '';
    document.getElementById('edit-projet-type').value             = data.type_projet || '';
    document.getElementById('edit-projet-phase').value            = data.phase || '';
    document.getElementById('edit-projet-statut').value           = data.statut || 'ACTIF';
    document.getElementById('edit-projet-priorite').value         = data.priorite || '';
    document.getElementById('edit-projet-service').value          = data.service_id || '';
    document.getElementById('edit-projet-budget-initial').value   = data.budget_initial || '';
    document.getElementById('edit-projet-budget').value           = data.budget_estime || '';
    document.getElementById('edit-projet-budget-actuel').value    = data.budget_actuel || '';
    document.getElementById('edit-projet-avancement').value       = data.avancement ?? '';
    document.getElementById('edit-projet-debut').value            = d2(data.date_debut);
    document.getElementById('edit-projet-fin').value              = d2(data.date_fin_prevue);
    document.getElementById('edit-projet-fin-reelle').value       = d2(data.date_fin_reelle);
    document.getElementById('edit-projet-objectifs').value        = data.objectifs || '';
    document.getElementById('edit-projet-enjeux').value           = data.enjeux || '';
    document.getElementById('edit-projet-gains').value            = data.gains || '';
    document.getElementById('edit-projet-risques').value          = data.risques || '';
    document.getElementById('edit-projet-contraintes').value      = data.contraintes || '';
    document.getElementById('edit-projet-solutions').value        = data.solutions || '';
    openModal('modal-edit-projet');
}

async function saveProjet() {
    const id = document.getElementById('edit-projet-id').value;
    const body = {
        code:            document.getElementById('edit-projet-code').value,
        nom:             document.getElementById('edit-projet-nom').value,
        description:     document.getElementById('edit-projet-description').value,
        type_projet:     document.getElementById('edit-projet-type').value || null,
        phase:           document.getElementById('edit-projet-phase').value || null,
        statut:          document.getElementById('edit-projet-statut').value,
        priorite:        document.getElementById('edit-projet-priorite').value || null,
        service_id:      document.getElementById('edit-projet-service').value || null,
        budget_initial:  document.getElementById('edit-projet-budget-initial').value || null,
        budget_estime:   document.getElementById('edit-projet-budget').value || null,
        budget_actuel:   document.getElementById('edit-projet-budget-actuel').value || null,
        avancement:      document.getElementById('edit-projet-avancement').value || 0,
        date_debut:      document.getElementById('edit-projet-debut').value || null,
        date_fin_prevue: document.getElementById('edit-projet-fin').value || null,
        date_fin_reelle: document.getElementById('edit-projet-fin-reelle').value || null,
        objectifs:       document.getElementById('edit-projet-objectifs').value || null,
        enjeux:          document.getElementById('edit-projet-enjeux').value || null,
        gains:           document.getElementById('edit-projet-gains').value || null,
        risques:         document.getElementById('edit-projet-risques').value || null,
        contraintes:     document.getElementById('edit-projet-contraintes').value || null,
        solutions:       document.getElementById('edit-projet-solutions').value || null,
    };
    if (!body.nom) { showMsg('Le nom est obligatoire', false); return; }
    try {
        const res = await apiFetch(`/projet/${id}`, { method: 'PUT', body: JSON.stringify(body) });
        if (res.success) { showMsg('Projet mis à jour'); closeModal('modal-edit-projet'); loadProjets(); initRefs(); }
        else showMsg(res.error || 'Erreur', false);
    } catch (e) { showMsg(e.message, false); }
}

async function deleteProjet(id) {
    if (!confirm('Supprimer ce projet ?')) return;
    try {
        const res = await apiFetch(`/projet/${id}`, { method: 'DELETE' });
        if (res.success) { showMsg('Projet supprimé'); loadProjets(); initRefs(); }
        else showMsg(res.error || 'Erreur', false);
    } catch (e) { showMsg(e.message, false); }
}

// ─── TÂCHES ────────────────────────────────────────────────

async function loadTaches() {
    const projetId = document.getElementById('tache-filter-projet')?.value;
    const statut   = document.getElementById('tache-filter-statut')?.value;
    try {
        const data = await apiFetch('/tache');
        _cache.taches = data.list || [];
        let list = _cache.taches;
        if (projetId) list = list.filter(t => String(t.projet_id) === projetId);
        if (statut)   list = list.filter(t => t.statut === statut);
        const tbody = document.getElementById('taches-tbody');
        tbody.innerHTML = list.map(t => `
            <tr>
                <td>${t.id}</td>
                <td><strong>${t.titre || '-'}</strong></td>
                <td>${t.projet_nom || '-'}</td>
                <td>${badge(t.statut)}</td>
                <td>${badge(t.priorite)}</td>
                <td>${fmtDate(t.date_echeance)}</td>
                <td>${t.estimation_heures != null ? t.estimation_heures + ' h' : '-'}</td>
                <td>${t.avancement != null ? t.avancement + ' %' : '-'}</td>
                <td>${t.assignee_nom
                    ? `<span style="font-size:.82em;color:#2563a8;">${t.assignee_nom}</span>`
                    : '<span style="color:#aaa;font-size:.82em;">—</span>'}</td>
                <td style="white-space:nowrap;">
                    <button class="btn btn-warning btn-sm" onclick="editTache(${t.id})">Éditer</button>
                    <button class="btn btn-danger btn-sm" onclick="deleteTache(${t.id})">Suppr.</button>
                </td>
            </tr>`).join('');

        // Peupler le select "Assigner à" du formulaire de création
        const addSel = document.getElementById('tache-assignee');
        if (addSel && addSel.options.length <= 1) {
            await _populateMembresSelect(addSel, null);
        }
    } catch (e) { showMsg('Erreur chargement tâches', false); }
}

function toggleRapportEditor() {
    const type = document.getElementById('edit-tache-type')?.value;
    const section = document.getElementById('rapport-reunion-section');
    if (!section) return;
    const show = type === 'reunion';
    section.style.display = show ? 'block' : 'none';
    if (show && !_quillRapport) {
        _quillRapport = new Quill('#quill-rapport', {
            theme: 'snow',
            placeholder: 'Saisissez le rapport de réunion...',
            modules: {
                toolbar: [
                    [{ header: [1, 2, 3, false] }],
                    ['bold', 'italic', 'underline', 'strike'],
                    [{ list: 'ordered' }, { list: 'bullet' }],
                    ['link'],
                    ['clean']
                ]
            }
        });
    }
}

async function addTache() {
    const assigneeVal = document.getElementById('tache-assignee')?.value;
    const body = {
        titre:             document.getElementById('tache-titre').value,
        projet_id:         document.getElementById('tache-projet').value || null,
        statut:            document.getElementById('tache-statut').value,
        priorite:          document.getElementById('tache-priorite').value || null,
        date_debut:        document.getElementById('tache-debut')?.value || null,
        date_echeance:     document.getElementById('tache-echeance').value || null,
        estimation_heures: document.getElementById('tache-heures').value || null,
        assignee_id:       assigneeVal ? parseInt(assigneeVal) : null,
        avancement:        0,
        type_tache:        document.getElementById('tache-type')?.value || 'autre',
    };
    if (!body.titre) { showMsg('Le titre est obligatoire', false); return; }
    try {
        const res = await apiFetch('/tache', { method: 'POST', body: JSON.stringify(body) });
        if (res.success) { showMsg('Tâche ajoutée'); loadTaches(); }
        else showMsg(res.error || 'Erreur', false);
    } catch (e) { showMsg(e.message, false); }
}

async function deleteTache(id) {
    if (!confirm('Supprimer cette tâche ?')) return;
    try {
        const res = await apiFetch(`/tache/${id}`, { method: 'DELETE' });
        if (res.success) { showMsg('Tâche supprimée'); loadTaches(); }
        else showMsg(res.error || 'Erreur', false);
    } catch (e) { showMsg(e.message, false); }
}

async function editTache(id) {
    let data = _cache.taches.find(t => t.id === id);
    if (!data) {
        try { data = await apiFetch(`/tache/${id}`); }
        catch (e) { showMsg('Tâche introuvable', false); return; }
    }
    if (!data) { showMsg('Tâche introuvable', false); return; }
    document.getElementById('edit-tache-id').value         = data.id;
    document.getElementById('edit-tache-titre').value      = data.titre || '';
    document.getElementById('edit-tache-projet').value     = data.projet_id || '';
    document.getElementById('edit-tache-statut').value     = data.statut || 'A faire';
    document.getElementById('edit-tache-priorite').value   = data.priorite || '';
    const deb = _toISODate(data.date_debut);
    const ech = _toISODate(data.date_echeance);
    const debutEl = document.getElementById('edit-tache-debut');
    if (debutEl) debutEl.value = deb;
    document.getElementById('edit-tache-echeance').value   = ech;
    document.getElementById('edit-tache-heures').value     = data.estimation_heures ?? '';
    document.getElementById('edit-tache-avancement').value = data.avancement ?? '';
    // Populate assignee select
    const assigneeSel = document.getElementById('edit-tache-assignee');
    if (assigneeSel) {
        await _populateMembresSelect(assigneeSel, data.assignee_id);
    }
    // Type de tâche
    const typeSel = document.getElementById('edit-tache-type');
    if (typeSel) typeSel.value = data.type_tache || 'autre';
    toggleRapportEditor();
    // Rapport de réunion (Quill)
    if (_quillRapport) {
        _quillRapport.root.innerHTML = data.rapport_reunion || '';
    } else if ((data.type_tache || 'autre') === 'reunion') {
        // Quill sera initialisé par toggleRapportEditor — on définit le contenu après
        setTimeout(() => { if (_quillRapport) _quillRapport.root.innerHTML = data.rapport_reunion || ''; }, 50);
    }
    openModal('modal-edit-tache');
}

async function saveTache() {
    const id = document.getElementById('edit-tache-id').value;
    const assigneeVal = document.getElementById('edit-tache-assignee')?.value;
    const typeTache = document.getElementById('edit-tache-type')?.value || 'autre';
    const rapportHtml = (_quillRapport && typeTache === 'reunion')
        ? _quillRapport.root.innerHTML
        : null;
    const body = {
        titre:             document.getElementById('edit-tache-titre').value,
        projet_id:         document.getElementById('edit-tache-projet').value || null,
        statut:            document.getElementById('edit-tache-statut').value,
        priorite:          document.getElementById('edit-tache-priorite').value || null,
        date_debut:        document.getElementById('edit-tache-debut')?.value || null,
        date_echeance:     document.getElementById('edit-tache-echeance').value || null,
        estimation_heures: document.getElementById('edit-tache-heures').value || null,
        avancement:        document.getElementById('edit-tache-avancement').value || 0,
        assignee_id:       assigneeVal ? parseInt(assigneeVal) : null,
        type_tache:        typeTache,
        rapport_reunion:   rapportHtml,
    };
    if (!body.titre) { showMsg('Le titre est obligatoire', false); return; }
    try {
        const res = await apiFetch(`/tache/${id}`, { method: 'PUT', body: JSON.stringify(body) });
        if (res.success) { showMsg('Tâche mise à jour'); closeModal('modal-edit-tache'); loadTaches(); }
        else showMsg(res.error || 'Erreur', false);
    } catch (e) { showMsg(e.message, false); }
}

// ─── KANBAN ────────────────────────────────────────────────

async function loadKanban() {
    const projetId = document.getElementById('kanban-filter-projet')?.value;
    const userId   = document.getElementById('kanban-filter-user')?.value;
    let params = '';
    if (projetId) params += `?projet_id=${projetId}`;
    if (userId)   params += (params ? '&' : '?') + `user_id=${userId}`;

    // Peupler le filtre user si vide
    const userSel = document.getElementById('kanban-filter-user');
    if (userSel && userSel.options.length <= 1) {
        await _populateMembresSelect(userSel, userId ? parseInt(userId) : null);
        // Réinsérer "Toutes les personnes" en premier
        const blankOpt = document.createElement('option');
        blankOpt.value = ''; blankOpt.textContent = 'Toutes les personnes';
        userSel.insertBefore(blankOpt, userSel.firstChild);
        if (userId) userSel.value = userId;
    }

    try {
        const data = await apiFetch('/kanban' + params);
        const board = document.getElementById('kanban-board');
        const columns = data.columns || {};
        const colorMap = {
            'A faire':    '#95a5a6',
            'En cours':   '#f39c12',
            'En attente': '#9b59b6',
            'Bloqué':     '#e74c3c',
            'Terminé':    '#27ae60',
        };
        board.innerHTML = Object.entries(columns).map(([col, cards]) => {
            const color = colorMap[col] || '#2563a8';
            return `<div style="flex:1;min-width:200px;max-width:270px;background:#fff;border-radius:8px;
                                box-shadow:0 1px 4px rgba(0,0,0,.08);">
                <div style="background:${color};color:#fff;padding:9px 12px;border-radius:8px 8px 0 0;
                            font-size:.9em;font-weight:bold;">
                    ${col} <span style="opacity:.8;font-weight:normal;">(${cards.length})</span>
                </div>
                <div style="padding:10px;min-height:60px;">
                ${cards.map(t => `
                    <div style="background:#f8f9fb;border-radius:6px;padding:8px 10px;
                                margin-bottom:8px;font-size:.82em;border-left:3px solid ${color};">
                        <strong>${t.titre || '-'}</strong>
                        ${t.projet_nom ? `<div style="color:#888;font-size:.9em;">${t.projet_nom}</div>` : ''}
                        ${t.assignee_nom ? `<div style="color:#2563a8;font-size:.85em;margin-top:2px;">👤 ${t.assignee_nom}</div>` : ''}
                        ${t.date_echeance ? `<div style="color:#666;margin-top:2px;">Éch: ${fmtDate(t.date_echeance)}</div>` : ''}
                        ${t.priorite ? `<div style="margin-top:3px;">${badge(t.priorite)}</div>` : ''}
                    </div>`).join('')}
                </div>
            </div>`;
        }).join('');
    } catch (e) { showMsg('Erreur chargement kanban', false); }
}

// ─── FOURNISSEURS ──────────────────────────────────────────

async function loadFournisseurs() {
    try {
        const data = await apiFetch('/fournisseur');
        _cache.fournisseurs = data.list || [];
        const tbody = document.getElementById('fournisseurs-tbody');
        tbody.innerHTML = _cache.fournisseurs.map(f => `
            <tr>
                <td>${f.id}</td>
                <td><strong>${f.nom || '-'}</strong></td>
                <td>${f.contact_principal || '-'}</td>
                <td style="font-size:.82em;color:#444;">${f.contacts_lies || '-'}</td>
                <td>${f.email || '-'}</td>
                <td>${f.telephone || '-'}</td>
                <td>${f.ville || '-'}</td>
                <td>${f.nb_contrats || 0}</td>
                <td>${f.nb_bc || 0}</td>
                <td>${fmt(f.montant_total)}</td>
                <td>${badge(f.statut || 'ACTIF')}</td>
                <td style="white-space:nowrap;">
                    <button class="btn btn-warning btn-sm" onclick="editFournisseur(${f.id})">Éditer</button>
                    <button class="btn btn-danger btn-sm" onclick="deleteFournisseur(${f.id})">Suppr.</button>
                </td>
            </tr>`).join('');
    } catch (e) { showMsg('Erreur chargement fournisseurs', false); }
}

async function addFournisseur() {
    const body = {
        nom:               document.getElementById('fournisseur-nom').value,
        contact_principal: document.getElementById('fournisseur-contact').value,
        email:             document.getElementById('fournisseur-email').value,
        telephone:         document.getElementById('fournisseur-telephone').value,
        adresse:           document.getElementById('fournisseur-adresse').value,
        ville:             document.getElementById('fournisseur-ville').value,
    };
    if (!body.nom) { showMsg('Le nom est obligatoire', false); return; }
    try {
        const res = await apiFetch('/fournisseur', { method: 'POST', body: JSON.stringify(body) });
        if (res.success) { showMsg('Fournisseur ajouté'); loadFournisseurs(); initRefs(); }
        else showMsg(res.error || 'Erreur', false);
    } catch (e) { showMsg(e.message, false); }
}

async function deleteFournisseur(id) {
    if (!confirm('Supprimer ce fournisseur ?')) return;
    try {
        const res = await apiFetch(`/fournisseur/${id}`, { method: 'DELETE' });
        if (res.success) { showMsg('Fournisseur supprimé'); loadFournisseurs(); initRefs(); }
        else showMsg(res.error || 'Erreur', false);
    } catch (e) { showMsg(e.message, false); }
}

async function editFournisseur(id) {
    const data = _cache.fournisseurs.find(f => f.id === id);
    if (!data) { showMsg('Données non chargées, rechargez', false); return; }
    document.getElementById('edit-fournisseur-id').value       = data.id;
    document.getElementById('edit-fournisseur-nom').value      = data.nom || '';
    document.getElementById('edit-fournisseur-contact').value  = data.contact_principal || '';
    document.getElementById('edit-fournisseur-email').value    = data.email || '';
    document.getElementById('edit-fournisseur-telephone').value= data.telephone || '';
    document.getElementById('edit-fournisseur-adresse').value  = data.adresse || '';
    document.getElementById('edit-fournisseur-ville').value    = data.ville || '';

    // Charger les contacts existants dans le select
    const sel = document.getElementById('fournisseur-contact-select');
    sel.innerHTML = '<option value="">— Sélectionner un contact existant —</option>';
    try {
        const cd = await apiFetch('/contact');
        (cd.list || []).forEach(c => {
            const label = [c.nom, c.prenom, c.societe || c.organisation].filter(Boolean).join(' – ');
            sel.innerHTML += `<option value="${c.id}">${label}</option>`;
        });
    } catch(e) {}

    await loadFournisseurContacts(id);
    openModal('modal-edit-fournisseur');
}

async function loadFournisseurContacts(fournisseurId) {
    const container = document.getElementById('fournisseur-contacts-list');
    try {
        const data = await apiFetch(`/fournisseur/${fournisseurId}/contacts`);
        const list = data.list || [];
        if (!list.length) {
            container.innerHTML = '<p style="color:#aaa;font-size:.82em;font-style:italic;">Aucun contact lié.</p>';
            return;
        }
        container.innerHTML = list.map(c => `
            <div style="display:flex;align-items:center;gap:8px;padding:4px 0;border-bottom:1px solid #f0f0f0;">
                <span style="flex:1;font-size:.85em;">
                    <strong>${c.nom || ''}${c.prenom ? ' ' + c.prenom : ''}</strong>
                    ${c.fonction ? `<span style="color:#666;"> · ${c.fonction}</span>` : ''}
                    ${c.societe || c.email ? `<span style="color:#888;font-size:.9em;"> — ${c.societe || c.email}</span>` : ''}
                </span>
                <button class="btn btn-danger btn-sm" onclick="unlinkContactFournisseur(${fournisseurId},${c.id})">✕</button>
            </div>`).join('');
    } catch(e) {
        container.innerHTML = '<p style="color:#c00;font-size:.82em;">Erreur chargement contacts.</p>';
    }
}

async function linkContactFournisseur() {
    const fournisseurId = document.getElementById('edit-fournisseur-id').value;
    const contactId = document.getElementById('fournisseur-contact-select').value;
    if (!contactId) { showMsg('Sélectionnez un contact', false); return; }
    try {
        const res = await apiFetch(`/fournisseur/${fournisseurId}/contacts`, {
            method: 'POST', body: JSON.stringify({ contact_id: parseInt(contactId) })
        });
        if (res.success) {
            document.getElementById('fournisseur-contact-select').value = '';
            await loadFournisseurContacts(parseInt(fournisseurId));
        } else showMsg(res.error || 'Erreur', false);
    } catch(e) { showMsg(e.message, false); }
}

async function unlinkContactFournisseur(fournisseurId, contactId) {
    try {
        const res = await apiFetch(`/fournisseur/${fournisseurId}/contacts/${contactId}`, { method: 'DELETE' });
        if (res.success) await loadFournisseurContacts(fournisseurId);
        else showMsg(res.error || 'Erreur', false);
    } catch(e) { showMsg(e.message, false); }
}

async function saveFournisseur() {
    const id = document.getElementById('edit-fournisseur-id').value;
    const body = {
        nom:               document.getElementById('edit-fournisseur-nom').value,
        contact_principal: document.getElementById('edit-fournisseur-contact').value,
        email:             document.getElementById('edit-fournisseur-email').value,
        telephone:         document.getElementById('edit-fournisseur-telephone').value,
        adresse:           document.getElementById('edit-fournisseur-adresse').value,
        ville:             document.getElementById('edit-fournisseur-ville').value,
    };
    if (!body.nom) { showMsg('Le nom est obligatoire', false); return; }
    try {
        const res = await apiFetch(`/fournisseur/${id}`, { method: 'PUT', body: JSON.stringify(body) });
        if (res.success) { showMsg('Fournisseur mis à jour'); closeModal('modal-edit-fournisseur'); loadFournisseurs(); initRefs(); }
        else showMsg(res.error || 'Erreur', false);
    } catch (e) { showMsg(e.message, false); }
}

// ─── CONTACTS ──────────────────────────────────────────────

async function _fillContactServiceSelects() {
    try {
        const data = await apiFetch('/service_org');
        const services = data.list || [];
        ['contact-service', 'edit-contact-service'].forEach(selId => {
            const sel = document.getElementById(selId);
            if (!sel) return;
            // Garder la valeur courante
            const cur = sel.value;
            // Réinitialiser avec les options fixes
            sel.innerHTML = '<option value="">— Aucun —</option><option value="INTERNE">Interne</option>';
            services.forEach(s => {
                const opt = document.createElement('option');
                opt.value = s.id;
                opt.textContent = s.nom + (s.code ? ` (${s.code})` : '');
                sel.appendChild(opt);
            });
            sel.value = cur;
        });
    } catch (e) { /* silencieux */ }
}

async function loadContacts() {
    const params = new URLSearchParams();
    const type   = document.getElementById('contact-filter-type')?.value;
    const search = document.getElementById('contact-search')?.value;
    if (type)   params.set('type', type);
    if (search) params.set('search', search);
    try {
        const [data] = await Promise.all([
            apiFetch('/contact?' + params),
            _fillContactServiceSelects()
        ]);
        _cache.contacts = data.list || [];
        const tbody = document.getElementById('contacts-tbody');
        tbody.innerHTML = _cache.contacts.map(c => `
            <tr>
                <td>${c.id}</td>
                <td>${c.nom || '-'}</td>
                <td>${c.prenom || '-'}</td>
                <td>${c.fonction || '-'}</td>
                <td>${badge(c.type)}</td>
                <td>${c.service_nom || '-'}</td>
                <td>${c.telephone || '-'}</td>
                <td>${c.email || '-'}</td>
                <td>${c.organisation || '-'}</td>
                <td>${c.societe || '-'}</td>
                <td style="white-space:nowrap;">
                    <button class="btn btn-warning btn-sm" onclick="editContact(${c.id})">Éditer</button>
                    <button class="btn btn-danger btn-sm" onclick="deleteContact(${c.id})">Suppr.</button>
                </td>
            </tr>`).join('');
    } catch (e) { showMsg('Erreur chargement contacts', false); }
}

async function addContact() {
    const svcRaw = document.getElementById('contact-service')?.value || '';
    const body = {
        nom:          document.getElementById('contact-nom').value,
        prenom:       document.getElementById('contact-prenom').value,
        fonction:     document.getElementById('contact-fonction').value,
        type:         document.getElementById('contact-type').value,
        service_id:   (svcRaw && svcRaw !== 'INTERNE') ? parseInt(svcRaw) : null,
        organisation: svcRaw === 'INTERNE' ? 'Interne' : document.getElementById('contact-organisation').value,
        telephone:    document.getElementById('contact-telephone').value,
        email:        document.getElementById('contact-email').value,
        societe:      document.getElementById('contact-societe').value,
    };
    if (!body.nom) { showMsg('Le nom est obligatoire', false); return; }
    try {
        const res = await apiFetch('/contact', { method: 'POST', body: JSON.stringify(body) });
        if (res.success) {
            showMsg('Contact ajouté');
            ['contact-nom','contact-prenom','contact-fonction','contact-telephone',
             'contact-email','contact-organisation','contact-societe'].forEach(id => {
                const el = document.getElementById(id);
                if (el) el.value = '';
            });
            document.getElementById('contact-type').value = '';
            const svcSel = document.getElementById('contact-service');
            if (svcSel) svcSel.value = '';
            loadContacts();
        } else showMsg(res.error || 'Erreur', false);
    } catch (e) { showMsg(e.message, false); }
}

async function deleteContact(id) {
    if (!confirm('Supprimer ce contact ?')) return;
    try {
        const res = await apiFetch(`/contact/${id}`, { method: 'DELETE' });
        if (res.success) { showMsg('Contact supprimé'); loadContacts(); }
        else showMsg(res.error || 'Erreur', false);
    } catch (e) { showMsg(e.message, false); }
}

function editContact(id) {
    const data = _cache.contacts.find(c => c.id === id);
    if (!data) { showMsg('Données non chargées, rechargez', false); return; }
    document.getElementById('edit-contact-id').value           = data.id;
    document.getElementById('edit-contact-nom').value          = data.nom || '';
    document.getElementById('edit-contact-prenom').value       = data.prenom || '';
    document.getElementById('edit-contact-fonction').value     = data.fonction || '';
    document.getElementById('edit-contact-type').value         = data.type || '';
    document.getElementById('edit-contact-telephone').value    = data.telephone || '';
    document.getElementById('edit-contact-email').value        = data.email || '';
    document.getElementById('edit-contact-organisation').value = data.organisation || '';
    document.getElementById('edit-contact-societe').value      = data.societe || '';
    // Service : service_id numérique ou 'INTERNE' si organisation = 'Interne' sans service_id
    const svcSel = document.getElementById('edit-contact-service');
    if (svcSel) {
        if (data.service_id) svcSel.value = String(data.service_id);
        else if ((data.organisation || '').toLowerCase() === 'interne') svcSel.value = 'INTERNE';
        else svcSel.value = '';
    }
    openModal('modal-edit-contact');
}

async function saveContact() {
    const id = document.getElementById('edit-contact-id').value;
    const svcRaw = document.getElementById('edit-contact-service')?.value || '';
    const body = {
        nom:          document.getElementById('edit-contact-nom').value,
        prenom:       document.getElementById('edit-contact-prenom').value,
        fonction:     document.getElementById('edit-contact-fonction').value,
        type:         document.getElementById('edit-contact-type').value || null,
        service_id:   (svcRaw && svcRaw !== 'INTERNE') ? parseInt(svcRaw) : null,
        organisation: svcRaw === 'INTERNE' ? 'Interne' : document.getElementById('edit-contact-organisation').value,
        telephone:    document.getElementById('edit-contact-telephone').value,
        email:        document.getElementById('edit-contact-email').value,
        societe:      document.getElementById('edit-contact-societe').value,
    };
    if (!body.nom) { showMsg('Le nom est obligatoire', false); return; }
    try {
        const res = await apiFetch(`/contact/${id}`, { method: 'PUT', body: JSON.stringify(body) });
        if (res.success) { showMsg('Contact mis à jour'); closeModal('modal-edit-contact'); loadContacts(); }
        else showMsg(res.error || 'Erreur', false);
    } catch (e) { showMsg(e.message, false); }
}

// ─── SERVICES / ORGANISATION ───────────────────────────────

// ─── Services : cache + tri + recherche ────────────────────────
let _servicesRows   = [];   // toutes les lignes enrichies
let _servicesSortCol = '';
let _servicesSortAsc = true;

async function loadServices() {
    try {
        const data = await apiFetch('/service_org');
        const services = data.list || [];

        // Arbre 3 niveaux : Direction → Service → Unité
        const rows = [];
        function _buildTree(parentId, depth) {
            services
                .filter(s => (s.parent_id || null) === parentId)
                .sort((a, b) => (a.nom || '').localeCompare(b.nom || '', 'fr'))
                .forEach(s => {
                    rows.push({ ...s, _isUnite: !!s.is_unite, _isDir: !!s.is_direction, _depth: depth });
                    _buildTree(s.id, depth + 1);
                });
        }
        _buildTree(null, 0);
        // Orphelins non vus (sécurité)
        const seen = new Set(rows.map(s => s.id));
        services.filter(s => !seen.has(s.id)).forEach(s =>
            rows.push({ ...s, _isUnite: !!s.is_unite, _isDir: !!s.is_direction, _depth: 0 })
        );

        _servicesRows = rows;
        _servicesSortCol = '';
        _servicesSortAsc = true;
        renderServicesTable();

        // Select service parent (formulaire ajout) — affichage hiérarchique
        const parentSel = document.getElementById('service-parent');
        if (parentSel) {
            parentSel.innerHTML = '<option value="">-- Parent (optionnel) --</option>' +
                rows.map(s => {
                    const prefix = '&nbsp;&nbsp;'.repeat(s._depth);
                    const typeLabel = s._isDir ? '[Dir]' : s._isUnite ? '[Unité]' : '[Svc]';
                    return `<option value="${s.id}">${prefix}${typeLabel} ${s.code ? s.code + ' – ' : ''}${s.nom}</option>`;
                }).join('');
        }

        // Contacts pour responsable (non-bloquant)
        apiFetch('/contact?limit=500').then(contactsData => {
            const contacts = contactsData.list || [];
            const respSel = document.getElementById('service-responsable');
            if (respSel) {
                respSel.innerHTML = '<option value="">-- Responsable (optionnel) --</option>' +
                    contacts.map(c => `<option value="${c.id}">${(c.prenom || '')} ${(c.nom || '')}${c.organisation ? ' — ' + c.organisation : ''}</option>`).join('');
            }
        }).catch(() => {});

    } catch (e) {
        console.error('loadServices error:', e);
        showMsg('Erreur chargement services: ' + e.message, false);
    }
}

function _serviceRowHtml(s, hasChildren) {
    let badge, rowStyle = '';
    if (s._isDir) {
        badge = '<span style="background:#7b2d8b;color:#fff;padding:2px 7px;border-radius:10px;font-size:.75em;">Direction</span>';
        rowStyle = 'background:#faf5ff;font-weight:bold;';
    } else if (s._isUnite) {
        badge = '<span style="background:#27ae60;color:#fff;padding:2px 7px;border-radius:10px;font-size:.75em;">Unité</span>';
    } else {
        badge = '<span style="background:#2563a8;color:#fff;padding:2px 7px;border-radius:10px;font-size:.75em;">Service</span>';
    }
    const depth = s._depth || 0;
    const padLeft = depth * 22; // px indent
    const toggleBtn = hasChildren
        ? `<span class="svc-toggle" data-open="0" data-id="${s.id}" onclick="toggleServiceBranch(${s.id})" title="Développer / Réduire"
              style="cursor:pointer;display:inline-flex;align-items:center;justify-content:center;width:20px;height:20px;border-radius:50%;background:#e0d4f0;color:#7b2d8b;font-size:.8em;margin-right:5px;user-select:none;">▶</span>`
        : `<span style="display:inline-block;width:20px;margin-right:5px;"></span>`;
    const nbP = s.nb_personnes != null ? s.nb_personnes : '-';
    const nbM = s.nb_membres || 0;
    return `<tr data-svc-id="${s.id}" data-svc-parent="${s.parent_id || ''}" data-svc-depth="${depth}" style="${rowStyle}">
        <td>${badge}</td>
        <td><strong>${s.code || '-'}</strong></td>
        <td style="padding-left:${padLeft}px;">${toggleBtn}${_h(s.nom || '-')}</td>
        <td>${_h(s.responsable_nom || '-')}</td>
        <td style="text-align:center;">${nbP}</td>
        <td style="text-align:center;">${nbM > 0 ? `<span style="color:#2563a8;font-weight:bold;">${nbM}</span>` : '-'}</td>
        <td style="white-space:nowrap;">
            <button onclick="editService(${s.id})"
                style="padding:3px 8px;font-size:.8em;background:#f39c12;color:#fff;border:none;border-radius:4px;cursor:pointer;margin-right:4px;">Éditer</button>
            <button class="btn btn-danger btn-sm" onclick="deleteService(${s.id})"
                style="padding:3px 8px;font-size:.8em;">Suppr.</button>
        </td>
    </tr>`;
}

function toggleServiceBranch(id) {
    const btn = document.querySelector(`#services-tbody .svc-toggle[data-id="${id}"]`);
    if (!btn) return;
    const isOpen = btn.dataset.open === '1';
    // Fermer : cacher récursivement tous les descendants
    function _hideDescendants(parentId) {
        document.querySelectorAll(`#services-tbody tr[data-svc-parent="${parentId}"]`).forEach(tr => {
            tr.style.display = 'none';
            const childId = tr.dataset.svcId;
            const childBtn = tr.querySelector('.svc-toggle');
            if (childBtn) { childBtn.dataset.open = '0'; childBtn.textContent = '▶'; }
            _hideDescendants(childId);
        });
    }
    // Ouvrir : afficher uniquement les enfants directs
    function _showChildren(parentId) {
        document.querySelectorAll(`#services-tbody tr[data-svc-parent="${parentId}"]`).forEach(tr => {
            tr.style.display = '';
        });
    }
    if (isOpen) {
        _hideDescendants(id);
        btn.dataset.open = '0';
        btn.textContent = '▶';
    } else {
        _showChildren(id);
        btn.dataset.open = '1';
        btn.textContent = '▼';
    }
}

function renderServicesTable() {
    const q = (document.getElementById('service-search')?.value || '').toLowerCase().trim();
    let rows = _servicesRows;

    // Filtre recherche
    if (q) {
        rows = rows.filter(s =>
            (s.code || '').toLowerCase().includes(q) ||
            (s.nom  || '').toLowerCase().includes(q) ||
            (s.responsable_nom || '').toLowerCase().includes(q)
        );
    }

    // Tri colonne (désactive la vue arbre)
    if (_servicesSortCol) {
        const col = _servicesSortCol;
        rows = [...rows].sort((a, b) => {
            let va = col === 'type'
                ? (a._isDir ? 'Direction' : a._isUnite ? 'Unité' : 'Service')
                : (a[col] || '');
            let vb = col === 'type'
                ? (b._isDir ? 'Direction' : b._isUnite ? 'Unité' : 'Service')
                : (b[col] || '');
            va = String(va).toLowerCase(); vb = String(vb).toLowerCase();
            return _servicesSortAsc ? va.localeCompare(vb, 'fr') : vb.localeCompare(va, 'fr');
        });
    }

    // Calculer quels IDs ont des enfants
    const childParents = new Set(rows.map(s => s.parent_id).filter(Boolean));

    document.getElementById('services-tbody').innerHTML = rows.map(s =>
        _serviceRowHtml(s, childParents.has(s.id))
    ).join('') || '<tr><td colspan="7" style="text-align:center;color:#aaa;padding:16px;">Aucun résultat</td></tr>';

    // Vue arbre : par défaut, masquer les noeuds enfants (depth > 0) si pas de recherche active
    if (!q && !_servicesSortCol) {
        document.querySelectorAll('#services-tbody tr[data-svc-depth]').forEach(tr => {
            if (parseInt(tr.dataset.svcDepth) > 0) tr.style.display = 'none';
        });
    }

    // Indicateurs de tri
    ['type','code','nom','responsable_nom'].forEach(c => {
        const el = document.getElementById(`sort-services-${c}`);
        if (el) el.textContent = _servicesSortCol === c ? (_servicesSortAsc ? ' ▲' : ' ▼') : ' ↕';
    });
}

function filterServices() { renderServicesTable(); }

function sortServices(col) {
    if (_servicesSortCol === col) {
        _servicesSortAsc = !_servicesSortAsc;
    } else {
        _servicesSortCol = col;
        _servicesSortAsc = true;
    }
    renderServicesTable();
}

async function addService() {
    const parentVal = document.getElementById('service-parent')?.value;
    const respVal   = document.getElementById('service-responsable')?.value;
    const nbP       = document.getElementById('service-nb-personnes')?.value;
    const svcType = document.getElementById('service-type')?.value || 'service';
    const body = {
        code:           document.getElementById('service-code').value.trim(),
        nom:            document.getElementById('service-nom').value.trim(),
        parent_id:      parentVal ? parseInt(parentVal) : null,
        responsable_id: respVal   ? parseInt(respVal)   : null,
        nb_personnes:   nbP       ? parseInt(nbP)        : null,
        is_direction:   svcType === 'direction',
        is_unite:       svcType === 'unite',
    };
    if (!body.nom) { showMsg('Le nom est obligatoire', false); return; }
    try {
        const res = await apiFetch('/service_org', { method: 'POST', body: JSON.stringify(body) });
        if (res.success) {
            showMsg('Service ajouté');
            document.getElementById('service-code').value = '';
            document.getElementById('service-nom').value  = '';
            if (document.getElementById('service-parent'))      document.getElementById('service-parent').value = '';
            if (document.getElementById('service-responsable'))  document.getElementById('service-responsable').value = '';
            if (document.getElementById('service-nb-personnes')) document.getElementById('service-nb-personnes').value = '';
            if (document.getElementById('service-is-unite')) document.getElementById('service-is-unite').checked = false;
            loadServices();
        } else showMsg(res.error || 'Erreur', false);
    } catch (e) { showMsg(e.message, false); }
}

async function deleteService(id) {
    if (!confirm('Supprimer ce service ?')) return;
    try {
        const res = await apiFetch(`/service_org/${id}`, { method: 'DELETE' });
        if (res.success) { showMsg('Service supprimé'); loadServices(); }
        else showMsg(res.error || 'Erreur', false);
    } catch (e) { showMsg(e.message, false); }
}

async function editService(id) {
    try {
        const [data, contactsData, membresData] = await Promise.all([
            apiFetch('/service_org'),
            apiFetch('/contact?limit=500'),
            apiFetch(`/service_org/${id}/membres`)
        ]);
        const services = data.list || [];
        const contacts = contactsData.list || [];
        const membres  = membresData.list || [];
        const s = services.find(x => x.id === id);
        if (!s) return;

        const typeVal = s.is_direction ? 'direction' : (s.is_unite ? 'unite' : 'service');
        const typeLabel = s.is_direction ? 'Direction' : (s.is_unite ? 'Unité' : 'Service');
        const titleEl = document.getElementById('edit-service-title');
        if (titleEl) titleEl.textContent = 'Modifier — ' + typeLabel;

        document.getElementById('edit-service-id').value            = id;
        document.getElementById('edit-service-code').value          = s.code || '';
        document.getElementById('edit-service-nom').value           = s.nom  || '';
        document.getElementById('edit-service-nb-personnes').value  = s.nb_personnes != null ? s.nb_personnes : '';
        document.getElementById('edit-service-membres').value       = s.membres_label || '';
        const typeSel = document.getElementById('edit-service-type');
        if (typeSel) typeSel.value = typeVal;

        // Construire select parent hiérarchique (exclure soi-même)
        const parentRows = [];
        function _buildEditTree(pid, depth) {
            services.filter(x => (x.parent_id || null) === pid && x.id !== id)
                .sort((a, b) => (a.nom || '').localeCompare(b.nom || '', 'fr'))
                .forEach(x => { parentRows.push({ ...x, _depth: depth }); _buildEditTree(x.id, depth + 1); });
        }
        _buildEditTree(null, 0);
        const parentSel = document.getElementById('edit-service-parent');
        parentSel.innerHTML = '<option value="">-- Aucun (racine) --</option>' +
            parentRows.map(x => {
                const prefix = '\u00a0\u00a0'.repeat(x._depth);
                const tl = x.is_direction ? '[Dir]' : x.is_unite ? '[Unité]' : '[Svc]';
                return `<option value="${x.id}" ${s.parent_id === x.id ? 'selected' : ''}>${prefix}${tl} ${x.code ? x.code + ' – ' : ''}${x.nom}</option>`;
            }).join('');

        const respSel = document.getElementById('edit-service-responsable');
        respSel.innerHTML = '<option value="">-- Aucun --</option>' +
            contacts.map(c =>
                `<option value="${c.id}" ${s.responsable_id === c.id ? 'selected' : ''}>${(c.prenom || '')} ${(c.nom || '')}${c.organisation ? ' — ' + c.organisation : ''}</option>`
            ).join('');

        // Afficher les membres avec compte système
        const memSysEl = document.getElementById('edit-service-membres-sys');
        if (memSysEl) {
            memSysEl.innerHTML = membres.length
                ? membres.map(u => `<span style="display:inline-block;background:#e8f4fd;border:1px solid #bee3f8;border-radius:4px;padding:2px 8px;margin:2px;font-size:.82em;">
                    ${u.prenom || ''} ${u.nom || ''} <span style="color:#888;font-size:.85em;">(${u.role || ''})</span>
                  </span>`).join('')
                : '<em style="color:#aaa;font-size:.85em;">Aucun utilisateur lié à ce service</em>';
        }

        openModal('modal-edit-service');
    } catch (e) { showMsg(e.message, false); }
}

async function saveEditService() {
    const id        = parseInt(document.getElementById('edit-service-id').value);
    const parentVal = document.getElementById('edit-service-parent').value;
    const respVal   = document.getElementById('edit-service-responsable').value;
    const nbP       = document.getElementById('edit-service-nb-personnes').value;
    const body = {
        code:           document.getElementById('edit-service-code').value.trim(),
        nom:            document.getElementById('edit-service-nom').value.trim(),
        parent_id:      parentVal ? parseInt(parentVal) : null,
        responsable_id: respVal   ? parseInt(respVal)   : null,
        nb_personnes:   nbP       ? parseInt(nbP)        : null,
        membres_label:  document.getElementById('edit-service-membres').value || null,
        is_direction:   document.getElementById('edit-service-type')?.value === 'direction',
        is_unite:       document.getElementById('edit-service-type')?.value === 'unite',
    };
    if (!body.nom) { showMsg('Le nom est obligatoire', false); return; }
    try {
        const res = await apiFetch(`/service_org/${id}`, { method: 'PUT', body: JSON.stringify(body) });
        if (res.success) {
            showMsg('Service mis à jour');
            closeModal('modal-edit-service');
            loadServices();
        } else showMsg(res.error || 'Erreur', false);
    } catch (e) { showMsg(e.message, false); }
}

// ─── GANTT ─────────────────────────────────────────────────

let _ganttInstance    = null;
let _ganttProjInstance = null;

function _periodDates(period) {
    const now = new Date();
    const y = now.getFullYear(), m = now.getMonth();
    switch (period) {
        case 'month':
            return { start: new Date(y, m, 1), end: new Date(y, m + 1, 0) };
        case 'quarter': {
            const q = Math.floor(m / 3);
            return { start: new Date(y, q * 3, 1), end: new Date(y, q * 3 + 3, 0) };
        }
        case 'semester': {
            const h = m < 6 ? 0 : 6;
            return { start: new Date(y, h, 1), end: new Date(y, h + 6, 0) };
        }
        case 'year':
            return { start: new Date(y, 0, 1), end: new Date(y, 11, 31) };
        default:
            return null;
    }
}

function _ganttColor(statut) {
    const map = {
        'ACTIF': '#2563a8', 'EN_ATTENTE': '#f39c12', 'TERMINE': '#27ae60',
        'ANNULE': '#999', 'En cours': '#2563a8', 'A faire': '#7f8c8d',
        'Terminée': '#27ae60', 'Bloquée': '#c0392b'
    };
    return map[statut] || '#2563a8';
}

async function loadGantt() {
    // Populate service filter on first load
    const serviceSel = document.getElementById('gantt-filter-service');
    if (serviceSel && serviceSel.options.length <= 1) {
        try {
            const sData = await apiFetch('/service_org');
            const services = sData.list || [];
            serviceSel.innerHTML = '<option value="">Tous les services</option>';
            function addServiceOpts(parentId, depth) {
                services
                    .filter(s => (s.parent_id || null) === parentId)
                    .sort((a, b) => (a.nom || '').localeCompare(b.nom || '', 'fr'))
                    .forEach(s => {
                        const opt = document.createElement('option');
                        opt.value = s.id;
                        const prefix = depth === 0 ? (s.code ? s.code + ' \u2014 ' : '') : '\u00a0'.repeat(depth * 2) + '└─ ';
                        opt.textContent = prefix + s.nom;
                        if (depth === 0) opt.style.fontWeight = 'bold';
                        serviceSel.appendChild(opt);
                        addServiceOpts(s.id, depth + 1);
                    });
            }
            addServiceOpts(null, 0);
        } catch(e) {}
    }

    const serviceId = serviceSel?.value;
    const period    = document.getElementById('gantt-filter-period')?.value || 'quarter';
    const mode      = document.getElementById('gantt-mode')?.value || 'projets';
    const viewMode  = document.getElementById('gantt-view-mode')?.value || 'Week';

    const params = new URLSearchParams();
    if (serviceId) params.set('service_id', serviceId);
    const dates = _periodDates(period);
    if (dates) {
        params.set('date_debut', dates.start.toISOString().slice(0, 10));
        params.set('date_fin',   dates.end.toISOString().slice(0, 10));
    }

    let data;
    try { data = await apiFetch('/gantt?' + params.toString()); }
    catch (e) { showMsg('Erreur chargement Gantt: ' + e.message, false); return; }

    const emptyEl = document.getElementById('gantt-empty');
    const wrapEl  = document.getElementById('gantt-wrap');
    const legendEl = document.getElementById('gantt-legend');

    const today = new Date().toISOString().slice(0, 10);

    let tasks = [];
    if (mode === 'projets') {
        tasks = (data.projets || [])
            .filter(p => p.date_debut || p.date_fin_prevue)
            .map(p => ({
                id:         String(p.id),
                name:       `${p.code ? p.code + ' - ' : ''}${p.nom}`,
                start:      p.date_debut      || today,
                end:        p.date_fin_prevue || today,
                progress:   p.avancement || 0,
                custom_class: 'bar-projet',
            }));
    } else {
        tasks = (data.taches || [])
            .filter(t => t.date_echeance)
            .map(t => ({
                id:       'T' + t.id,
                name:     `${t.projet_code || t.projet_nom || ''} › ${t.titre}`,
                start:    t.date_debut    || today,
                end:      t.date_echeance || today,
                progress: t.avancement   || 0,
                custom_class: 'bar-tache',
            }));
    }

    if (!tasks.length) {
        if (emptyEl) emptyEl.style.display = '';
        wrapEl.innerHTML = '<svg id="gantt-global"></svg>';
        if (legendEl) legendEl.innerHTML = '';
        _ganttInstance = null;
        return;
    }
    if (emptyEl) emptyEl.style.display = 'none';

    // Rebuild SVG container (Frappe Gantt targets existing SVG)
    wrapEl.innerHTML = '<svg id="gantt-global"></svg>';
    try {
        _ganttInstance = new Gantt('#gantt-global', tasks, {
            view_mode:    viewMode,
            date_format:  'YYYY-MM-DD',
            language:     'fr',
            bar_height:   24,
            padding:      18,
        });
    } catch (e) { showMsg('Erreur rendu Gantt: ' + e.message, false); }

    // Legend
    if (legendEl) {
        legendEl.innerHTML = mode === 'projets'
            ? '<div class="gantt-legend-item"><div class="gantt-legend-dot" style="background:#2563a8"></div>Projets</div>'
            : '<div class="gantt-legend-item"><div class="gantt-legend-dot" style="background:#27ae60"></div>Tâches</div>';
    }
}

function updateGanttViewMode() {
    if (!_ganttInstance) return;
    const vm = document.getElementById('gantt-view-mode')?.value || 'Week';
    try { _ganttInstance.change_view_mode(vm); } catch(e) {}
}

async function loadProjetGantt(projetId) {
    const viewMode = document.getElementById('gantt-proj-view-mode')?.value || 'Week';
    const emptyEl  = document.getElementById('gantt-proj-empty');
    const wrapEl   = document.querySelector('#ptab-gantt-proj .gantt-wrap');
    if (!wrapEl) return;

    let data;
    try { data = await apiFetch(`/gantt?projet_id=${projetId}`); }
    catch (e) { showMsg('Erreur Gantt projet: ' + e.message, false); return; }

    const today = new Date().toISOString().slice(0, 10);
    const tasks = (data.taches || [])
        .filter(t => t.date_echeance)
        .map(t => ({
            id:       'T' + t.id,
            name:     t.titre + (t.responsable_label ? ' (' + t.responsable_label + ')' : ''),
            start:    t.date_debut    || today,
            end:      t.date_echeance || today,
            progress: t.avancement   || 0,
        }));

    wrapEl.innerHTML = '<svg id="gantt-projet-svg"></svg>';
    if (!tasks.length) {
        if (emptyEl) emptyEl.style.display = '';
        _ganttProjInstance = null;
        return;
    }
    if (emptyEl) emptyEl.style.display = 'none';
    try {
        _ganttProjInstance = new Gantt('#gantt-projet-svg', tasks, {
            view_mode:   viewMode,
            date_format: 'YYYY-MM-DD',
            language:    'fr',
            bar_height:  24,
            padding:     16,
        });
    } catch (e) { showMsg('Erreur rendu Gantt projet: ' + e.message, false); }
}

function updateProjetGanttViewMode() {
    if (!_ganttProjInstance) return;
    const vm = document.getElementById('gantt-proj-view-mode')?.value || 'Week';
    try { _ganttProjInstance.change_view_mode(vm); } catch(e) {}
}

// ─── ETP ───────────────────────────────────────────────────

let _etpMode = 'projet';

function switchEtpMode(mode) {
    _etpMode = mode;
    document.getElementById('etp-tab-projet').style.background   = mode === 'projet'   ? '#2563a8' : '#e9ecef';
    document.getElementById('etp-tab-projet').style.color        = mode === 'projet'   ? '#fff'    : '#333';
    document.getElementById('etp-tab-personne').style.background = mode === 'personne' ? '#2563a8' : '#e9ecef';
    document.getElementById('etp-tab-personne').style.color      = mode === 'personne' ? '#fff'    : '#333';
    document.getElementById('etp-view-projet').style.display   = mode === 'projet'   ? '' : 'none';
    document.getElementById('etp-view-personne').style.display = mode === 'personne' ? '' : 'none';
    loadETP();
}

async function loadETP() {
    try {
        const data = await apiFetch(`/etp?mode=${_etpMode}`);
        const kpiEl = document.getElementById('etp-kpi-bar');

        if (_etpMode === 'personne') {
            const users = data.list || [];
            const totalH = users.reduce((s, u) => s + (u.heures_estimees || 0), 0);
            kpiEl.innerHTML =
                `<span>Personnes: <strong class="kpi-num">${users.length}</strong></span>` +
                `<span>Total heures assignées: <strong class="kpi-num">${Math.round(totalH)} h</strong></span>` +
                `<span>ETP chargé: <strong class="kpi-num">${Math.round(totalH / (data.heures_an || 1540) * 100) / 100}</strong></span>`;

            const tbody = document.getElementById('etp-personne-tbody');
            tbody.innerHTML = users.map(u => {
                const h = u.heures_estimees || 0;
                const hr = u.heures_reelles || 0;
                const pct = u.pct_charge || 0;
                const dispo = u.heures_dispo || (1540 - h);
                // Barre de charge colorée
                const barColor = pct >= 90 ? '#e74c3c' : pct >= 70 ? '#f39c12' : '#27ae60';
                const serviceBadge = u.is_unite
                    ? `<span style="background:#27ae60;color:#fff;padding:1px 6px;border-radius:8px;font-size:.75em;">Unité</span> `
                    : `<span style="background:#2563a8;color:#fff;padding:1px 6px;border-radius:8px;font-size:.75em;">Service</span> `;
                return `<tr>
                    <td><strong>${u.nom || '-'}</strong></td>
                    <td>${u.prenom || '-'}</td>
                    <td>${serviceBadge}${u.service_code ? '<strong>' + u.service_code + '</strong> – ' : ''}${u.service_nom || '<em style="color:#aaa">Aucun</em>'}</td>
                    <td style="text-align:center;">${u.nb_taches || 0}</td>
                    <td>${h} h</td>
                    <td>${hr} h</td>
                    <td>
                        <div style="display:flex;align-items:center;gap:6px;">
                            <div style="flex:1;background:#e9ecef;border-radius:4px;height:8px;min-width:60px;">
                                <div style="width:${Math.min(pct,100)}%;background:${barColor};height:8px;border-radius:4px;"></div>
                            </div>
                            <span style="font-weight:bold;color:${barColor};min-width:40px;">${pct}%</span>
                        </div>
                    </td>
                    <td style="color:${dispo < 0 ? '#e74c3c' : '#27ae60'};font-weight:bold;">${Math.round(dispo)} h</td>
                    <td>${u.etp_charge || 0}</td>
                </tr>`;
            }).join('') || '<tr><td colspan="9" style="text-align:center;color:#aaa;">Aucune donnée</td></tr>';

        } else {
            kpiEl.innerHTML =
                `<span>Total heures estimées: <strong class="kpi-num">${data.total_heures || 0} h</strong></span>` +
                `<span>Jours estimés: <strong class="kpi-num">${data.total_jours || 0} j</strong></span>` +
                `<span>ETP annuel: <strong class="kpi-num">${data.total_etp || 0}</strong></span>`;
            const tbody = document.getElementById('etp-tbody');
            tbody.innerHTML = (data.list || []).map(p => {
                const h = p.heures_estimees || 0;
                const hr = p.heures_reelles || 0;
                return `<tr>
                    <td>${p.code || '-'}</td>
                    <td><strong>${p.nom || '-'}</strong></td>
                    <td>${badge(p.statut)}</td>
                    <td>${p.nb_taches || 0}</td>
                    <td>${h} h</td>
                    <td>${hr} h</td>
                    <td>${Math.round(h / 7 * 10) / 10} j</td>
                    <td>${Math.round(h / 154 * 100) / 100} ETP</td>
                </tr>`;
            }).join('');
        }
    } catch (e) { showMsg('Erreur chargement ETP', false); }
}

// ─── NOTIFICATIONS ─────────────────────────────────────────

async function loadNotifications() {
    try {
        const data = await apiFetch('/notifications');
        const list = data.list || [];
        const badge = document.getElementById('notif-badge');
        if (data.non_lues > 0) {
            badge.textContent = data.non_lues;
            badge.style.display = 'inline';
        } else { badge.style.display = 'none'; }

        const el = document.getElementById('notif-list');
        if (!list.length) {
            el.innerHTML = '<p style="padding:20px;color:#888;">Aucune notification.</p>';
            return;
        }
        el.innerHTML = list.map(n => `
            <div style="background:#fff;border-radius:8px;padding:12px 16px;margin-bottom:8px;
                        box-shadow:0 1px 4px rgba(0,0,0,.06);
                        border-left:4px solid ${n.lue ? '#ccc' : '#2563a8'};
                        opacity:${n.lue ? .65 : 1};">
                <div style="font-weight:bold;font-size:.9em;">${n.titre || '-'}</div>
                <div style="font-size:.82em;color:#555;margin-top:3px;">${n.message || ''}</div>
                <div style="font-size:.75em;color:#999;margin-top:4px;">${fmtDate(n.date_creation)}</div>
                ${!n.lue ? `<button class="btn btn-sm btn-info" style="margin-top:6px;"
                    onclick="lireNotif(${n.id})">Marquer lue</button>` : ''}
            </div>`).join('');
    } catch (e) { /* notifications optionnelles */ }
}

async function lireNotif(id) {
    try {
        await apiFetch(`/notifications/${id}/lire`, { method: 'POST', body: '{}' });
        loadNotifications();
    } catch (e) { /* silencieux */ }
}

// ─── ADMIN UTILISATEURS ────────────────────────────────────

let _adminServicesCache = [];

async function loadAdminUsers() {
    try {
        const [usersData, servicesData] = await Promise.all([
            apiFetch('/users'),
            apiFetch('/service_org')
        ]);
        _adminServicesCache = servicesData.list || [];
        const tbody = document.getElementById('admin-users-tbody');
        const roleColor = { admin: '#c0392b', gestionnaire: '#2563a8', lecteur: '#27ae60' };
        tbody.innerHTML = (usersData.list || []).map(u => `
            <tr style="opacity:${u.actif ? 1 : 0.5}">
                <td>${u.nom || '-'}</td>
                <td>${u.prenom || '-'}</td>
                <td><strong>${u.login || '-'}</strong></td>
                <td>${u.email || '-'}</td>
                <td><span style="background:${roleColor[u.role]||'#888'};color:#fff;
                    padding:2px 8px;border-radius:10px;font-size:.82em;">${u.role}</span></td>
                <td>${u.service_id
                    ? (_adminServicesCache.find(s => s.id === u.service_id) || {}).nom || u.service_id
                    : '<em style="color:#aaa">Global</em>'}</td>
                <td style="text-align:center">${u.actif
                    ? '<span style="color:#27ae60">✓</span>'
                    : '<span style="color:#c0392b">✗</span>'}</td>
                <td style="white-space:nowrap;">
                    <button class="btn btn-warning btn-sm" onclick="editAdminUser(${u.id})"
                            style="padding:3px 8px;font-size:.8em;">Éditer</button>
                    <button class="btn btn-sm" onclick="toggleAdminUser(${u.id}, ${!u.actif})"
                            style="padding:3px 8px;font-size:.8em;background:${u.actif ? '#e67e22' : '#27ae60'};color:#fff;border:none;border-radius:4px;cursor:pointer;">
                        ${u.actif ? 'Désactiver' : 'Activer'}</button>
                    <button class="btn btn-danger btn-sm" onclick="deleteAdminUser(${u.id})"
                            style="padding:3px 8px;font-size:.8em;">Suppr.</button>
                </td>
            </tr>`).join('');
    } catch (e) { showMsg('Erreur chargement utilisateurs: ' + e.message, false); }
}

function switchAdminTab(tab) {
    ['users', 'audit', 'modules', 'smtp'].forEach(t => {
        const sub = document.getElementById('admin-sub-' + t);
        const btn = document.getElementById('admin-tab-' + t);
        if (sub) sub.classList.toggle('active', t === tab);
        if (btn) btn.classList.toggle('active', t === tab);
    });
    const addBtn = document.getElementById('admin-add-user-btn');
    if (addBtn) addBtn.style.display = tab === 'users' ? '' : 'none';
    if (tab === 'audit')   loadAuditLog();
    if (tab === 'modules') loadAdminModules();
    if (tab === 'smtp')    loadSmtpConfig();
}

async function loadAuditLog() {
    const table  = document.getElementById('audit-filter-table')?.value  || '';
    const action = document.getElementById('audit-filter-action')?.value || '';
    const params = new URLSearchParams();
    if (table)  params.set('table', table);
    if (action) params.set('action', action);
    params.set('limit', '200');
    try {
        const data = await apiFetch('/audit_log?' + params);
        const tbody = document.getElementById('audit-log-tbody');
        if (!tbody) return;
        if (!(data.list || []).length) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#999;padding:16px;font-style:italic;">Aucune entrée dans le journal.</td></tr>';
            return;
        }
        const actionColors = {
            'CREATE':   '#d4edda', 'UPDATE': '#fff3cd', 'DELETE': '#f8d7da',
            'VALIDER':  '#cce5ff', 'REFUSER': '#f8d7da', 'IMPUTER': '#d1ecf1',
            'VOTER':    '#e2d9f3', 'RECONDUIRE': '#d1ecf1',
        };
        tbody.innerHTML = data.list.map(e => {
            const color = actionColors[e.action] || '#f0f0f0';
            const details = e.details ? JSON.parse(e.details) : null;
            const detailStr = details ? Object.entries(details).map(([k,v]) => `${k}: ${v}`).join(', ') : '-';
            const nom = [e.prenom, e.nom].filter(Boolean).join(' ') || e.user_login || `#${e.user_id}`;
            return `<tr>
                <td style="font-size:.78em;white-space:nowrap;">${(e.date_creation||'').substring(0,19).replace('T',' ')}</td>
                <td style="font-size:.82em;">${nom}</td>
                <td><span class="badge" style="background:${color};color:#333;font-size:.75em;">${e.action}</span></td>
                <td style="font-size:.78em;color:#555;">${e.table_name || '-'}</td>
                <td style="text-align:center;font-size:.78em;">${e.record_id || '-'}</td>
                <td style="font-size:.78em;color:#555;max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${detailStr}">${detailStr}</td>
            </tr>`;
        }).join('');
    } catch (e) { showMsg('Erreur journal audit: ' + e.message, false); }
}

async function saveNewUser() {
    const serviceVal = document.getElementById('new-user-service').value;
    const data = {
        nom:          document.getElementById('new-user-nom').value,
        prenom:       document.getElementById('new-user-prenom').value,
        login:        document.getElementById('new-user-login').value.trim(),
        email:        document.getElementById('new-user-email').value,
        mot_de_passe: document.getElementById('new-user-password').value,
        role:         document.getElementById('new-user-role').value,
        service_id:   serviceVal ? parseInt(serviceVal) : null,
        actif:        true,
    };
    if (!data.login || !data.mot_de_passe) { showMsg('Login et mot de passe obligatoires', false); return; }
    try {
        await apiFetch('/users', { method: 'POST', body: JSON.stringify(data) });
        showMsg('Utilisateur créé');
        closeModal('modal-add-user');
        loadAdminUsers();
    } catch (e) { showMsg(e.message, false); }
}

async function editAdminUser(id) {
    try {
        const u = await apiFetch(`/users/${id}`);
        document.getElementById('edit-user-id').value    = u.id;
        document.getElementById('edit-user-nom').value   = u.nom || '';
        document.getElementById('edit-user-prenom').value= u.prenom || '';
        document.getElementById('edit-user-login').value = u.login || '';
        document.getElementById('edit-user-email').value = u.email || '';
        document.getElementById('edit-user-password').value = '';
        document.getElementById('edit-user-role').value  = u.role || 'lecteur';
        document.getElementById('edit-user-actif').checked = !!u.actif;
        // Peupler select service avec hiérarchie
        const sel = document.getElementById('edit-user-service');
        _buildServiceOptions(sel, u.service_id);
        openModal('modal-edit-user');
    } catch (e) { showMsg(e.message, false); }
}

async function saveEditUser() {
    const id = parseInt(document.getElementById('edit-user-id').value);
    const serviceVal = document.getElementById('edit-user-service').value;
    const data = {
        nom:          document.getElementById('edit-user-nom').value,
        prenom:       document.getElementById('edit-user-prenom').value,
        login:        document.getElementById('edit-user-login').value.trim(),
        email:        document.getElementById('edit-user-email').value,
        role:         document.getElementById('edit-user-role').value,
        service_id:   serviceVal ? parseInt(serviceVal) : null,
        actif:        document.getElementById('edit-user-actif').checked,
    };
    const pwd = document.getElementById('edit-user-password').value;
    if (pwd) data.mot_de_passe = pwd;
    try {
        await apiFetch(`/users/${id}`, { method: 'PUT', body: JSON.stringify(data) });
        showMsg('Utilisateur mis à jour');
        closeModal('modal-edit-user');
        loadAdminUsers();
    } catch (e) { showMsg(e.message, false); }
}

async function toggleAdminUser(id, actif) {
    try {
        await apiFetch(`/users/${id}/toggle`, { method: 'POST', body: JSON.stringify({ actif }) });
        showMsg(actif ? 'Compte activé' : 'Compte désactivé');
        loadAdminUsers();
    } catch (e) { showMsg(e.message, false); }
}

async function deleteAdminUser(id) {
    if (!confirm('Supprimer définitivement cet utilisateur ?')) return;
    try {
        await apiFetch(`/users/${id}`, { method: 'DELETE' });
        showMsg('Utilisateur supprimé');
        loadAdminUsers();
    } catch (e) { showMsg(e.message, false); }
}

function _buildServiceOptions(sel, selectedId) {
    const all      = _adminServicesCache;
    const byId     = Object.fromEntries(all.map(s => [s.id, s]));

    sel.innerHTML  = '';
    sel.appendChild(Object.assign(document.createElement('option'),
        { value: '', textContent: 'Aucun (accès global)' }));

    function _opt(s, prefix) {
        const o = document.createElement('option');
        o.value = s.id;
        const parentLabel = s.parent_id && byId[s.parent_id]
            ? ` (${byId[s.parent_id].code || byId[s.parent_id].nom})` : '';
        o.textContent = prefix + (s.code ? s.code + ' – ' : '') + s.nom + parentLabel;
        if (selectedId && s.id == selectedId) o.selected = true;
        return o;
    }

    // ── Section Services (récursif, tous niveaux) ─────────────
    const svcList = all.filter(s => !s.is_unite);
    if (svcList.length) {
        const grpSvc = document.createElement('optgroup');
        grpSvc.label = '── Services ──';
        function addSvcOpt(parentId, depth) {
            svcList.filter(s => (s.parent_id || null) === parentId)
                .sort((a, b) => (a.nom || '').localeCompare(b.nom || '', 'fr'))
                .forEach(s => {
                    grpSvc.appendChild(_opt(s, '  '.repeat(depth) + (depth ? '└─ ' : '')));
                    addSvcOpt(s.id, depth + 1);
                });
        }
        addSvcOpt(null, 0);
        sel.appendChild(grpSvc);
    }

    // ── Section Unités (récursif, tous niveaux) ────────────────
    const uniList = all.filter(s => s.is_unite);
    if (uniList.length) {
        const grpUni = document.createElement('optgroup');
        grpUni.label = '── Unités ──';
        function addUniOpt(parentId, depth) {
            uniList.filter(s => (s.parent_id || null) === parentId)
                .sort((a, b) => (a.nom || '').localeCompare(b.nom || '', 'fr'))
                .forEach(s => {
                    grpUni.appendChild(_opt(s, '  '.repeat(depth) + (depth ? '└─ ' : '')));
                    addUniOpt(s.id, depth + 1);
                });
        }
        addUniOpt(null, 0);
        // Unités dont le parent est un Service
        all.filter(s => !s.is_unite && uniList.some(u => u.parent_id === s.id)).forEach(p => {
            uniList.filter(u => u.parent_id === p.id)
                .forEach(u => grpUni.appendChild(_opt(u, '  └─ ')));
        });
        sel.appendChild(grpUni);
    }
}

function _populateNewUserServiceSelect() {
    const sel = document.getElementById('new-user-service');
    if (!sel) return;
    _buildServiceOptions(sel, null);
}


// ─── Cache utilisateurs actifs (pour selects tâches/kanban) ────────────────
let _usersActifsCache = [];

async function _loadUsersActifs(force = false) {
    if (_usersActifsCache.length && !force) return _usersActifsCache;
    try {
        const data = await apiFetch('/users/actifs');
        _usersActifsCache = data.list || [];
    } catch (e) { _usersActifsCache = []; }
    return _usersActifsCache;
}

/**
 * Peuple un <select> avec les utilisateurs actifs groupés par service/unité.
 * @param {HTMLSelectElement} sel
 * @param {number|null} selectedId  — id à pré-sélectionner
 */
async function _populateMembresSelect(sel, selectedId = null) {
    if (!sel) return;
    const users = await _loadUsersActifs();
    sel.innerHTML = '<option value="">-- Non assigné --</option>';

    // Grouper par service
    const byService = {};
    const noService = [];
    users.forEach(u => {
        const grpKey = u.service_id
            ? `${u.is_unite ? '[Unité] ' : ''}${u.service_code ? u.service_code + ' – ' : ''}${u.service_nom || 'Service ' + u.service_id}`
            : null;
        if (grpKey) {
            if (!byService[grpKey]) byService[grpKey] = [];
            byService[grpKey].push(u);
        } else {
            noService.push(u);
        }
    });

    Object.entries(byService).sort((a, b) => a[0].localeCompare(b[0], 'fr')).forEach(([grpLabel, members]) => {
        const grp = document.createElement('optgroup');
        grp.label = grpLabel;
        members.forEach(u => {
            const o = document.createElement('option');
            o.value = u.id;
            o.textContent = `${u.nom} ${u.prenom}`;
            if (selectedId && u.id == selectedId) o.selected = true;
            grp.appendChild(o);
        });
        sel.appendChild(grp);
    });
    noService.forEach(u => {
        const o = document.createElement('option');
        o.value = u.id;
        o.textContent = `${u.nom} ${u.prenom}`;
        if (selectedId && u.id == selectedId) o.selected = true;
        sel.appendChild(o);
    });
}

// ─── INIT ──────────────────────────────────────────────────

document.getElementById('header-date').textContent =
    new Date().toLocaleDateString('fr-FR', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

// ─── Helper : peupler un <select> avec les contacts filtrés par type ──────────
async function loadContactsForSelect(sel, type = '') {
    if (!sel) return;
    sel.innerHTML = '<option value="">-- Sélectionner un contact --</option>';
    const url = type ? `/contact?type=${encodeURIComponent(type)}` : '/contact?limit=500';
    try {
        const data = await apiFetch(url);
        (data.list || []).forEach(c => {
            const opt = document.createElement('option');
            opt.value = `${c.prenom || ''} ${c.nom || ''}`.trim();
            opt.textContent = `${c.prenom || ''} ${c.nom || ''}${c.organisation ? ' — ' + c.organisation : ''}`.trim();
            sel.appendChild(opt);
        });
    } catch(e) {}
}

async function loadContactsIdForSelect(sel, type = '', searchInput = null) {
    if (!sel) return;
    sel.innerHTML = '<option value="">-- Sélectionner un contact --</option>';
    if (searchInput) searchInput.value = '';
    const url = type ? `/contact?type=${encodeURIComponent(type)}` : '/contact?limit=500';
    try {
        const data = await apiFetch(url);
        (data.list || []).forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.id;
            opt.textContent = `${c.prenom || ''} ${c.nom || ''}${c.organisation ? ' — ' + c.organisation : ''}`.trim();
            sel.appendChild(opt);
        });
    } catch(e) {}
}

function filterContactSelect(searchInput, selId) {
    const q = searchInput.value.toLowerCase();
    const sel = document.getElementById(selId);
    if (!sel) return;
    Array.from(sel.options).forEach(opt => {
        if (!opt.value) return; // garder le placeholder
        opt.style.display = opt.textContent.toLowerCase().includes(q) ? '' : 'none';
    });
}

function showAddTacheProjet(projetId) {
    const form = document.getElementById(`add-tache-form-${projetId}`);
    if (!form) return;
    form.style.display = form.style.display === 'none' ? '' : 'none';
    if (form.style.display !== 'none') {
        const el = document.getElementById(`ntf-titre-${projetId}`);
        if (el) el.focus();
    }
}

async function saveNewTacheProjet(projetId) {
    const titre = document.getElementById(`ntf-titre-${projetId}`)?.value?.trim();
    if (!titre) { showMsg('Le titre est obligatoire', false); return; }
    const body = {
        titre,
        projet_id:         projetId,
        statut:            document.getElementById(`ntf-statut-${projetId}`)?.value || 'A faire',
        priorite:          document.getElementById(`ntf-priorite-${projetId}`)?.value || 'NORMALE',
        date_echeance:     document.getElementById(`ntf-echeance-${projetId}`)?.value || null,
        estimation_heures: document.getElementById(`ntf-heures-${projetId}`)?.value || null,
    };
    try {
        await apiFetch('/tache', { method: 'POST', body: JSON.stringify(body) });
        showMsg('Tâche créée', true);
        await ficheProjet(projetId);
        switchProjTab('taches');
    } catch(e) { showMsg(e.message, false); }
}

// ─── Équipe projet ───────────────────────────────────────────────────────────
async function showAddMembreForm(projetId) {
    const form = document.getElementById(`add-membre-form-${projetId}`);
    if (!form) return;
    form.style.display = form.style.display === 'none' ? '' : 'none';
    if (form.style.display === 'none') return;

    const contactSel = document.getElementById(`new-membre-select-${projetId}`);
    const serviceSel = document.getElementById(`new-service-select-${projetId}`);
    const labelInput = document.getElementById(`new-membre-label-${projetId}`);
    if (labelInput) labelInput.value = '';

    try {
        const sData = await apiFetch('/service_org');
        if (serviceSel) {
            serviceSel.innerHTML = '<option value="">-- Ou sélectionner un service --</option>';
            // Grouper par parent
            const parents = sData.list.filter(s => !s.parent_id);
            const children = sData.list.filter(s => s.parent_id);
            parents.forEach(p => {
                const grp = document.createElement('optgroup');
                grp.label = `${p.code || ''} ${p.nom || ''}`.trim();
                const subs = children.filter(c => c.parent_id === p.id);
                subs.forEach(s => {
                    const opt = document.createElement('option');
                    opt.value = s.nom || s.code || '';
                    opt.textContent = `└─ ${s.nom || s.code || ''}`.trim();
                    grp.appendChild(opt);
                });
                serviceSel.appendChild(grp);
                // Si pas de sous-services, ajouter le parent directement
                if (!subs.length) {
                    const opt = document.createElement('option');
                    opt.value = p.nom || p.code || '';
                    opt.textContent = `${p.code || ''} ${p.nom || ''}`.trim();
                    serviceSel.appendChild(opt);
                }
            });
        }
    } catch(e) {}

    await loadContactsForSelect(contactSel, '');
    if (contactSel) contactSel.focus();
}

async function saveMembreEquipe(projetId) {
    const contactVal = document.getElementById(`new-membre-select-${projetId}`)?.value?.trim();
    const serviceVal = document.getElementById(`new-service-select-${projetId}`)?.value?.trim();
    const libreVal   = document.getElementById(`new-membre-label-${projetId}`)?.value?.trim();
    const label = contactVal || serviceVal || libreVal;
    if (!label) { showMsg('Renseignez un membre', false); return; }
    await apiFetch(`/projet/${projetId}/equipe`, {
        method: 'POST',
        body: JSON.stringify({ membre_label: label })
    });
    await ficheProjet(projetId);
    switchProjTab('equipe');
}

async function deleteMembreEquipe(projetId, membreId) {
    if (!confirm('Retirer ce membre de l\'équipe ?')) return;
    await apiFetch(`/projet/${projetId}/equipe/${membreId}`, { method: 'DELETE' });
    await ficheProjet(projetId);
    switchProjTab('equipe');
}

// ─── Contacts projet ─────────────────────────────────────────────────────────
async function showAddContactForm(projetId) {
    const form = document.getElementById(`add-contact-form-${projetId}`);
    if (!form) return;
    form.style.display = form.style.display === 'none' ? '' : 'none';
    if (form.style.display === 'none') return;
    const sel = document.getElementById(`new-contact-id-${projetId}`);
    const searchInput = document.getElementById(`new-contact-search-${projetId}`);
    await loadContactsIdForSelect(sel, '', searchInput);
    if (searchInput) searchInput.focus();
}

async function saveProjetContact(projetId) {
    const contactId    = document.getElementById(`new-contact-id-${projetId}`)?.value;
    const contactLibre = document.getElementById(`new-contact-libre-${projetId}`)?.value?.trim();
    const role         = document.getElementById(`new-contact-role-${projetId}`)?.value?.trim();
    if (!contactId && !contactLibre) { showMsg('Sélectionnez un contact ou saisissez un nom', false); return; }
    const body = { role };
    if (contactId) body.contact_id = parseInt(contactId);
    else body.contact_libre = contactLibre;
    await apiFetch(`/projet/${projetId}/contact`, { method: 'POST', body: JSON.stringify(body) });
    await ficheProjet(projetId);
    switchProjTab('contacts');
}

async function deleteProjetContact(projetId, contactId, contactLibre) {
    if (!confirm('Retirer ce contact du projet ?')) return;
    if (contactId) {
        await apiFetch(`/projet/${projetId}/contact/${contactId}`, { method: 'DELETE' });
    } else {
        await apiFetch(`/projet/${projetId}/contact/libre`, {
            method: 'DELETE',
            body: JSON.stringify({ contact_libre: contactLibre })
        });
    }
    await ficheProjet(projetId);
    switchProjTab('contacts');
}

// Fermer modals au clic sur l'overlay
document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', e => {
        if (e.target === overlay) overlay.classList.remove('open');
    });
});

// Enter key sur le formulaire de login
document.getElementById('login-pass').addEventListener('keydown', e => {
    if (e.key === 'Enter') doLogin();
});
document.getElementById('login-user').addEventListener('keydown', e => {
    if (e.key === 'Enter') document.getElementById('login-pass').focus();
});

// Peupler le select service du modal "Nouvel utilisateur" à l'ouverture
document.getElementById('modal-add-user').addEventListener('click', function(e) {
    if (e.target === this) return;
}, false);
const _addUserBtn = document.querySelector('[onclick="openModal(\'modal-add-user\')"]');
if (_addUserBtn) {
    _addUserBtn.addEventListener('click', () => {
        setTimeout(_populateNewUserServiceSelect, 50);
    });
}

// Vérifier token existant (refresh de page)
const _existingToken = getToken();
if (_existingToken) {
    const _payload = decodeToken(_existingToken);
    if (_payload && _payload.exp * 1000 > Date.now()) {
        hideLoginOverlay();
        applyRoleUI(_payload);
        initRefs().then(() => { loadDashboard(); loadNotifications(); });
    } else {
        removeToken();
        showLoginOverlay();
    }
} else {
    showLoginOverlay();
}

// ─── Colonnes redimensionnables ─────────────────────────────────
function makeTableResizable(table) {
    // Éviter de re-initialiser si déjà fait
    if (table._resizable) return;
    table._resizable = true;

    table.querySelectorAll('th').forEach(th => {
        // Ne pas ajouter sur la colonne checkbox (width fixe)
        if (th.querySelector('input[type="checkbox"]')) return;

        // Retirer un ancien handle s'il existe
        const old = th.querySelector('.col-resizer');
        if (old) old.remove();

        const handle = document.createElement('div');
        handle.className = 'col-resizer';
        th.appendChild(handle);

        handle.addEventListener('mousedown', e => {
            const startX   = e.clientX;
            const startW   = th.offsetWidth;
            handle.classList.add('is-dragging');
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';

            const onMove = e => {
                const newW = Math.max(50, startW + e.clientX - startX);
                th.style.width    = newW + 'px';
                th.style.minWidth = newW + 'px';
            };
            const onUp = () => {
                handle.classList.remove('is-dragging');
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
                document.removeEventListener('mousemove', onMove);
                document.removeEventListener('mouseup', onUp);
            };
            document.addEventListener('mousemove', onMove);
            document.addEventListener('mouseup', onUp);
            e.preventDefault();
        });
    });
}

// ═══════════════════════════════════════════════════════════════
// MODULE TPE — Terminaux de Paiement Électronique
// ═══════════════════════════════════════════════════════════════

// ─── Modules : activation / nav tabs ────────────────────────
async function loadModules() {
    try {
        const data = await apiFetch('/modules');
        const modules = data.list || [];
        const tpeMod = modules.find(m => m.module_name === 'tpe');
        const tpeEnabled = tpeMod && tpeMod.enabled;
        const navTpe = document.getElementById('nav-tpe');
        if (navTpe) navTpe.style.display = tpeEnabled ? '' : 'none';
        // Exposer pour réutilisation (ex: bouton add dans la vue)
        window._tpeModuleEnabled = tpeEnabled;
    } catch {
        // silencieux si non connecté
    }
}

async function loadAdminModules() {
    const el = document.getElementById('admin-modules-list');
    if (!el) return;
    try {
        const data = await apiFetch('/admin/modules');
        const modules = data.list || [];
        if (!modules.length) {
            el.innerHTML = '<p style="color:#999;font-style:italic;">Aucun module disponible.</p>';
            return;
        }
        el.innerHTML = modules.map(m => {
            const label = { tpe: 'Terminaux de Paiement (TPE)' }[m.module_name] || m.module_name;
            const desc  = { tpe: 'Gestion des terminaux de paiement électronique, cartes commerçant et régisseurs.' }[m.module_name] || '';
            return `<div style="display:flex;align-items:flex-start;gap:16px;padding:14px 0;border-bottom:1px solid #eee;">
                <label class="switch" style="margin-top:2px;cursor:pointer;">
                    <input type="checkbox" ${m.enabled ? 'checked' : ''}
                           onchange="toggleModule('${_h(m.module_name)}', this.checked)"
                           style="width:36px;height:20px;cursor:pointer;">
                </label>
                <div>
                    <strong>${_h(label)}</strong>
                    <div style="font-size:.85em;color:#666;margin-top:2px;">${_h(desc)}</div>
                    ${m.date_activation ? `<div style="font-size:.78em;color:#aaa;margin-top:2px;">Dernière modification : ${m.date_activation.substring(0,19).replace('T',' ')}</div>` : ''}
                </div>
            </div>`;
        }).join('');
    } catch (e) {
        el.innerHTML = `<p style="color:#c00;">Erreur : ${_h(e.message)}</p>`;
    }
}

async function toggleModule(moduleName, enabled) {
    try {
        await apiFetch(`/admin/modules/${moduleName}`, {
            method: 'PUT',
            body: JSON.stringify({ enabled })
        });
        showMsg(enabled ? `Module "${moduleName}" activé` : `Module "${moduleName}" désactivé`);
        loadModules(); // rafraîchir nav tabs
    } catch (e) {
        showMsg('Erreur : ' + e.message, false);
        loadAdminModules(); // remettre l'état UI à jour
    }
}

// ─── SMTP config & test ─────────────────────────────────────
async function loadSmtpConfig() {
    const el = document.getElementById('smtp-config-display');
    if (!el) return;
    try {
        const cfg = await apiFetch('/admin/smtp/config');
        if (cfg.configured) {
            el.innerHTML = `
                <span style="color:#27ae60;font-weight:bold;">✔ Configuré</span><br>
                Serveur : <strong>${_h(cfg.host)}</strong> : <strong>${_h(cfg.port)}</strong><br>
                Compte  : <strong>${_h(cfg.user)}</strong><br>
                Expéditeur : <strong>${_h(cfg.from)}</strong><br>
                TLS/STARTTLS : <strong>${cfg.tls === 'true' ? 'Oui (port 587)' : 'Non — SSL (port 465)'}</strong>
            `;
        } else {
            el.innerHTML = '<span style="color:#e74c3c;">✘ Non configuré — ajoutez SMTP_HOST et SMTP_USER dans le .env</span>';
        }
    } catch (e) {
        el.textContent = 'Impossible de lire la configuration : ' + e.message;
    }
}

async function testSmtp() {
    const toEmail = document.getElementById('smtp-test-email')?.value.trim();
    if (!toEmail) { showMsg('Saisissez un email destinataire', false); return; }
    const btn = document.getElementById('smtp-test-btn');
    const res  = document.getElementById('smtp-test-result');
    btn.disabled = true;
    btn.textContent = 'Envoi en cours…';
    res.style.display = 'none';
    try {
        const data = await apiFetch('/admin/smtp/test', {
            method: 'POST',
            body: JSON.stringify({ to_email: toEmail })
        });
        res.style.display = 'block';
        if (data.success) {
            res.style.background = '#d4edda';
            res.style.border = '1px solid #c3e6cb';
            res.style.color = '#155724';
            res.innerHTML = `✅ <strong>Succès !</strong> Email de test envoyé à <strong>${_h(toEmail)}</strong>.<br>
                <small>Vérifiez votre boîte mail (et le dossier spam).</small>`;
        } else {
            res.style.background = '#f8d7da';
            res.style.border = '1px solid #f5c6cb';
            res.style.color = '#721c24';
            res.innerHTML = `✘ <strong>Échec :</strong> ${_h(data.error || 'Erreur inconnue')}`;
        }
    } catch (e) {
        res.style.display = 'block';
        res.style.background = '#f8d7da';
        res.style.border = '1px solid #f5c6cb';
        res.style.color = '#721c24';
        res.innerHTML = `✘ <strong>Erreur :</strong> ${_h(e.message)}`;
    } finally {
        btn.disabled = false;
        btn.textContent = 'Tester la connexion';
    }
}

// ─── TPE : liste ────────────────────────────────────────────
async function loadTpe() {
    const q = document.getElementById('tpe-search')?.value.trim() || '';
    const params = new URLSearchParams();
    if (q) params.set('q', q);
    try {
        const data = await apiFetch('/tpe?' + params);
        _renderTpeRows(data.list || []);
        // Stats
        const st = data.stats || {};
        const set = (id, v) => { const e = document.getElementById(id); if (e) e.textContent = v ?? '-'; };
        set('tpe-stat-fiches',    st.total_fiches    ?? '-');
        set('tpe-stat-appareils', st.total_appareils ?? '-');
        set('tpe-stat-ethernet',  st.nb_ethernet     ?? '-');
        set('tpe-stat-4g',        st.nb_4_5g         ?? '-');
        set('tpe-stat-bo',        st.nb_backoffice   ?? '-');
        // Bouton ajout selon rôle
        const addBtn = document.getElementById('tpe-add-btn');
        if (addBtn) {
            const p = decodeToken(getToken());
            addBtn.style.display = (p && (p.role === 'admin' || p.role === 'gestionnaire')) ? '' : 'none';
        }
    } catch (e) {
        showMsg('Erreur chargement TPE : ' + e.message, false);
    }
}

function _renderTpeRows(list) {
    const tbody = document.getElementById('tpe-tbody');
    if (!tbody) return;
    // Réinitialiser l'état de sélection
    _updateTpeBulkBar();
    const chkAll = document.getElementById('tpe-check-all');
    if (chkAll) chkAll.checked = false;
    if (!list.length) {
        tbody.innerHTML = '<tr><td colspan="11" style="text-align:center;color:#999;padding:16px;font-style:italic;">Aucun TPE enregistré.</td></tr>';
        return;
    }
    const p = decodeToken(getToken());
    const canEdit = p && (p.role === 'admin' || p.role === 'gestionnaire');
    tbody.innerHTML = list.map(t => {
        const regisseur = [t.regisseur_prenom, t.regisseur_nom].filter(Boolean).join(' ') || '-';
        const types = [];
        if (t.type_ethernet) types.push('Ethernet');
        if (t.type_4_5g)     types.push('4/5G');
        const typeBadge = types.map(ty => `<span style="background:#dbeafe;color:#1d4ed8;border-radius:3px;padding:1px 5px;font-size:.78em;margin-right:3px;">${ty}</span>`).join('');
        const cartes = t.cartes || [];
        const cartesStr = cartes.length
            ? cartes.map(c => _h(c.numero)).join(', ')
            : '<span style="color:#ccc;">—</span>';
        const boEmail = t.backoffice_email ? `<br><small style="color:#555;">${_h(t.backoffice_email)}</small>` : '';
        const bo = t.backoffice_actif
            ? `<span style="color:#27ae60;">Oui</span>${boEmail}`
            : `<span style="color:#ccc;">Non</span>${boEmail}`;
        const actions = canEdit
            ? `<button class="btn btn-sm" onclick="editTpe(${t.id})" style="margin-right:4px;">Modifier</button>
               <button class="btn btn-danger btn-sm" onclick="deleteTpe(${t.id}, '${_h(t.service).replace(/['\u2018\u2019]/g,'&#39;')}')">Suppr.</button>`
            : '';
        return `<tr>
            <td style="text-align:center;"><input type="checkbox" class="tpe-chk" value="${t.id}" onchange="_updateTpeBulkBar()"></td>
            <td>${_h(t.service)}</td>
            <td>${_h(regisseur)}</td>
            <td>${_h(t.regisseur_telephone) || '-'}</td>
            <td>${t.shop_id || '-'}</td>
            <td>${_h(t.modele_tpe) || '-'}</td>
            <td>${typeBadge || '<span style="color:#ccc;">—</span>'}</td>
            <td style="font-size:.82em;">${cartesStr}</td>
            <td>${bo}</td>
            <td style="text-align:center;">${t.nombre_tpe ?? 1}</td>
            <td>${actions}</td>
        </tr>`;
    }).join('');
    // Activer le redimensionnement des colonnes (reset pour re-attacher après re-render)
    const tbl = document.getElementById('tpe-table');
    if (tbl) { tbl._resizable = false; makeTableResizable(tbl); }
}

function toggleAllTpe() {
    const checked = document.getElementById('tpe-check-all')?.checked;
    document.querySelectorAll('#tpe-tbody .tpe-chk').forEach(cb => { cb.checked = checked; });
    _updateTpeBulkBar();
}

function _updateTpeBulkBar() {
    const selected = document.querySelectorAll('#tpe-tbody .tpe-chk:checked');
    const bar = document.getElementById('tpe-bulk-bar');
    const cnt = document.getElementById('tpe-bulk-count');
    if (!bar) return;
    if (selected.length > 0) {
        bar.style.display = 'flex';
        if (cnt) cnt.textContent = `${selected.length} TPE sélectionné${selected.length > 1 ? 's' : ''}`;
    } else {
        bar.style.display = 'none';
    }
    // Mettre à jour l'état indéterminé de la case "tout sélectionner"
    const all = document.querySelectorAll('#tpe-tbody .tpe-chk');
    const chkAll = document.getElementById('tpe-check-all');
    if (chkAll) {
        chkAll.indeterminate = selected.length > 0 && selected.length < all.length;
        chkAll.checked = all.length > 0 && selected.length === all.length;
    }
}

function clearTpeSelection() {
    document.querySelectorAll('#tpe-tbody .tpe-chk').forEach(cb => { cb.checked = false; });
    const chkAll = document.getElementById('tpe-check-all');
    if (chkAll) { chkAll.checked = false; chkAll.indeterminate = false; }
    _updateTpeBulkBar();
}

async function deleteTpeSelected() {
    const checked = [...document.querySelectorAll('#tpe-tbody .tpe-chk:checked')];
    if (!checked.length) return;
    if (!confirm(`Supprimer ${checked.length} TPE sélectionné${checked.length > 1 ? 's' : ''} ?`)) return;
    let errors = 0;
    for (const cb of checked) {
        try {
            await apiFetch(`/tpe/${cb.value}`, { method: 'DELETE' });
        } catch { errors++; }
    }
    if (errors) showMsg(`${checked.length - errors} supprimé(s), ${errors} erreur(s).`, false);
    else showMsg(`${checked.length} TPE supprimé${checked.length > 1 ? 's' : ''}.`);
    loadTpe();
}

// ─── TPE : export Excel ──────────────────────────────────────
async function exportTpe() {
    const token = getToken();
    const a = document.createElement('a');
    a.href = `${API}/tpe/export`;
    a.setAttribute('download', 'export_tpe.xlsx');
    // fetch avec auth header pour forcer le téléchargement
    try {
        const res = await fetch(`${API}/tpe/export`, {
            headers: { 'Authorization': 'Bearer ' + token }
        });
        if (!res.ok) throw new Error('Export échoué');
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'export_tpe.xlsx';
        link.click();
        URL.revokeObjectURL(url);
    } catch (e) {
        showMsg('Erreur export : ' + e.message, false);
    }
}

// ─── TPE : modal helpers ─────────────────────────────────────
function toggleTpeBackoffice() {
    const checked = document.getElementById('tpe-backoffice-actif')?.checked;
    const row = document.getElementById('tpe-backoffice-email-row');
    if (row) row.style.display = checked ? '' : 'none';
}

function toggleTpeEthernet() {
    const checked = document.getElementById('tpe-type-ethernet')?.checked;
    const row = document.getElementById('tpe-reseau-row');
    if (row) row.style.display = checked ? '' : 'none';
}

function addTpeCarte(carte = {}) {
    const container = document.getElementById('tpe-cartes-container');
    if (!container) return;
    const div = document.createElement('div');
    div.style.cssText = 'display:grid;grid-template-columns:1fr 1fr 1fr auto;gap:8px;margin-bottom:6px;align-items:end;';
    div.innerHTML = `
        <div><label style="font-size:.8em;color:#666;">N° carte</label>
             <input class="form-control carte-numero" value="${_h(carte.numero || '')}"></div>
        <div><label style="font-size:.8em;color:#666;">N° série TPE</label>
             <input class="form-control carte-serie" value="${_h(carte.numero_serie_tpe || '')}"></div>
        <div><label style="font-size:.8em;color:#666;">Modèle</label>
             <input class="form-control carte-modele" value="${_h(carte.modele_tpe || '')}"></div>
        <button type="button" class="btn btn-danger btn-sm" onclick="this.parentElement.remove()"
                style="margin-bottom:0;padding:6px 10px;">✕</button>
    `;
    container.appendChild(div);
}

function _getTpeCartes() {
    const rows = document.querySelectorAll('#tpe-cartes-container > div');
    const cartes = [];
    rows.forEach(row => {
        const numero = row.querySelector('.carte-numero')?.value.trim();
        if (numero) {
            cartes.push({
                numero,
                numero_serie_tpe: row.querySelector('.carte-serie')?.value.trim() || null,
                modele_tpe:       row.querySelector('.carte-modele')?.value.trim() || null,
            });
        }
    });
    return cartes;
}

function _resetTpeModal() {
    ['tpe-id','tpe-service','tpe-reg-prenom','tpe-reg-nom','tpe-reg-tel',
     'tpe-suppleants','tpe-shop-id','tpe-nombre','tpe-modele',
     'tpe-backoffice-email','tpe-reseau-ip','tpe-reseau-masque','tpe-reseau-passerelle'
    ].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });
    ['tpe-backoffice-actif','tpe-type-ethernet','tpe-type-4g'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.checked = false;
    });
    document.getElementById('tpe-nombre').value = '1';
    document.getElementById('tpe-backoffice-email-row').style.display = 'none';
    document.getElementById('tpe-reseau-row').style.display = 'none';
    document.getElementById('tpe-cartes-container').innerHTML = '';
}

// ─── TPE : créer ─────────────────────────────────────────────
function openAddTpe() {
    _resetTpeModal();
    document.getElementById('modal-tpe-titre').textContent = 'Nouveau TPE';
    openModal('modal-tpe');
}

// ─── TPE : éditer ────────────────────────────────────────────
async function editTpe(id) {
    _resetTpeModal();
    document.getElementById('modal-tpe-titre').textContent = 'Modifier le TPE';
    try {
        const data = await apiFetch(`/tpe/${id}`);
        const t = data.tpe;
        document.getElementById('tpe-id').value = t.id;
        document.getElementById('tpe-service').value        = t.service || '';
        document.getElementById('tpe-reg-prenom').value     = t.regisseur_prenom || '';
        document.getElementById('tpe-reg-nom').value        = t.regisseur_nom || '';
        document.getElementById('tpe-reg-tel').value        = t.regisseur_telephone || '';
        document.getElementById('tpe-suppleants').value     = t.regisseurs_suppleants || '';
        document.getElementById('tpe-shop-id').value        = t.shop_id ?? '';
        document.getElementById('tpe-nombre').value         = t.nombre_tpe ?? 1;
        document.getElementById('tpe-modele').value         = t.modele_tpe || '';
        document.getElementById('tpe-backoffice-actif').checked = !!t.backoffice_actif;
        document.getElementById('tpe-backoffice-email').value   = t.backoffice_email || '';
        document.getElementById('tpe-type-ethernet').checked    = !!t.type_ethernet;
        document.getElementById('tpe-type-4g').checked          = !!t.type_4_5g;
        document.getElementById('tpe-reseau-ip').value          = t.reseau_ip || '';
        document.getElementById('tpe-reseau-masque').value      = t.reseau_masque || '';
        document.getElementById('tpe-reseau-passerelle').value  = t.reseau_passerelle || '';
        toggleTpeBackoffice();
        toggleTpeEthernet();
        (t.cartes || []).forEach(c => addTpeCarte(c));
        openModal('modal-tpe');
    } catch (e) {
        showMsg('Erreur chargement TPE : ' + e.message, false);
    }
}

// ─── TPE : sauvegarder ───────────────────────────────────────
async function saveTpe() {
    const id      = document.getElementById('tpe-id').value;
    const service = document.getElementById('tpe-service').value.trim();
    if (!service) { showMsg('Le champ Service est obligatoire.', false); return; }

    const payload = {
        service,
        regisseur_prenom:    document.getElementById('tpe-reg-prenom').value.trim() || null,
        regisseur_nom:       document.getElementById('tpe-reg-nom').value.trim()    || null,
        regisseur_telephone: document.getElementById('tpe-reg-tel').value.trim()    || null,
        regisseurs_suppleants: document.getElementById('tpe-suppleants').value.trim() || null,
        shop_id:             parseInt(document.getElementById('tpe-shop-id').value)  || 0,
        nombre_tpe:          parseInt(document.getElementById('tpe-nombre').value)   || 1,
        modele_tpe:          document.getElementById('tpe-modele').value.trim()      || null,
        backoffice_actif:    document.getElementById('tpe-backoffice-actif').checked,
        backoffice_email:    document.getElementById('tpe-backoffice-email').value.trim() || null,
        type_ethernet:       document.getElementById('tpe-type-ethernet').checked,
        type_4_5g:           document.getElementById('tpe-type-4g').checked,
        reseau_ip:           document.getElementById('tpe-reseau-ip').value.trim()          || null,
        reseau_masque:       document.getElementById('tpe-reseau-masque').value.trim()      || null,
        reseau_passerelle:   document.getElementById('tpe-reseau-passerelle').value.trim()  || null,
        cartes: _getTpeCartes(),
    };
    try {
        if (id) {
            await apiFetch(`/tpe/${id}`, { method: 'PUT', body: JSON.stringify(payload) });
            showMsg('TPE mis à jour.');
        } else {
            await apiFetch('/tpe', { method: 'POST', body: JSON.stringify(payload) });
            showMsg('TPE créé.');
        }
        closeModal('modal-tpe');
        loadTpe();
    } catch (e) {
        showMsg('Erreur : ' + e.message, false);
    }
}

// ─── TPE : supprimer ─────────────────────────────────────────
async function deleteTpe(id, label) {
    if (!confirm(`Supprimer le TPE "${label}" ?`)) return;
    try {
        await apiFetch(`/tpe/${id}`, { method: 'DELETE' });
        showMsg('TPE supprimé.');
        loadTpe();
    } catch (e) {
        showMsg('Erreur : ' + e.message, false);
    }
}
