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

function fmt(n) {
    if (n == null || n === '') return '-';
    return Number(n).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtDate(d) {
    if (!d) return '-';
    return String(d).substring(0, 10);
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

async function apiFetch(path, opts = {}) {
    const token = getToken();
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = 'Bearer ' + token;
    const res = await fetch(API + path, { headers, ...opts });
    if (res.status === 401) {
        removeToken();
        showLoginOverlay();
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
    notifications: loadNotifications,
    admin:         loadAdminUsers,
};

function showView(name) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.querySelectorAll('nav button').forEach(b => b.classList.remove('active'));
    const view = document.getElementById('view-' + name);
    if (view) view.classList.add('active');
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
    } catch (e) { console.error('Dashboard:', e); }
}

// ─── BUDGETS ───────────────────────────────────────────────

let _lignesSelectId = null; // ligne sélectionnée dans la vue lignes

function switchBudgetSubTab(tab) {
    document.querySelectorAll('.budget-subtab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.budget-subview').forEach(v => v.classList.remove('active'));
    const idx = tab === 'lignes' ? 1 : 0;
    document.querySelectorAll('.budget-subtab')[idx].classList.add('active');
    document.getElementById(`budget-sub-${tab}`).classList.add('active');
    if (tab === 'lignes') loadAllLignes();
}

async function loadAllLignes() {
    try {
        const budgetId = document.getElementById('lignes-filter-budget').value || '';
        const search   = (document.getElementById('lignes-search').value || '').toLowerCase();
        const url = budgetId ? `/lignes?budget_id=${budgetId}` : '/lignes';
        const data = await apiFetch(url);
        _lignesCache = data.list || [];
        let lignes = _lignesCache;
        if (search) {
            lignes = lignes.filter(l =>
                (l.libelle || '').toLowerCase().includes(search) ||
                (l.application_nom || '').toLowerCase().includes(search) ||
                (l.fournisseur_nom || '').toLowerCase().includes(search)
            );
        }
        const tbody = document.getElementById('lignes-tbody');
        if (!lignes.length) {
            tbody.innerHTML = '<tr><td colspan="11" style="text-align:center;color:#999;font-style:italic;padding:18px;">Aucune ligne trouvée.</td></tr>';
            return;
        }
        tbody.innerHTML = lignes.map((l, i) => {
            const taux = l.taux_engagement || 0;
            const alerte = l.alerte
                ? '<span style="color:#e74c3c;font-weight:bold;">⚠ SEUIL</span>'
                : '<span style="color:#27ae60;font-weight:bold;">✓ OK</span>';
            const solde = parseFloat(l.montant_solde || 0);
            const soldeColor = solde < 0 ? 'color:#e74c3c;font-weight:bold;' : 'color:#27ae60;';
            return `<tr class="ligne-row${_lignesSelectId===l.id?' selected':''}" data-id="${l.id}" onclick="selectLigne(${l.id}, '${(l.libelle||'Ligne #'+l.id).replace(/'/g,"&#39;")}')">
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
        // Remettre la sélection si toujours présente
        if (_lignesSelectId) selectLigne(_lignesSelectId, null, true);
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
    const res = await apiFetch(url, method, body);
    if (res.success) {
        showMsg(id ? 'Ligne mise à jour' : 'Ligne créée');
        closeModal('modal-edit-ligne');
        loadAllLignes();
        loadBudget(); // recalculer les agrégats budget
    } else {
        showMsg(res.error || 'Erreur lors de l\'enregistrement', false);
    }
}

async function loadBudget() {
    try {
        const data = await apiFetch('/budget');
        _budgetsList = data.details || [];
        // Alimenter le filtre budget de la vue lignes
        const filterSel = document.getElementById('lignes-filter-budget');
        if (filterSel && filterSel.options.length <= 1) {
            _budgetsList.forEach(b => {
                const opt = document.createElement('option');
                opt.value = b.id;
                opt.textContent = `${b.entite_code || b.entite_nom || '?'} — ${b.nature || '?'} ${b.exercice || '?'}`;
                filterSel.appendChild(opt);
            });
        }
        const tbody = document.getElementById('budget-tbody');
        tbody.innerHTML = (data.details || []).map(b => {
            const vote   = b.montant_vote   || 0;
            const engage = b.montant_engage || 0;
            const label    = `${b.entite_code || b.entite_nom || '?'} — ${b.exercice || '?'} (${b.nature || '?'})`;
            const labelEsc = label.replace(/'/g, "\\'");
            return `<tr>
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
                    <button class="btn btn-success btn-sm" onclick="openVoterBudget(${b.id}, ${vote})">Voter</button>
                    <button class="btn btn-danger btn-sm" onclick="deleteBudget(${b.id})">Suppr.</button>
                </td>
            </tr>`;
        }).join('');
    } catch (e) { showMsg('Erreur chargement budgets', false); }
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

async function loadBC() {
    const params = new URLSearchParams();
    const statut  = document.getElementById('bc-filter-statut')?.value;
    const entite  = document.getElementById('bc-filter-entite')?.value;
    const search  = document.getElementById('bc-search')?.value;
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

        const tbody = document.getElementById('bc-tbody');
        tbody.innerHTML = (data.list || []).map(b => `
            <tr>
                <td>${b.id}</td>
                <td><strong>${b.numero_bc || '-'}</strong></td>
                <td>${b.objet || '-'}</td>
                <td>${b.fournisseur_nom || '-'}</td>
                <td>${b.entite_code || '-'}</td>
                <td>${fmt(b.montant_ht)}</td>
                <td>${fmt(b.montant_ttc)}</td>
                <td>${badge(b.statut)}</td>
                <td style="white-space:nowrap;">
                    <button class="btn btn-info btn-sm" onclick="ficheBc(${b.id})">Fiche</button>
                    <button class="btn btn-sm" style="background:#6c757d;color:#fff;" onclick="editBC(${b.id})">Modifier</button>
                    ${['BROUILLON','EN_ATTENTE'].includes(b.statut)
                        ? `<button class="btn btn-warning btn-sm" onclick="validerBc(${b.id})">Valider</button>` : ''}
                    ${b.statut === 'VALIDE'
                        ? `<button class="btn btn-success btn-sm" onclick="openImputer(${b.id})">Imputer</button>` : ''}
                    ${!['IMPUTE','SOLDE'].includes(b.statut)
                        ? `<button class="btn btn-danger btn-sm" onclick="deleteBC(${b.id})">Suppr.</button>` : ''}
                </td>
            </tr>`).join('');
    } catch (e) { showMsg('Erreur chargement BC', false); }
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
        setVal('edit-bc-ligne',       bc.ligne_budgetaire_id);
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

async function loadContrats() {
    try {
        const data = await apiFetch('/contrat');
        _cache.contrats = data.list || [];
        const tbody = document.getElementById('contrats-tbody');
        tbody.innerHTML = _cache.contrats.map(c => {
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
                <td style="font-size:.78em;">${c.type_contrat || '-'}</td>
                <td>${alerteBadge(niveau)}</td>
                <td style="white-space:nowrap;">
                    <button class="btn btn-info btn-sm" onclick="ficheContrat(${c.id})">Fiche</button>
                    <button class="btn btn-warning btn-sm" onclick="editContrat(${c.id})">Éditer</button>
                    ${['ACTIF','RECONDUIT'].includes(c.statut)
                        ? `<button class="btn btn-sm" style="background:#6c757d;color:#fff;" onclick="openReconduire(${c.id})">Reconduire</button>` : ''}
                    <button class="btn btn-danger btn-sm" onclick="deleteContrat(${c.id})">Suppr.</button>
                </td>
            </tr>`;
        }).join('');
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
    document.getElementById('edit-contrat-debut').value    = fmtDate(data.date_debut) === '-' ? '' : fmtDate(data.date_debut);
    document.getElementById('edit-contrat-fin').value      = fmtDate(data.date_fin) === '-' ? '' : fmtDate(data.date_fin);
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

async function loadProjets() {
    try {
        const data = await apiFetch('/projet');
        _cache.projets = data.list || [];
        const tbody = document.getElementById('projets-tbody');
        tbody.innerHTML = _cache.projets.map(p => `
            <tr>
                <td>${p.id}</td>
                <td>${p.code || '-'}</td>
                <td><strong>${p.nom || '-'}</strong></td>
                <td style="font-size:.8em;">${p.type_projet || '-'}</td>
                <td style="font-size:.8em;">${p.phase || '-'}</td>
                <td>${badge(p.statut)}</td>
                <td>${badge(p.priorite)}</td>
                <td style="font-size:.8em;">${p.service_code || p.service_nom || '-'}</td>
                <td>${fmt(p.budget_estime)}</td>
                <td>${p.avancement != null ? p.avancement + ' %' : '-'}</td>
                <td>${fmtDate(p.date_debut)}</td>
                <td>${fmtDate(p.date_fin_prevue)}</td>
                <td style="white-space:nowrap;">
                    <button class="btn btn-info btn-sm" onclick="ficheProjet(${p.id})">Fiche</button>
                    <button class="btn btn-warning btn-sm" onclick="editProjet(${p.id})">Éditer</button>
                    <button class="btn btn-danger btn-sm" onclick="deleteProjet(${p.id})">Suppr.</button>
                </td>
            </tr>`).join('');
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

async function ficheProjet(id) {
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

        const tachesHtml = (p.taches || []).length === 0
            ? '<p style="color:#888;font-style:italic;margin:8px 0;">Aucune tâche liée.</p>'
            : `<table style="width:100%;border-collapse:collapse;font-size:.82em;margin-top:6px;">
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
                    <input id="new-membre-label-${id}" type="text" placeholder="Nom du membre" style="width:100%;padding:6px 8px;border:1px solid #ccc;border-radius:4px;font-size:.85em;box-sizing:border-box;margin-bottom:6px;">
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
                    <input id="new-membre-label-${id}" type="text" placeholder="Nom du membre" style="width:100%;padding:6px 8px;border:1px solid #ccc;border-radius:4px;font-size:.85em;box-sizing:border-box;margin-bottom:6px;">
                    <div style="display:flex;gap:6px;">
                        <button onclick="saveMembreEquipe(${id})" style="background:#27ae60;color:#fff;border:none;border-radius:4px;padding:5px 14px;cursor:pointer;font-size:.82em;">Ajouter</button>
                        <button onclick="document.getElementById('add-membre-form-${id}').style.display='none'" style="background:#95a5a6;color:#fff;border:none;border-radius:4px;padding:5px 14px;cursor:pointer;font-size:.82em;">Annuler</button>
                    </div>
                </div>
            </div>`;
        })();

        // ── Contacts HTML ───────────────────────────────────────────────────
        const contactsHtml = (p.contacts_externes || []).length === 0
            ? '<p style="color:#aaa;font-style:italic;margin:12px 0;">Aucun contact externe lié.</p>'
            : `<table style="width:100%;border-collapse:collapse;font-size:.82em;margin-top:6px;">
                <thead><tr style="background:#1a3c5e;color:#fff;">
                    <th style="padding:6px;">Rôle</th><th>Nom</th><th>Organisation</th><th>Email</th><th>Tél.</th>
                </tr></thead><tbody>
                ${p.contacts_externes.map(c => `<tr style="border-bottom:1px solid #eee;">
                    <td style="padding:5px;font-weight:bold;color:#2563a8;">${c.role || '-'}</td>
                    <td>${c.prenom || ''} ${c.nom || ''}</td>
                    <td style="color:#666;">${c.organisation || '-'}</td>
                    <td style="color:#2563a8;">${c.email || '-'}</td>
                    <td>${c.telephone || '-'}</td>
                </tr>`).join('')}
                </tbody></table>`;

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

            <div class="modal-footer" style="margin-top:14px;">
                <button class="btn" style="background:#6c757d;color:#fff;" onclick="printFicheProjet()">&#128424; Imprimer</button>
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
    const d2 = v => (fmtDate(v) === '-' ? '' : fmtDate(v));
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
                <td style="white-space:nowrap;">
                    <button class="btn btn-warning btn-sm" onclick="editTache(${t.id})">Éditer</button>
                    <button class="btn btn-danger btn-sm" onclick="deleteTache(${t.id})">Suppr.</button>
                </td>
            </tr>`).join('');
    } catch (e) { showMsg('Erreur chargement tâches', false); }
}

async function addTache() {
    const body = {
        titre:             document.getElementById('tache-titre').value,
        projet_id:         document.getElementById('tache-projet').value || null,
        statut:            document.getElementById('tache-statut').value,
        priorite:          document.getElementById('tache-priorite').value || null,
        date_echeance:     document.getElementById('tache-echeance').value || null,
        estimation_heures: document.getElementById('tache-heures').value || null,
        avancement:        0,
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
    const ech = data.date_echeance ? data.date_echeance.split('T')[0] : '';
    document.getElementById('edit-tache-echeance').value   = ech;
    document.getElementById('edit-tache-heures').value     = data.estimation_heures ?? '';
    document.getElementById('edit-tache-avancement').value = data.avancement ?? '';
    openModal('modal-edit-tache');
}

async function saveTache() {
    const id = document.getElementById('edit-tache-id').value;
    const body = {
        titre:             document.getElementById('edit-tache-titre').value,
        projet_id:         document.getElementById('edit-tache-projet').value || null,
        statut:            document.getElementById('edit-tache-statut').value,
        priorite:          document.getElementById('edit-tache-priorite').value || null,
        date_echeance:     document.getElementById('edit-tache-echeance').value || null,
        estimation_heures: document.getElementById('edit-tache-heures').value || null,
        avancement:        document.getElementById('edit-tache-avancement').value || 0,
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
    const params   = projetId ? `?projet_id=${projetId}` : '';
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
            return `<div style="flex:1;min-width:190px;max-width:260px;background:#fff;border-radius:8px;
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

function editFournisseur(id) {
    const data = _cache.fournisseurs.find(f => f.id === id);
    if (!data) { showMsg('Données non chargées, rechargez', false); return; }
    document.getElementById('edit-fournisseur-id').value       = data.id;
    document.getElementById('edit-fournisseur-nom').value      = data.nom || '';
    document.getElementById('edit-fournisseur-contact').value  = data.contact_principal || '';
    document.getElementById('edit-fournisseur-email').value    = data.email || '';
    document.getElementById('edit-fournisseur-telephone').value= data.telephone || '';
    document.getElementById('edit-fournisseur-adresse').value  = data.adresse || '';
    document.getElementById('edit-fournisseur-ville').value    = data.ville || '';
    openModal('modal-edit-fournisseur');
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

async function loadContacts() {
    const params = new URLSearchParams();
    const type   = document.getElementById('contact-filter-type')?.value;
    const search = document.getElementById('contact-search')?.value;
    if (type)   params.set('type', type);
    if (search) params.set('search', search);
    try {
        const data = await apiFetch('/contact?' + params);
        _cache.contacts = data.list || [];
        const tbody = document.getElementById('contacts-tbody');
        tbody.innerHTML = _cache.contacts.map(c => `
            <tr>
                <td>${c.id}</td>
                <td>${c.nom || '-'}</td>
                <td>${c.prenom || '-'}</td>
                <td>${c.fonction || '-'}</td>
                <td>${badge(c.type)}</td>
                <td>${c.telephone || '-'}</td>
                <td>${c.email || '-'}</td>
                <td>${c.organisation || c.service_nom || '-'}</td>
                <td style="white-space:nowrap;">
                    <button class="btn btn-warning btn-sm" onclick="editContact(${c.id})">Éditer</button>
                    <button class="btn btn-danger btn-sm" onclick="deleteContact(${c.id})">Suppr.</button>
                </td>
            </tr>`).join('');
    } catch (e) { showMsg('Erreur chargement contacts', false); }
}

async function addContact() {
    const body = {
        nom:          document.getElementById('contact-nom').value,
        prenom:       document.getElementById('contact-prenom').value,
        fonction:     document.getElementById('contact-fonction').value,
        type:         document.getElementById('contact-type').value,
        telephone:    document.getElementById('contact-telephone').value,
        email:        document.getElementById('contact-email').value,
        organisation: document.getElementById('contact-organisation').value,
    };
    if (!body.nom) { showMsg('Le nom est obligatoire', false); return; }
    try {
        const res = await apiFetch('/contact', { method: 'POST', body: JSON.stringify(body) });
        if (res.success) { showMsg('Contact ajouté'); loadContacts(); }
        else showMsg(res.error || 'Erreur', false);
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
    openModal('modal-edit-contact');
}

async function saveContact() {
    const id = document.getElementById('edit-contact-id').value;
    const body = {
        nom:          document.getElementById('edit-contact-nom').value,
        prenom:       document.getElementById('edit-contact-prenom').value,
        fonction:     document.getElementById('edit-contact-fonction').value,
        type:         document.getElementById('edit-contact-type').value || null,
        telephone:    document.getElementById('edit-contact-telephone').value,
        email:        document.getElementById('edit-contact-email').value,
        organisation: document.getElementById('edit-contact-organisation').value,
    };
    if (!body.nom) { showMsg('Le nom est obligatoire', false); return; }
    try {
        const res = await apiFetch(`/contact/${id}`, { method: 'PUT', body: JSON.stringify(body) });
        if (res.success) { showMsg('Contact mis à jour'); closeModal('modal-edit-contact'); loadContacts(); }
        else showMsg(res.error || 'Erreur', false);
    } catch (e) { showMsg(e.message, false); }
}

// ─── SERVICES / ORGANISATION ───────────────────────────────

async function loadServices() {
    try {
        const data = await apiFetch('/service_org');
        const tbody = document.getElementById('services-tbody');
        tbody.innerHTML = (data.list || []).map(s => `
            <tr>
                <td>${s.id}</td>
                <td><strong>${s.code || '-'}</strong></td>
                <td>${s.nom || '-'}</td>
                <td>${s.responsable_nom || '-'}</td>
                <td>${s.parent_nom || '-'}</td>
                <td>${s.nb_projets || 0}</td>
                <td>
                    <button class="btn btn-danger btn-sm" onclick="deleteService(${s.id})">Suppr.</button>
                </td>
            </tr>`).join('');
    } catch (e) { showMsg('Erreur chargement services', false); }
}

async function addService() {
    const body = {
        code: document.getElementById('service-code').value,
        nom:  document.getElementById('service-nom').value,
    };
    if (!body.nom) { showMsg('Le nom est obligatoire', false); return; }
    try {
        const res = await apiFetch('/service_org', { method: 'POST', body: JSON.stringify(body) });
        if (res.success) { showMsg('Service ajouté'); loadServices(); }
        else showMsg(res.error || 'Erreur', false);
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

// ─── ETP ───────────────────────────────────────────────────

async function loadETP() {
    try {
        const data = await apiFetch('/etp');
        const kpiEl = document.getElementById('etp-kpi-bar');
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
        // Peupler select service
        const sel = document.getElementById('edit-user-service');
        sel.innerHTML = '<option value="">Aucun (accès global)</option>' +
            _adminServicesCache.map(s =>
                `<option value="${s.id}" ${u.service_id === s.id ? 'selected' : ''}>${s.nom}</option>`
            ).join('');
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

function _populateNewUserServiceSelect() {
    const sel = document.getElementById('new-user-service');
    if (!sel) return;
    sel.innerHTML = '<option value="">Aucun (accès global)</option>' +
        _adminServicesCache.map(s => `<option value="${s.id}">${s.nom}</option>`).join('');
}


// ─── INIT ──────────────────────────────────────────────────

document.getElementById('header-date').textContent =
    new Date().toLocaleDateString('fr-FR', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

// ─── Équipe projet ───────────────────────────────────────────────────────────
function showAddMembreForm(projetId) {
    const form = document.getElementById(`add-membre-form-${projetId}`);
    if (!form) return;
    form.style.display = form.style.display === 'none' ? '' : 'none';
    if (form.style.display !== 'none') {
        const input = document.getElementById(`new-membre-label-${projetId}`);
        if (input) { input.value = ''; input.focus(); }
    }
}

async function saveMembreEquipe(projetId) {
    const input = document.getElementById(`new-membre-label-${projetId}`);
    const label = input?.value?.trim();
    if (!label) { if (input) input.focus(); return; }
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
