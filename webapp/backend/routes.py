import functools
import time
from collections import defaultdict
from flask import Blueprint, jsonify, request, g

from app.services.projet_service import ProjetService
from app.services.budget_v5_service import BudgetV5Service
from app.services.bon_commande_service import BonCommandeService
from app.services.contrat_service import ContratService
from app.services.tache_service import TacheService
from app.services.referentiel_service import ReferentielService
from app.services.contact_service import ContactService
from app.services.service_org_service import ServiceOrgService
from app.services.auth_service import AuthService

routes = Blueprint('routes', __name__)

projet_service      = ProjetService()
budget_service      = BudgetV5Service()
bc_service          = BonCommandeService()
contrat_service     = ContratService()
referentiel_service = ReferentielService()
tache_service       = TacheService()
contact_service     = ContactService()
service_org_service = ServiceOrgService()
auth_service        = AuthService()


# ─────────────────────────────────────────────
# DECORATOR AUTH
# ─────────────────────────────────────────────

def require_auth(*roles):
    """
    @require_auth()                      → tout utilisateur authentifié
    @require_auth('admin')               → admin seulement
    @require_auth('admin','gestionnaire')→ admin ou gestionnaire
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return jsonify({"error": "Token manquant"}), 401
            payload = auth_service.verify_token(auth_header[7:])
            if not payload:
                return jsonify({"error": "Token invalide ou expiré"}), 401
            if roles and payload.get('role') not in roles:
                return jsonify({"error": "Accès interdit"}), 403
            # Vérifier que le compte est toujours actif en base
            try:
                user_row = auth_service.db.fetch_one(
                    "SELECT actif FROM utilisateurs WHERE id=%s", [payload.get('sub')]
                )
                if not user_row or not user_row.get('actif'):
                    return jsonify({"error": "Compte désactivé"}), 401
            except Exception:
                pass  # DB temporairement indisponible : on accepte le token JWT
            g.user = payload
            return f(*args, **kwargs)
        return wrapper
    return decorator


# ─────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────

# Rate limiting — max 10 tentatives par fenêtre de 5 min par IP
_login_attempts: dict = defaultdict(list)
_LOGIN_WINDOW   = 300   # secondes
_LOGIN_MAX      = 10    # tentatives max

def _check_login_rate(ip: str) -> bool:
    now = time.time()
    _login_attempts[ip] = [t for t in _login_attempts[ip] if now - t < _LOGIN_WINDOW]
    if len(_login_attempts[ip]) >= _LOGIN_MAX:
        return False
    _login_attempts[ip].append(now)
    return True

@routes.route('/auth/login', methods=['POST'])
def login():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()
    if not _check_login_rate(ip):
        return jsonify({"error": "Trop de tentatives, réessayez dans quelques minutes"}), 429
    data = request.json or {}
    result = auth_service.login(data.get('login', ''), data.get('password', ''))
    if not result:
        return jsonify({"error": "Identifiants invalides ou compte désactivé"}), 401
    return jsonify(result)

@routes.route('/auth/me', methods=['GET'])
@require_auth()
def me():
    return jsonify(g.user)


# ─────────────────────────────────────────────
# USERS (admin)
# ─────────────────────────────────────────────

@routes.route('/users', methods=['GET'])
@require_auth('admin')
def get_users():
    return jsonify({"list": auth_service.get_all_users()})

@routes.route('/users', methods=['POST'])
@require_auth('admin')
def create_user():
    data = request.json or {}
    try:
        if not data.get('login') or not data.get('mot_de_passe'):
            return jsonify({"error": "login et mot_de_passe requis"}), 400
        auth_service.create_user(data)
        return jsonify({"success": True}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@routes.route('/users/<int:user_id>', methods=['GET'])
@require_auth('admin')
def get_user(user_id):
    user = auth_service.get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "Utilisateur introuvable"}), 404
    return jsonify(user)

@routes.route('/users/<int:user_id>', methods=['PUT'])
@require_auth('admin')
def update_user(user_id):
    data = request.json or {}
    try:
        auth_service.update_user(user_id, data)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@routes.route('/users/<int:user_id>', methods=['DELETE'])
@require_auth('admin')
def delete_user(user_id):
    try:
        if g.user.get('sub') == user_id:
            return jsonify({"error": "Impossible de supprimer son propre compte"}), 400
        auth_service.delete_user(user_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@routes.route('/users/<int:user_id>/toggle', methods=['POST'])
@require_auth('admin')
def toggle_user(user_id):
    data = request.json or {}
    try:
        auth_service.set_active(user_id, data.get('actif', True))
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────

@routes.route('/dashboard', methods=['GET'])
@require_auth()
def dashboard():
    projets       = projet_service.get_all()
    budget        = budget_service.get_budget()
    bons_commande = bc_service.get_all_bons_commande()
    contrats      = contrat_service.get_all()
    alertes       = contrat_service.get_alertes()
    bc_attente    = [b for b in bons_commande if b.get('statut') in ('BROUILLON', 'EN_ATTENTE')]
    return jsonify({
        "kpi_projets":       len(projets),
        "kpi_budget":        sum(b.get('montant_vote', 0) or 0 for b in budget),
        "kpi_bons_commande": len(bons_commande),
        "kpi_montant_bc":    sum(b.get('montant_ttc', 0) or 0 for b in bons_commande),
        "kpi_contrats":      len([c for c in contrats if c.get('statut') == 'ACTIF']),
        "kpi_alertes_contrats": len(alertes),
        "kpi_bc_attente":    len(bc_attente),
        "alertes_contrats":  alertes[:5],
    })


# ─────────────────────────────────────────────
# ENTITÉS
# ─────────────────────────────────────────────

@routes.route('/entites', methods=['GET'])
@require_auth()
def get_entites():
    return jsonify({"list": budget_service.get_entites()})


# ─────────────────────────────────────────────
# APPLICATIONS
# ─────────────────────────────────────────────

@routes.route('/applications', methods=['GET'])
@require_auth()
def get_applications():
    return jsonify({"list": budget_service.get_all_applications()})


# ─────────────────────────────────────────────
# BUDGETS ANNUELS — avec contrôle d'accès explicite
# ─────────────────────────────────────────────

def _user_budget_role(user_id, budget_id):
    """Retourne le rôle de l'utilisateur sur ce budget ('lecteur'/'gestionnaire'), ou None."""
    row = budget_service.db.fetch_one(
        "SELECT role FROM budget_permissions WHERE budget_id=%s AND user_id=%s",
        [budget_id, user_id]
    )
    return row['role'] if row else None


@routes.route('/budget', methods=['GET'])
@require_auth()
def get_budget():
    user_id = g.user.get('sub')
    role    = g.user.get('role')
    if role == 'admin':
        budgets = budget_service.get_budget()
        for b in budgets:
            b['user_perm'] = 'gestionnaire'
    else:
        rows = budget_service.db.fetch_all(
            "SELECT ba.*, e.code as entite_code, e.nom as entite_nom, bp.role as user_perm "
            "FROM budgets_annuels ba "
            "LEFT JOIN entites e ON e.id = ba.entite_id "
            "JOIN budget_permissions bp ON bp.budget_id = ba.id AND bp.user_id = %s "
            "ORDER BY ba.exercice DESC, ba.nature",
            [user_id]
        )
        budgets = [dict(b) for b in (rows or [])]
    return jsonify({
        "total_vote":   sum(b.get('montant_vote', 0) or 0 for b in budgets),
        "total_engage": sum(b.get('montant_engage', 0) or 0 for b in budgets),
        "details": budgets
    })


@routes.route('/budget/<int:budget_id>/lignes', methods=['GET'])
@require_auth()
def get_lignes_budget(budget_id):
    user_id = g.user.get('sub')
    role    = g.user.get('role')
    if role != 'admin' and _user_budget_role(user_id, budget_id) is None:
        return jsonify({"error": "Accès interdit à ce budget"}), 403
    return jsonify({"list": budget_service.get_lignes(budget_id)})


@routes.route('/lignes', methods=['GET'])
@require_auth()
def get_all_lignes():
    user_id   = g.user.get('sub')
    role      = g.user.get('role')
    budget_id = request.args.get('budget_id', type=int)
    if budget_id:
        if role != 'admin' and _user_budget_role(user_id, budget_id) is None:
            return jsonify({"list": []})
        return jsonify({"list": budget_service.get_lignes(budget_id)})
    if role == 'admin':
        rows = budget_service.db.fetch_all(
            "SELECT l.*, ba.exercice, ba.nature, "
            "e.code as entite_code, e.nom as entite_nom, "
            "CONCAT(e.code, ' — ', ba.nature, ' ', ba.exercice) as budget_label, "
            "app.nom as application_nom, f.nom as fournisseur_nom, "
            "CASE WHEN l.montant_vote > 0 "
            "THEN ROUND((COALESCE(l.montant_engage,0)/l.montant_vote*100)::numeric, 1) "
            "ELSE 0 END as taux_engagement, "
            "CASE WHEN l.montant_vote > 0 AND COALESCE(l.montant_engage,0) >= l.montant_vote * "
            "COALESCE(l.seuil_alerte_pct,80)/100.0 THEN true ELSE false END as alerte "
            "FROM lignes_budgetaires l "
            "JOIN budgets_annuels ba ON ba.id = l.budget_id "
            "LEFT JOIN entites e ON e.id = ba.entite_id "
            "LEFT JOIN applications app ON app.id = l.application_id "
            "LEFT JOIN fournisseurs f ON f.id = l.fournisseur_id "
            "ORDER BY l.id"
        )
    else:
        rows = budget_service.db.fetch_all(
            "SELECT l.*, ba.exercice, ba.nature, "
            "e.code as entite_code, e.nom as entite_nom, "
            "CONCAT(e.code, ' — ', ba.nature, ' ', ba.exercice) as budget_label, "
            "app.nom as application_nom, f.nom as fournisseur_nom, "
            "CASE WHEN l.montant_vote > 0 "
            "THEN ROUND((COALESCE(l.montant_engage,0)/l.montant_vote*100)::numeric, 1) "
            "ELSE 0 END as taux_engagement, "
            "CASE WHEN l.montant_vote > 0 AND COALESCE(l.montant_engage,0) >= l.montant_vote * "
            "COALESCE(l.seuil_alerte_pct,80)/100.0 THEN true ELSE false END as alerte "
            "FROM lignes_budgetaires l "
            "JOIN budgets_annuels ba ON ba.id = l.budget_id "
            "LEFT JOIN entites e ON e.id = ba.entite_id "
            "LEFT JOIN applications app ON app.id = l.application_id "
            "LEFT JOIN fournisseurs f ON f.id = l.fournisseur_id "
            "JOIN budget_permissions bp ON bp.budget_id = l.budget_id AND bp.user_id = %s "
            "ORDER BY l.id",
            [user_id]
        )
    return jsonify({"list": [dict(r) for r in (rows or [])]})


@routes.route('/ligne', methods=['POST'])
@require_auth('admin', 'gestionnaire')
def create_ligne():
    data    = request.json
    user_id = g.user.get('sub')
    role    = g.user.get('role')
    bid     = data.get('budget_id')
    if role != 'admin' and _user_budget_role(user_id, bid) != 'gestionnaire':
        return jsonify({"error": "Droits insuffisants sur ce budget"}), 403
    try:
        vote = float(data.get('montant_vote') or 0)
        budget_service.db.execute(
            "INSERT INTO lignes_budgetaires "
            "(budget_id, libelle, application_id, fournisseur_id, "
            "montant_prevu, montant_vote, montant_solde, nature, note, statut) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            [bid, data.get('libelle'),
             data.get('application_id') or None, data.get('fournisseur_id') or None,
             float(data.get('montant_prevu') or 0), vote, vote,
             data.get('nature') or 'FONCTIONNEMENT',
             data.get('note') or None, data.get('statut') or 'ACTIF']
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@routes.route('/ligne/<int:ligne_id>', methods=['PUT'])
@require_auth('admin', 'gestionnaire')
def update_ligne(ligne_id):
    data    = request.json
    user_id = g.user.get('sub')
    role    = g.user.get('role')
    bid     = data.get('budget_id')
    if role != 'admin' and _user_budget_role(user_id, bid) != 'gestionnaire':
        return jsonify({"error": "Droits insuffisants sur ce budget"}), 403
    try:
        vote = float(data.get('montant_vote') or 0)
        budget_service.db.execute(
            "UPDATE lignes_budgetaires SET "
            "budget_id=%s, libelle=%s, application_id=%s, fournisseur_id=%s, "
            "montant_prevu=%s, montant_vote=%s, "
            "montant_solde=GREATEST(%s - COALESCE(montant_engage, 0), 0), "
            "nature=%s, note=%s, statut=%s, date_maj=NOW() WHERE id=%s",
            [bid, data.get('libelle'),
             data.get('application_id') or None, data.get('fournisseur_id') or None,
             float(data.get('montant_prevu') or 0), vote, vote,
             data.get('nature') or 'FONCTIONNEMENT',
             data.get('note') or None, data.get('statut') or 'ACTIF', ligne_id]
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@routes.route('/ligne/<int:ligne_id>/bcs', methods=['GET'])
@require_auth()
def get_ligne_bcs(ligne_id):
    user_id = g.user.get('sub')
    role    = g.user.get('role')
    if role != 'admin':
        row = budget_service.db.fetch_one(
            "SELECT l.budget_id FROM lignes_budgetaires l WHERE l.id=%s", [ligne_id]
        )
        if not row or _user_budget_role(user_id, row['budget_id']) is None:
            return jsonify({"bcs": []})
    bcs = budget_service.db.fetch_all(
        "SELECT bc.id, bc.numero_bc, bc.objet, bc.montant_ht, bc.montant_ttc, "
        "bc.statut, bc.date_creation, bc.date_imputation, bc.date_solde, "
        "f.nom as fournisseur_nom, "
        "c.numero_contrat as contrat_numero, c.objet as contrat_objet, "
        "p.nom as projet_nom "
        "FROM bons_commande bc "
        "LEFT JOIN fournisseurs f ON f.id = bc.fournisseur_id "
        "LEFT JOIN contrats c ON c.id = bc.contrat_id "
        "LEFT JOIN projets p ON p.id = bc.projet_id "
        "WHERE bc.ligne_budgetaire_id = %s ORDER BY bc.date_creation DESC",
        [ligne_id]
    )
    return jsonify({"bcs": [dict(b) for b in bcs] if bcs else []})


@routes.route('/budget/<int:budget_id>/detail', methods=['GET'])
@require_auth()
def get_budget_detail(budget_id):
    user_id = g.user.get('sub')
    role    = g.user.get('role')
    if role != 'admin' and _user_budget_role(user_id, budget_id) is None:
        return jsonify({"error": "Accès interdit à ce budget"}), 403
    lignes = budget_service.get_lignes(budget_id)
    for ligne in lignes:
        bcs = budget_service.db.fetch_all(
            "SELECT bc.id, bc.numero_bc, bc.objet, bc.montant_ht, bc.montant_ttc, "
            "bc.statut, bc.date_creation, f.nom as fournisseur_nom, "
            "c.numero_contrat as contrat_numero, c.objet as contrat_objet "
            "FROM bons_commande bc "
            "LEFT JOIN fournisseurs f ON f.id = bc.fournisseur_id "
            "LEFT JOIN contrats c ON c.id = bc.contrat_id "
            "WHERE bc.ligne_budgetaire_id = %s ORDER BY bc.date_creation DESC",
            [ligne['id']]
        )
        ligne['bons_commande'] = [dict(b) for b in bcs] if bcs else []
    return jsonify({"lignes": lignes})


@routes.route('/budget/<int:budget_id>/voter', methods=['POST'])
@require_auth('admin', 'gestionnaire')
def voter_budget(budget_id):
    user_id = g.user.get('sub')
    role    = g.user.get('role')
    if role != 'admin' and _user_budget_role(user_id, budget_id) != 'gestionnaire':
        return jsonify({"error": "Droits insuffisants sur ce budget"}), 403
    data = request.json
    try:
        montant_vote = float(data.get('montant_vote') or 0)
        budget_service.voter_budget(budget_id, montant_vote)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@routes.route('/budget', methods=['POST'])
@require_auth('admin', 'gestionnaire')
def create_budget():
    data    = request.json
    user_id = g.user.get('sub')
    role    = g.user.get('role')
    try:
        row = budget_service.db.execute_returning(
            "INSERT INTO budgets_annuels (entite_id, exercice, nature, montant_previsionnel, statut) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING id",
            [data.get('entite_id') or None, data.get('exercice'), data.get('nature'),
             data.get('montant_previsionnel') or 0, data.get('statut', 'BROUILLON')]
        )
        new_id = row[0] if row else None
        if new_id and role != 'admin':
            budget_service.db.execute(
                "INSERT INTO budget_permissions (budget_id, user_id, role) "
                "VALUES (%s, %s, 'gestionnaire') ON CONFLICT DO NOTHING",
                [new_id, user_id]
            )
        return jsonify({"success": True}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@routes.route('/budget/<int:budget_id>', methods=['PUT'])
@require_auth('admin', 'gestionnaire')
def update_budget(budget_id):
    user_id = g.user.get('sub')
    role    = g.user.get('role')
    if role != 'admin' and _user_budget_role(user_id, budget_id) != 'gestionnaire':
        return jsonify({"error": "Droits insuffisants sur ce budget"}), 403
    data = request.json
    try:
        budget_service.db.execute(
            "UPDATE budgets_annuels SET entite_id=%s, exercice=%s, nature=%s, "
            "montant_previsionnel=%s, montant_vote=%s, statut=%s, date_maj=NOW() WHERE id=%s",
            [data.get('entite_id') or None, data.get('exercice'), data.get('nature'),
             data.get('montant_previsionnel') or 0, data.get('montant_vote') or 0,
             data.get('statut'), budget_id]
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@routes.route('/budget/<int:budget_id>', methods=['DELETE'])
@require_auth('admin')
def delete_budget(budget_id):
    try:
        budget_service.db.execute("DELETE FROM budgets_annuels WHERE id=%s", [budget_id])
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ─── Gestion des permissions budget ───────────────────────────────────────────

@routes.route('/budget/<int:budget_id>/permissions', methods=['GET'])
@require_auth()
def get_budget_permissions(budget_id):
    user_id = g.user.get('sub')
    role    = g.user.get('role')
    if role != 'admin' and _user_budget_role(user_id, budget_id) != 'gestionnaire':
        return jsonify({"error": "Accès interdit"}), 403
    rows = budget_service.db.fetch_all(
        "SELECT bp.id, bp.user_id, bp.role, bp.date_creation, "
        "u.nom, u.prenom, u.login, s.nom as service_nom "
        "FROM budget_permissions bp "
        "JOIN utilisateurs u ON u.id = bp.user_id "
        "LEFT JOIN services s ON s.id = u.service_id "
        "WHERE bp.budget_id = %s ORDER BY u.nom, u.prenom",
        [budget_id]
    )
    return jsonify({"list": [dict(r) for r in (rows or [])]})


@routes.route('/budget/<int:budget_id>/permissions', methods=['POST'])
@require_auth()
def add_budget_permission(budget_id):
    user_id = g.user.get('sub')
    role    = g.user.get('role')
    if role != 'admin' and _user_budget_role(user_id, budget_id) != 'gestionnaire':
        return jsonify({"error": "Accès interdit"}), 403
    data = request.json or {}
    perm_role = data.get('role', 'lecteur')
    if perm_role not in ('lecteur', 'gestionnaire'):
        return jsonify({"error": "Rôle invalide — valeurs acceptées : lecteur, gestionnaire"}), 400
    target_uid = data.get('user_id')
    if not target_uid or not str(target_uid).isdigit():
        return jsonify({"error": "user_id invalide"}), 400
    try:
        budget_service.db.execute(
            "INSERT INTO budget_permissions (budget_id, user_id, role) VALUES (%s, %s, %s) "
            "ON CONFLICT (budget_id, user_id) DO UPDATE SET role = EXCLUDED.role",
            [budget_id, int(target_uid), perm_role]
        )
        return jsonify({"success": True}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@routes.route('/budget/<int:budget_id>/permissions/<int:target_uid>', methods=['DELETE'])
@require_auth()
def delete_budget_permission(budget_id, target_uid):
    user_id = g.user.get('sub')
    role    = g.user.get('role')
    if role != 'admin' and _user_budget_role(user_id, budget_id) != 'gestionnaire':
        return jsonify({"error": "Accès interdit"}), 403
    try:
        budget_service.db.execute(
            "DELETE FROM budget_permissions WHERE budget_id=%s AND user_id=%s",
            [budget_id, target_uid]
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ─────────────────────────────────────────────
# BONS DE COMMANDE  — filtre par propriétaire
# ─────────────────────────────────────────────

def _ownership_where(user_id, role, service_id, alias='bc'):
    """
    Retourne (clause WHERE, params) pour filtrer par propriétaire.
    - admin        → voit tout
    - gestionnaire → voit les siens + tous les membres de son service/unité
    - lecteur      → voit uniquement les siens
    Les enregistrements sans created_by_id (NULL = données historiques)
    sont visibles uniquement par admin. Les non-admins ne voient QUE
    les enregistrements avec un created_by_id explicite.
    """
    p = alias + '.'
    if role == 'admin':
        return "1=1", []
    elif role == 'gestionnaire' and service_id:
        # Chef de service : voit tous les membres de son service/unité
        return (
            f"({p}created_by_id = %s "
            f"OR {p}created_by_id IN "
            f"(SELECT id FROM utilisateurs WHERE service_id = %s AND actif = true))",
            [user_id, service_id]
        )
    else:
        # lecteur (ou gestionnaire sans service) : uniquement les siens
        return f"{p}created_by_id = %s", [user_id]


@routes.route('/bon_commande', methods=['GET'])
@require_auth()
def get_bon_commande():
    user_id    = g.user.get('sub')
    role       = g.user.get('role')
    service_id = g.user.get('service_id')
    filters    = {k: v for k, v in request.args.items() if v}

    if role == 'admin':
        bc_list = bc_service.get_all_bons_commande(filters)
    else:
        # Récupérer tous les BCs accessibles puis appliquer filtres supplémentaires
        where, params = _ownership_where(user_id, role, service_id, 'bc')
        extra_where = [where]
        extra_params = list(params)
        if filters.get('statut'):
            extra_where.append("bc.statut = %s")
            extra_params.append(filters['statut'])
        if filters.get('entite_id'):
            extra_where.append("bc.entite_id = %s")
            extra_params.append(filters['entite_id'])
        rows = bc_service.db.fetch_all(
            "SELECT bc.*, f.nom as fournisseur_nom, e.code as entite_code, "
            "e.nom as entite_nom, p.nom as projet_nom, c.numero_contrat, "
            "u.nom || ' ' || COALESCE(u.prenom,'') as createur_nom "
            "FROM bons_commande bc "
            "LEFT JOIN fournisseurs f ON f.id = bc.fournisseur_id "
            "LEFT JOIN entites e ON e.id = bc.entite_id "
            "LEFT JOIN projets p ON p.id = bc.projet_id "
            "LEFT JOIN contrats c ON c.id = bc.contrat_id "
            "LEFT JOIN utilisateurs u ON u.id = bc.created_by_id "
            f"WHERE {' AND '.join(extra_where)} ORDER BY bc.date_creation DESC",
            extra_params
        )
        bc_list = [dict(r) for r in (rows or [])]
    return jsonify({"count": len(bc_list), "list": bc_list})


@routes.route('/bon_commande/stats', methods=['GET'])
@require_auth()
def get_bc_stats():
    user_id    = g.user.get('sub')
    role       = g.user.get('role')
    service_id = g.user.get('service_id')
    if role == 'admin':
        return jsonify(bc_service.get_stats())
    where, params = _ownership_where(user_id, role, service_id, 'bc')
    row = bc_service.db.fetch_one(
        f"SELECT COUNT(*) as total, "
        f"SUM(CASE WHEN bc.statut='BROUILLON' THEN 1 ELSE 0 END) as brouillon, "
        f"SUM(CASE WHEN bc.statut='VALIDE' THEN 1 ELSE 0 END) as valide, "
        f"SUM(CASE WHEN bc.statut='SOLDE' THEN 1 ELSE 0 END) as solde, "
        f"COALESCE(SUM(bc.montant_ht),0) as total_ht "
        f"FROM bons_commande bc WHERE {where}",
        params
    )
    return jsonify(dict(row) if row else {})


@routes.route('/bon_commande/<int:bc_id>', methods=['GET'])
@require_auth()
def get_bon_commande_by_id(bc_id):
    user_id    = g.user.get('sub')
    role       = g.user.get('role')
    service_id = g.user.get('service_id')
    bc = bc_service.get_by_id(bc_id)
    if not bc:
        return jsonify({"error": "BC introuvable"}), 404
    if role != 'admin':
        creator = bc.get('created_by_id')
        if creator is not None:
            where, params = _ownership_where(user_id, role, service_id, 'bc')
            row = bc_service.db.fetch_one(
                f"SELECT id FROM bons_commande bc WHERE bc.id=%s AND {where}",
                [bc_id] + params
            )
            if not row:
                return jsonify({"error": "Accès interdit"}), 403
    return jsonify(bc)


@routes.route('/bon_commande/<int:bc_id>/valider', methods=['POST'])
@require_auth('admin', 'gestionnaire')
def valider_bc(bc_id):
    try:
        new_statut = bc_service.valider(bc_id)
        return jsonify({"success": True, "statut": new_statut})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@routes.route('/bon_commande/<int:bc_id>/imputer', methods=['POST'])
@require_auth('admin', 'gestionnaire')
def imputer_bc(bc_id):
    data = request.json
    ligne_id = data.get('ligne_id')
    if not ligne_id:
        return jsonify({"success": False, "error": "ligne_id requis"}), 400
    try:
        bc_service.imputer(bc_id, ligne_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@routes.route('/bon_commande', methods=['POST'])
@require_auth('admin', 'gestionnaire')
def create_bon_commande():
    data    = request.json
    user_id = g.user.get('sub')
    try:
        montant_ht  = float(data.get('montant_ht') or 0)
        montant_ttc = float(data.get('montant_ttc') or montant_ht * 1.2)
        bc_service.db.execute(
            "INSERT INTO bons_commande (numero_bc, objet, fournisseur_id, entite_id, "
            "projet_id, ligne_budgetaire_id, contrat_id, montant_ht, montant_ttc, statut, created_by_id) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            [data.get('numero_bc'), data.get('objet'), data.get('fournisseur_id') or None,
             data.get('entite_id') or None, data.get('projet_id') or None,
             data.get('ligne_budgetaire_id') or None, data.get('contrat_id') or None,
             montant_ht, montant_ttc, data.get('statut', 'BROUILLON'), user_id]
        )
        return jsonify({"success": True}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@routes.route('/bon_commande/<int:bc_id>', methods=['PUT'])
@require_auth('admin', 'gestionnaire')
def update_bon_commande(bc_id):
    data       = request.json
    user_id    = g.user.get('sub')
    role       = g.user.get('role')
    service_id = g.user.get('service_id')
    if role != 'admin':
        where, params = _ownership_where(user_id, role, service_id, 'bc')
        row = bc_service.db.fetch_one(
            f"SELECT id FROM bons_commande bc WHERE bc.id=%s AND {where}", [bc_id] + params
        )
        if not row:
            return jsonify({"error": "Accès interdit"}), 403
    try:
        montant_ht  = float(data.get('montant_ht') or 0)
        montant_ttc = float(data.get('montant_ttc') or montant_ht * 1.2)
        bc_service.db.execute(
            "UPDATE bons_commande SET numero_bc=%s, objet=%s, fournisseur_id=%s, "
            "entite_id=%s, projet_id=%s, ligne_budgetaire_id=%s, contrat_id=%s, "
            "montant_ht=%s, montant_ttc=%s, statut=%s, date_maj=NOW() WHERE id=%s",
            [data.get('numero_bc'), data.get('objet'), data.get('fournisseur_id') or None,
             data.get('entite_id') or None, data.get('projet_id') or None,
             data.get('ligne_budgetaire_id') or None, data.get('contrat_id') or None,
             montant_ht, montant_ttc, data.get('statut'), bc_id]
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@routes.route('/bon_commande/<int:bc_id>', methods=['DELETE'])
@require_auth('admin', 'gestionnaire')
def delete_bon_commande(bc_id):
    user_id    = g.user.get('sub')
    role       = g.user.get('role')
    service_id = g.user.get('service_id')
    if role != 'admin':
        where, params = _ownership_where(user_id, role, service_id, 'bc')
        row = bc_service.db.fetch_one(
            f"SELECT id FROM bons_commande bc WHERE bc.id=%s AND {where}", [bc_id] + params
        )
        if not row:
            return jsonify({"error": "Accès interdit"}), 403
    try:
        bc_service.db.execute("DELETE FROM bons_commande WHERE id=%s", [bc_id])
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ─────────────────────────────────────────────
# CONTRATS — filtre par propriétaire
# ─────────────────────────────────────────────

@routes.route('/contrat', methods=['GET'])
@require_auth()
def get_contrats():
    user_id    = g.user.get('sub')
    role       = g.user.get('role')
    service_id = g.user.get('service_id')
    if role == 'admin':
        contrats = contrat_service.get_all()
    else:
        where, params = _ownership_where(user_id, role, service_id, 'c')
        rows = contrat_service.db.fetch_all(
            "SELECT c.*, f.nom as fournisseur_nom, "
            "u.nom || ' ' || COALESCE(u.prenom,'') as createur_nom "
            "FROM contrats c "
            "LEFT JOIN fournisseurs f ON f.id = c.fournisseur_id "
            "LEFT JOIN utilisateurs u ON u.id = c.created_by_id "
            f"WHERE {where} ORDER BY c.date_creation DESC",
            params
        )
        contrats = [dict(r) for r in (rows or [])]
    return jsonify({"count": len(contrats), "list": contrats})


@routes.route('/contrat/<int:contrat_id>', methods=['GET'])
@require_auth()
def get_contrat_by_id(contrat_id):
    user_id    = g.user.get('sub')
    role       = g.user.get('role')
    service_id = g.user.get('service_id')
    c = contrat_service.get_by_id(contrat_id)
    if not c:
        return jsonify({"error": "Contrat introuvable"}), 404
    if role != 'admin' and c.get('created_by_id') is not None:
        where, params = _ownership_where(user_id, role, service_id, 'c')
        row = contrat_service.db.fetch_one(
            f"SELECT id FROM contrats c WHERE c.id=%s AND {where}", [contrat_id] + params
        )
        if not row:
            return jsonify({"error": "Accès interdit"}), 403
    return jsonify(c)


@routes.route('/contrat/alertes', methods=['GET'])
@require_auth()
def get_contrat_alertes():
    user_id    = g.user.get('sub')
    role       = g.user.get('role')
    service_id = g.user.get('service_id')
    if role == 'admin':
        return jsonify({"list": contrat_service.get_alertes()})
    where, params = _ownership_where(user_id, role, service_id, 'c')
    rows = contrat_service.db.fetch_all(
        "SELECT c.*, f.nom as fournisseur_nom FROM contrats c "
        "LEFT JOIN fournisseurs f ON f.id = c.fournisseur_id "
        f"WHERE c.date_fin IS NOT NULL AND c.date_fin <= NOW() + INTERVAL '60 days' AND {where} "
        "ORDER BY c.date_fin",
        params
    )
    return jsonify({"list": [dict(r) for r in (rows or [])]})


@routes.route('/contrat/<int:contrat_id>/reconduire', methods=['POST'])
@require_auth('admin', 'gestionnaire')
def reconduire_contrat(contrat_id):
    user_id    = g.user.get('sub')
    role       = g.user.get('role')
    service_id = g.user.get('service_id')
    if role != 'admin':
        where, params = _ownership_where(user_id, role, service_id, 'c')
        row = contrat_service.db.fetch_one(
            f"SELECT id FROM contrats c WHERE c.id=%s AND {where}", [contrat_id] + params
        )
        if not row:
            return jsonify({"error": "Accès interdit"}), 403
    data = request.json
    nouvelle_date_fin = data.get('nouvelle_date_fin')
    if not nouvelle_date_fin:
        return jsonify({"success": False, "error": "nouvelle_date_fin requise"}), 400
    try:
        contrat_service.reconduire(contrat_id, nouvelle_date_fin)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@routes.route('/contrat', methods=['POST'])
@require_auth('admin', 'gestionnaire')
def create_contrat():
    data    = request.json
    user_id = g.user.get('sub')
    try:
        montant_ht = float(data.get('montant_total_ht') or 0)
        contrat_service.db.execute(
            "INSERT INTO contrats (numero_contrat, objet, fournisseur_id, montant_initial_ht, "
            "montant_total_ht, montant_ttc, date_debut, date_fin, statut, created_by_id) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            [data.get('numero_contrat'), data.get('objet'), data.get('fournisseur_id') or None,
             montant_ht, montant_ht, round(montant_ht * 1.2, 2),
             data.get('date_debut') or None, data.get('date_fin') or None,
             data.get('statut', 'ACTIF'), user_id]
        )
        return jsonify({"success": True}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@routes.route('/contrat/<int:contrat_id>', methods=['PUT'])
@require_auth('admin', 'gestionnaire')
def update_contrat(contrat_id):
    data       = request.json
    user_id    = g.user.get('sub')
    role       = g.user.get('role')
    service_id = g.user.get('service_id')
    if role != 'admin':
        where, params = _ownership_where(user_id, role, service_id, 'c')
        row = contrat_service.db.fetch_one(
            f"SELECT id FROM contrats c WHERE c.id=%s AND {where}", [contrat_id] + params
        )
        if not row:
            return jsonify({"error": "Accès interdit"}), 403
    try:
        montant_ht = float(data.get('montant_total_ht') or 0)
        contrat_service.db.execute(
            "UPDATE contrats SET numero_contrat=%s, objet=%s, fournisseur_id=%s, "
            "montant_total_ht=%s, montant_ttc=%s, date_debut=%s, date_fin=%s, "
            "statut=%s, date_maj=NOW() WHERE id=%s",
            [data.get('numero_contrat'), data.get('objet'), data.get('fournisseur_id') or None,
             montant_ht, round(montant_ht * 1.2, 2),
             data.get('date_debut') or None, data.get('date_fin') or None,
             data.get('statut'), contrat_id]
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@routes.route('/contrat/<int:contrat_id>', methods=['DELETE'])
@require_auth('admin', 'gestionnaire')
def delete_contrat(contrat_id):
    user_id    = g.user.get('sub')
    role       = g.user.get('role')
    service_id = g.user.get('service_id')
    if role != 'admin':
        where, params = _ownership_where(user_id, role, service_id, 'c')
        row = contrat_service.db.fetch_one(
            f"SELECT id FROM contrats c WHERE c.id=%s AND {where}", [contrat_id] + params
        )
        if not row:
            return jsonify({"error": "Accès interdit"}), 403
    try:
        contrat_service.db.execute("DELETE FROM contrats WHERE id=%s", [contrat_id])
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ─────────────────────────────────────────────
# PROJETS
# ─────────────────────────────────────────────

@routes.route('/projet', methods=['GET'])
@require_auth()
def get_projets():
    user_id    = g.user.get('sub')
    role       = g.user.get('role')
    service_id = g.user.get('service_id')
    filters    = request.args.to_dict()

    if role == 'admin':
        projets = projet_service.get_all(filters)
    else:
        where, params = _ownership_where(user_id, role, service_id, 'p')
        extra = []
        if filters.get('statut'):
            extra.append("p.statut = %s")
            params.append(filters['statut'])
        clause = f"({where})" + (" AND " + " AND ".join(extra) if extra else "")
        rows = projet_service.db.fetch_all(
            "SELECT p.*, s.nom as service_nom, s.code as service_code "
            "FROM projets p "
            "LEFT JOIN services s ON s.id = p.service_id "
            f"WHERE {clause} ORDER BY p.date_creation DESC",
            params
        )
        projets = [dict(r) for r in (rows or [])]
    return jsonify({"count": len(projets), "list": projets})


@routes.route('/projet/<int:projet_id>', methods=['GET'])
@require_auth()
def get_projet(projet_id):
    user_id    = g.user.get('sub')
    role       = g.user.get('role')
    service_id = g.user.get('service_id')
    p = projet_service.get_by_id(projet_id)
    if not p:
        return jsonify({"error": "Projet introuvable"}), 404
    if role != 'admin' and p.get('created_by_id') is not None:
        where, params = _ownership_where(user_id, role, service_id, 'p')
        row = projet_service.db.fetch_one(
            f"SELECT id FROM projets p WHERE p.id=%s AND {where}", [projet_id] + params
        )
        if not row:
            return jsonify({"error": "Accès interdit"}), 403
    return jsonify(p)

@routes.route('/projet', methods=['POST'])
@require_auth('admin', 'gestionnaire')
def create_projet():
    data    = request.json
    user_id = g.user.get('sub')
    try:
        projet_service.db.execute(
            "INSERT INTO projets (code, nom, description, statut, priorite, type_projet, phase, "
            "service_id, date_debut, date_fin_prevue, date_fin_reelle, "
            "budget_initial, budget_estime, budget_actuel, avancement, "
            "objectifs, enjeux, gains, risques, contraintes, solutions, created_by_id) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            [data.get('code'), data.get('nom'), data.get('description'), data.get('statut'),
             data.get('priorite'), data.get('type_projet') or None, data.get('phase') or None,
             data.get('service_id') or None,
             data.get('date_debut') or None, data.get('date_fin_prevue') or None,
             data.get('date_fin_reelle') or None,
             data.get('budget_initial') or None, data.get('budget_estime') or None,
             data.get('budget_actuel') or None, data.get('avancement') or 0,
             data.get('objectifs') or None, data.get('enjeux') or None,
             data.get('gains') or None, data.get('risques') or None,
             data.get('contraintes') or None, data.get('solutions') or None, user_id]
        )
        return jsonify({"success": True}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@routes.route('/projet/<int:projet_id>', methods=['PUT'])
@require_auth('admin', 'gestionnaire')
def update_projet(projet_id):
    data = request.json
    try:
        projet_service.db.execute(
            "UPDATE projets SET code=%s, nom=%s, description=%s, statut=%s, priorite=%s, "
            "type_projet=%s, phase=%s, service_id=%s, "
            "date_debut=%s, date_fin_prevue=%s, date_fin_reelle=%s, "
            "budget_initial=%s, budget_estime=%s, budget_actuel=%s, avancement=%s, "
            "objectifs=%s, enjeux=%s, gains=%s, risques=%s, contraintes=%s, solutions=%s, "
            "updated_at=NOW() WHERE id=%s",
            [data.get('code'), data.get('nom'), data.get('description'), data.get('statut'),
             data.get('priorite'), data.get('type_projet') or None, data.get('phase') or None,
             data.get('service_id') or None,
             data.get('date_debut') or None, data.get('date_fin_prevue') or None,
             data.get('date_fin_reelle') or None,
             data.get('budget_initial') or None, data.get('budget_estime') or None,
             data.get('budget_actuel') or None, data.get('avancement') or 0,
             data.get('objectifs') or None, data.get('enjeux') or None,
             data.get('gains') or None, data.get('risques') or None,
             data.get('contraintes') or None, data.get('solutions') or None,
             projet_id]
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@routes.route('/projet/<int:projet_id>', methods=['DELETE'])
@require_auth('admin')
def delete_projet(projet_id):
    try:
        projet_service.db.execute("DELETE FROM projets WHERE id=%s", [projet_id])
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@routes.route('/projet/<int:projet_id>/equipe', methods=['POST'])
@require_auth('admin', 'gestionnaire')
def add_projet_equipe(projet_id):
    data = request.json or {}
    try:
        projet_service.add_equipe_membre(
            projet_id,
            data.get('utilisateur_id') or None,
            data.get('membre_label') or None
        )
        return jsonify({"ok": True}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@routes.route('/projet/<int:projet_id>/equipe/<int:membre_id>', methods=['DELETE'])
@require_auth('admin', 'gestionnaire')
def remove_projet_equipe(projet_id, membre_id):
    try:
        projet_service.remove_equipe_membre(projet_id, membre_id)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@routes.route('/projet/<int:projet_id>/contact', methods=['POST'])
@require_auth('admin', 'gestionnaire')
def add_projet_contact(projet_id):
    data = request.json or {}
    contact_id    = data.get('contact_id') or None
    contact_libre = (data.get('contact_libre') or '').strip() or None
    if not contact_id and not contact_libre:
        return jsonify({"error": "contact_id ou contact_libre requis"}), 400
    try:
        projet_service.add_projet_contact(projet_id, contact_id, data.get('role'), contact_libre)
        return jsonify({"ok": True}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@routes.route('/projet/<int:projet_id>/contact/<int:contact_id>', methods=['DELETE'])
@require_auth('admin', 'gestionnaire')
def remove_projet_contact(projet_id, contact_id):
    try:
        projet_service.remove_projet_contact(projet_id, contact_id=contact_id)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@routes.route('/projet/<int:projet_id>/contact/libre', methods=['DELETE'])
@require_auth('admin', 'gestionnaire')
def remove_projet_contact_libre(projet_id):
    data = request.json or {}
    try:
        projet_service.remove_projet_contact(projet_id, contact_libre=data.get('contact_libre'))
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ─────────────────────────────────────────────
# TÂCHES
# ─────────────────────────────────────────────

def _tache_visibility_where(user_id, role, service_id):
    """
    Filtre de visibilité pour les tâches :
    - admin        → voit tout
    - gestionnaire → voit toutes les tâches assignées à son service/unité (+ les siennes)
    - lecteur      → voit uniquement les tâches qui lui sont assignées ou qu'il a créées
    Les tâches sans assignee (NULL) sont visibles aux gestionnaires et admins.
    """
    if role == 'admin':
        return "1=1", []
    elif role == 'gestionnaire' and service_id:
        return (
            "(t.assignee_id = %s "
            "OR t.created_by_id = %s "
            "OR t.assignee_id IN (SELECT id FROM utilisateurs WHERE service_id = %s AND actif = true) "
            "OR t.created_by_id IN (SELECT id FROM utilisateurs WHERE service_id = %s AND actif = true) "
            "OR t.assignee_id IS NULL)",
            [user_id, user_id, service_id, service_id]
        )
    else:
        # lecteur ou gestionnaire sans service : uniquement les siennes
        return "(t.assignee_id = %s OR t.created_by_id = %s)", [user_id, user_id]


@routes.route('/tache', methods=['GET'])
@require_auth()
def get_taches():
    user_id    = g.user.get('sub')
    role       = g.user.get('role')
    service_id = g.user.get('service_id')
    if role == 'admin':
        taches = tache_service.get_all()
    else:
        where, params = _tache_visibility_where(user_id, role, service_id)
        rows = tache_service.db.fetch_all(
            "SELECT t.*, p.nom as projet_nom, p.code as projet_code, "
            "u.nom || ' ' || u.prenom as assignee_nom, "
            "u.id as assignee_user_id, "
            "s.nom as assignee_service_nom, s.code as assignee_service_code, "
            "s.is_unite as assignee_is_unite "
            "FROM taches t "
            "LEFT JOIN projets p ON p.id = t.projet_id "
            "LEFT JOIN utilisateurs u ON u.id = t.assignee_id "
            "LEFT JOIN services s ON s.id = u.service_id "
            f"WHERE {where} "
            "ORDER BY t.date_echeance ASC NULLS LAST, t.id DESC",
            params
        )
        taches = [dict(r) for r in (rows or [])]
    return jsonify({"count": len(taches), "list": taches})


@routes.route('/tache', methods=['POST'])
@require_auth('admin', 'gestionnaire')
def create_tache():
    data    = request.json
    user_id = g.user.get('sub')
    try:
        tache_service.db.execute(
            "INSERT INTO taches (projet_id, titre, statut, priorite, date_debut, date_echeance, "
            "estimation_heures, avancement, responsable_label, assignee_id, created_by_id) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            [data.get('projet_id') or None, data.get('titre'),
             data.get('statut', 'A faire'), data.get('priorite'),
             data.get('date_debut') or None, data.get('date_echeance') or None,
             data.get('estimation_heures') or None, data.get('avancement') or 0,
             data.get('responsable_label') or None,
             data.get('assignee_id') or None, user_id]
        )
        return jsonify({"success": True}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@routes.route('/tache/<int:tache_id>', methods=['GET'])
@require_auth()
def get_tache_by_id(tache_id):
    user_id    = g.user.get('sub')
    role       = g.user.get('role')
    service_id = g.user.get('service_id')
    try:
        if role != 'admin':
            vis_w, vis_p = _tache_visibility_where(user_id, role, service_id)
            row = tache_service.db.fetch_one(
                "SELECT t.*, p.nom as projet_nom FROM taches t "
                "LEFT JOIN projets p ON p.id = t.projet_id "
                f"WHERE t.id = %s AND ({vis_w})",
                [tache_id] + vis_p
            )
        else:
            row = tache_service.db.fetch_one(
                "SELECT t.*, p.nom as projet_nom FROM taches t "
                "LEFT JOIN projets p ON p.id = t.projet_id WHERE t.id = %s",
                [tache_id]
            )
        if row:
            return jsonify(dict(row))
        return jsonify({"error": "Tâche introuvable"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@routes.route('/tache/<int:tache_id>', methods=['PUT'])
@require_auth('admin', 'gestionnaire')
def update_tache(tache_id):
    data       = request.json
    user_id    = g.user.get('sub')
    role       = g.user.get('role')
    service_id = g.user.get('service_id')
    # Vérifier que la tâche est visible avant modification
    if role != 'admin':
        vis_w, vis_p = _tache_visibility_where(user_id, role, service_id)
        check = tache_service.db.fetch_one(
            f"SELECT id FROM taches t WHERE t.id=%s AND ({vis_w})",
            [tache_id] + vis_p
        )
        if not check:
            return jsonify({"error": "Tâche introuvable"}), 404
    try:
        tache_service.db.execute(
            "UPDATE taches SET projet_id=%s, titre=%s, statut=%s, priorite=%s, "
            "date_debut=%s, date_echeance=%s, estimation_heures=%s, avancement=%s, "
            "responsable_label=%s, assignee_id=%s, updated_at=NOW() WHERE id=%s",
            [data.get('projet_id') or None, data.get('titre'), data.get('statut'),
             data.get('priorite'), data.get('date_debut') or None,
             data.get('date_echeance') or None,
             data.get('estimation_heures') or None, data.get('avancement') or 0,
             data.get('responsable_label') or None,
             data.get('assignee_id') or None, tache_id]
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@routes.route('/tache/<int:tache_id>', methods=['DELETE'])
@require_auth('admin')
def delete_tache(tache_id):
    try:
        tache_service.db.execute("DELETE FROM taches WHERE id=%s", [tache_id])
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ─────────────────────────────────────────────
# FOURNISSEURS
# ─────────────────────────────────────────────

@routes.route('/fournisseur', methods=['GET'])
@require_auth()
def get_fournisseurs_list():
    user_id    = g.user.get('sub')
    role       = g.user.get('role')
    service_id = g.user.get('service_id')
    try:
        if role == 'admin':
            w_clause, w_params = "1=1", []
        else:
            w_clause, w_params = _ownership_where(user_id, role, service_id, 'f')
        rows = referentiel_service.db.fetch_all(
            "SELECT f.*, "
            "(SELECT COUNT(*) FROM contrats c WHERE c.fournisseur_id=f.id) as nb_contrats, "
            "(SELECT COUNT(*) FROM bons_commande bc WHERE bc.fournisseur_id=f.id) as nb_bc, "
            "(SELECT COALESCE(SUM(bc.montant_ttc),0) FROM bons_commande bc WHERE bc.fournisseur_id=f.id) as montant_total, "
            "(SELECT STRING_AGG(TRIM(CONCAT(c.nom, ' ', COALESCE(c.prenom,''))), ', ' ORDER BY c.nom) "
            " FROM contacts c JOIN fournisseur_contacts fc ON fc.contact_id=c.id WHERE fc.fournisseur_id=f.id) as contacts_lies "
            f"FROM fournisseurs f WHERE {w_clause} ORDER BY f.nom",
            w_params
        )
        result = [dict(r) for r in rows] if rows else []
        return jsonify({"count": len(result), "list": result})
    except Exception as e:
        return jsonify({"count": 0, "list": [], "error": str(e)})


@routes.route('/fournisseur', methods=['POST'])
@require_auth('admin', 'gestionnaire')
def create_fournisseur():
    data    = request.json
    user_id = g.user.get('sub')
    try:
        referentiel_service.db.execute(
            "INSERT INTO fournisseurs (nom, contact_principal, email, telephone, adresse, ville, statut, created_by_id) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            [data.get('nom'), data.get('contact_principal'), data.get('email'),
             data.get('telephone'), data.get('adresse'), data.get('ville'), 'ACTIF', user_id]
        )
        return jsonify({"success": True}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@routes.route('/fournisseur/<int:fournisseur_id>', methods=['PUT'])
@require_auth('admin', 'gestionnaire')
def update_fournisseur(fournisseur_id):
    data       = request.json
    user_id    = g.user.get('sub')
    role       = g.user.get('role')
    service_id = g.user.get('service_id')
    if role != 'admin':
        own_w, own_p = _ownership_where(user_id, role, service_id, 'f')
        check = referentiel_service.db.fetch_one(
            f"SELECT id FROM fournisseurs f WHERE f.id=%s AND {own_w}",
            [fournisseur_id] + own_p
        )
        if not check:
            return jsonify({"error": "Fournisseur introuvable"}), 404
    try:
        referentiel_service.db.execute(
            "UPDATE fournisseurs SET nom=%s, contact_principal=%s, email=%s, "
            "telephone=%s, adresse=%s, ville=%s WHERE id=%s",
            [data.get('nom'), data.get('contact_principal'), data.get('email'),
             data.get('telephone'), data.get('adresse'), data.get('ville'), fournisseur_id]
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@routes.route('/fournisseur/<int:fournisseur_id>', methods=['DELETE'])
@require_auth('admin')
def delete_fournisseur(fournisseur_id):
    try:
        referentiel_service.db.execute("DELETE FROM fournisseurs WHERE id=%s", [fournisseur_id])
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ── Contacts liés à un fournisseur ──────────────────────────

@routes.route('/fournisseur/<int:fournisseur_id>/contacts', methods=['GET'])
@require_auth()
def get_fournisseur_contacts(fournisseur_id):
    try:
        rows = referentiel_service.db.fetch_all(
            "SELECT c.id, c.nom, c.prenom, c.fonction, c.type, c.telephone, c.email, c.societe "
            "FROM contacts c "
            "JOIN fournisseur_contacts fc ON fc.contact_id = c.id "
            "WHERE fc.fournisseur_id = %s ORDER BY c.nom, c.prenom",
            [fournisseur_id]
        )
        return jsonify({"list": [dict(r) for r in rows] if rows else []})
    except Exception as e:
        return jsonify({"list": [], "error": str(e)})


@routes.route('/fournisseur/<int:fournisseur_id>/contacts', methods=['POST'])
@require_auth('admin', 'gestionnaire')
def add_fournisseur_contact(fournisseur_id):
    data = request.json
    contact_id = data.get('contact_id')
    if not contact_id:
        return jsonify({"error": "contact_id requis"}), 400
    try:
        referentiel_service.db.execute(
            "INSERT INTO fournisseur_contacts (fournisseur_id, contact_id) "
            "VALUES (%s, %s) ON CONFLICT DO NOTHING",
            [fournisseur_id, contact_id]
        )
        return jsonify({"success": True}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@routes.route('/fournisseur/<int:fournisseur_id>/contacts/<int:contact_id>', methods=['DELETE'])
@require_auth('admin', 'gestionnaire')
def remove_fournisseur_contact(fournisseur_id, contact_id):
    try:
        referentiel_service.db.execute(
            "DELETE FROM fournisseur_contacts WHERE fournisseur_id=%s AND contact_id=%s",
            [fournisseur_id, contact_id]
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ─────────────────────────────────────────────
# CONTACTS
# ─────────────────────────────────────────────

@routes.route('/contact', methods=['GET'])
@require_auth()
def get_contacts():
    user_id    = g.user.get('sub')
    role       = g.user.get('role')
    service_id = g.user.get('service_id')
    filters    = request.args.to_dict()

    if role == 'admin':
        contacts = contact_service.get_all(filters)
    else:
        where, params = _ownership_where(user_id, role, service_id, 'c')
        extra = []
        if filters.get('type'):
            extra.append("AND c.type = %s")
            params.append(filters['type'])
        if filters.get('search'):
            s = '%' + filters['search'] + '%'
            extra.append("AND (c.nom ILIKE %s OR c.prenom ILIKE %s OR c.email ILIKE %s OR c.organisation ILIKE %s)")
            params.extend([s, s, s, s])
        rows = contact_service.db.fetch_all(
            "SELECT c.*, s.nom as service_nom "
            "FROM contacts c "
            "LEFT JOIN services s ON s.id = c.service_id "
            f"WHERE {where} " + " ".join(extra) +
            " ORDER BY c.nom, c.prenom",
            params
        )
        contacts = [dict(r) for r in rows] if rows else []

    return jsonify({"count": len(contacts), "list": contacts})

@routes.route('/contact', methods=['POST'])
@require_auth('admin', 'gestionnaire')
def create_contact():
    data = request.json
    data['created_by_id'] = g.user.get('sub')
    try:
        contact_service.create(data)
        return jsonify({"success": True}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@routes.route('/contact/<int:contact_id>', methods=['PUT'])
@require_auth('admin', 'gestionnaire')
def update_contact(contact_id):
    data = request.json
    try:
        contact_service.update(contact_id, data)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@routes.route('/contact/<int:contact_id>', methods=['DELETE'])
@require_auth('admin')
def delete_contact(contact_id):
    try:
        contact_service.delete(contact_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ─────────────────────────────────────────────
# SERVICES (ORGANISATION)
# ─────────────────────────────────────────────

@routes.route('/service_org', methods=['GET'])
@require_auth()
def get_services_org():
    services = service_org_service.get_all()
    return jsonify({"count": len(services), "list": services})

@routes.route('/service_org', methods=['POST'])
@require_auth('admin')
def create_service_org():
    data = request.json
    try:
        service_org_service.create(data)
        return jsonify({"success": True}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@routes.route('/service_org/<int:service_id>', methods=['PUT'])
@require_auth('admin')
def update_service_org(service_id):
    data = request.json
    try:
        service_org_service.update(service_id, data)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@routes.route('/service_org/<int:service_id>', methods=['DELETE'])
@require_auth('admin')
def delete_service_org(service_id):
    try:
        service_org_service.delete(service_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@routes.route('/service_org/<int:service_id>/membres', methods=['GET'])
@require_auth()
def get_service_membres(service_id):
    membres = service_org_service.get_membres(service_id)
    return jsonify({"list": membres})


# ─────────────────────────────────────────────
# RÉFÉRENTIELS (données pour les selects)
# ─────────────────────────────────────────────

@routes.route('/referentiels', methods=['GET'])
@require_auth()
def get_referentiels():
    try:
        etp          = referentiel_service.get_etp()
        fournisseurs = referentiel_service.get_fournisseurs()
        contacts     = referentiel_service.get_contacts()
        services     = referentiel_service.get_services()
        entites      = budget_service.get_entites()
        projets      = projet_service.get_all()
        lignes       = budget_service.get_lignes()
        applications = budget_service.get_all_applications()
        contrats_ref = contrat_service.db.fetch_all(
            "SELECT id, numero_contrat, objet FROM contrats ORDER BY numero_contrat"
        )
        contrats_ref = [dict(c) for c in contrats_ref] if contrats_ref else []
        return jsonify({
            "etp": etp, "fournisseurs": fournisseurs,
            "contacts": contacts, "services": services,
            "entites": entites, "projets": projets,
            "lignes": lignes, "applications": applications,
            "contrats": contrats_ref,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
# KANBAN
# ─────────────────────────────────────────────

@routes.route('/kanban', methods=['GET'])
@require_auth()
def kanban():
    cur_user_id = g.user.get('sub')
    role        = g.user.get('role')
    service_id  = g.user.get('service_id')
    projet_id   = request.args.get('projet_id')
    user_id     = request.args.get('user_id')

    if role == 'admin':
        taches = tache_service.get_all()
    else:
        where, params = _tache_visibility_where(cur_user_id, role, service_id)
        rows = tache_service.db.fetch_all(
            "SELECT t.*, p.nom as projet_nom, p.code as projet_code, "
            "u.nom || ' ' || u.prenom as assignee_nom, u.id as assignee_user_id, "
            "s.nom as assignee_service_nom, s.code as assignee_service_code, "
            "s.is_unite as assignee_is_unite "
            "FROM taches t "
            "LEFT JOIN projets p ON p.id = t.projet_id "
            "LEFT JOIN utilisateurs u ON u.id = t.assignee_id "
            "LEFT JOIN services s ON s.id = u.service_id "
            f"WHERE {where} ORDER BY t.date_echeance ASC NULLS LAST",
            params
        )
        taches = [dict(r) for r in (rows or [])]

    if projet_id:
        taches = [t for t in taches if str(t.get('projet_id', '')) == str(projet_id)]
    if user_id:
        taches = [t for t in taches if str(t.get('assignee_id', '')) == str(user_id)]
    colonnes = ['A faire', 'En cours', 'En attente', 'Bloqué', 'Terminé']
    columns = {c: [] for c in colonnes}
    for t in taches:
        statut = t.get('statut', 'A faire')
        if statut in columns:
            columns[statut].append(t)
        else:
            columns.setdefault(statut, []).append(t)
    return jsonify({"columns": columns})


# ─────────────────────────────────────────────
# ETP / CHARGE (simplifié)
# ─────────────────────────────────────────────

@routes.route('/etp', methods=['GET'])
@require_auth()
def etp():
    mode       = request.args.get('mode', 'projet')  # 'projet' ou 'personne'
    user_id    = g.user.get('sub')
    role       = g.user.get('role')
    service_id = g.user.get('service_id')
    try:
        if mode == 'personne':
            # Filtre utilisateurs selon rôle
            if role == 'admin':
                user_where  = "u.actif = true"
                user_params = []
            elif role == 'gestionnaire' and service_id:
                user_where  = "u.actif = true AND u.service_id = %s"
                user_params = [service_id]
            else:
                # lecteur : uniquement soi-même
                user_where  = "u.actif = true AND u.id = %s"
                user_params = [user_id]

            rows = projet_service.db.fetch_all(
                "SELECT u.id, u.nom, u.prenom, u.email, u.role, "
                "s.nom as service_nom, s.code as service_code, "
                "COALESCE(s.is_unite, false) as is_unite, "
                "COUNT(t.id) as nb_taches, "
                "COALESCE(SUM(t.estimation_heures), 0) as heures_estimees, "
                "COALESCE(SUM(t.heures_reelles), 0) as heures_reelles "
                "FROM utilisateurs u "
                "LEFT JOIN services s ON s.id = u.service_id "
                "LEFT JOIN taches t ON t.assignee_id = u.id "
                "  AND t.statut NOT IN ('Terminé', 'Annulé') "
                f"WHERE {user_where} "
                "GROUP BY u.id, u.nom, u.prenom, u.email, u.role, "
                "  s.nom, s.code, s.is_unite "
                "ORDER BY heures_estimees DESC, u.nom",
                user_params
            )
            result = [dict(r) for r in rows] if rows else []
            HEURES_AN = 1540  # 1 ETP = ~220 jours * 7h
            for r in result:
                h = float(r.get('heures_estimees') or 0)
                r['heures_dispo'] = round(HEURES_AN - h, 1)
                r['pct_charge']   = round(h / HEURES_AN * 100, 1)
                r['etp_charge']   = round(h / HEURES_AN, 2)
            return jsonify({"list": result, "mode": "personne",
                            "heures_an": HEURES_AN})
        else:
            # Charge par projet — filtré par ownership
            if role == 'admin':
                proj_where  = "p.statut NOT IN ('Terminé', 'Annulé')"
                proj_params = []
            else:
                own_w, own_p = _ownership_where(user_id, role, service_id, 'p')
                proj_where   = f"p.statut NOT IN ('Terminé', 'Annulé') AND ({own_w})"
                proj_params  = own_p
            rows = projet_service.db.fetch_all(
                "SELECT p.id, p.code, p.nom, p.statut, "
                "COALESCE(SUM(t.estimation_heures), 0) as heures_estimees, "
                "COALESCE(SUM(t.heures_reelles), 0) as heures_reelles, "
                "COUNT(t.id) as nb_taches "
                "FROM projets p "
                "LEFT JOIN taches t ON t.projet_id = p.id "
                f"WHERE {proj_where} "
                "GROUP BY p.id, p.code, p.nom, p.statut "
                "ORDER BY heures_estimees DESC",
                proj_params
            )
            result = [dict(r) for r in rows] if rows else []
            total_h = sum(r.get('heures_estimees', 0) or 0 for r in result)
            return jsonify({
                "list": result, "mode": "projet",
                "total_heures": total_h,
                "total_jours": round(total_h / 7, 1),
                "total_etp": round(total_h / 154, 2),
            })
    except Exception as e:
        return jsonify({"list": [], "error": str(e)})


@routes.route('/users/actifs', methods=['GET'])
@require_auth()
def get_users_actifs():
    """Tous les utilisateurs actifs — pour les selects tâches/équipe."""
    try:
        rows = tache_service.db.fetch_all(
            "SELECT u.id, u.nom, u.prenom, u.email, u.role, "
            "u.service_id, s.nom as service_nom, s.code as service_code, "
            "COALESCE(s.is_unite, false) as is_unite "
            "FROM utilisateurs u "
            "LEFT JOIN services s ON s.id = u.service_id "
            "WHERE u.actif = true ORDER BY u.nom, u.prenom"
        )
        result = [dict(r) for r in rows] if rows else []
        return jsonify({"list": result})
    except Exception as e:
        return jsonify({"list": [], "error": str(e)})


# ─────────────────────────────────────────────
# NOTIFICATIONS
# ─────────────────────────────────────────────

@routes.route('/notifications', methods=['GET'])
@require_auth()
def get_notifications():
    try:
        rows = budget_service.db.fetch_all(
            "SELECT * FROM notifications ORDER BY date_creation DESC LIMIT 50"
        )
        result = [dict(r) for r in rows] if rows else []
        non_lues = sum(1 for r in result if not r.get('lue'))
        return jsonify({"list": result, "non_lues": non_lues})
    except Exception as e:
        return jsonify({"list": [], "non_lues": 0})

@routes.route('/notifications/<int:notif_id>/lire', methods=['POST'])
@require_auth()
def lire_notification(notif_id):
    try:
        budget_service.db.execute("UPDATE notifications SET lue=true WHERE id=%s", [notif_id])
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ─────────────────────────────────────────────
# GANTT
# ─────────────────────────────────────────────

@routes.route('/gantt', methods=['GET'])
@require_auth()
def get_gantt():
    """Retourne projets + tâches pour le diagramme de Gantt."""
    user_id    = g.user.get('sub')
    role       = g.user.get('role')
    svc_id     = g.user.get('service_id')

    service_id = request.args.get('service_id', type=int)
    date_debut = request.args.get('date_debut')   # YYYY-MM-DD
    date_fin   = request.args.get('date_fin')     # YYYY-MM-DD
    projet_id  = request.args.get('projet_id', type=int)

    db = budget_service.db

    # ── Projets ─────────────────────────────────────────────
    proj_where = ["(p.date_debut IS NOT NULL OR p.date_fin_prevue IS NOT NULL)"]
    proj_params = []
    # Filtre propriétaire (non-admin)
    if role != 'admin':
        own_w, own_p = _ownership_where(user_id, role, svc_id, 'p')
        proj_where.append(f"({own_w})")
        proj_params.extend(own_p)
    if service_id:
        proj_where.append("p.service_id = %s")
        proj_params.append(service_id)
    if date_debut:
        proj_where.append("(p.date_fin_prevue IS NULL OR p.date_fin_prevue >= %s)")
        proj_params.append(date_debut)
    if date_fin:
        proj_where.append("(p.date_debut IS NULL OR p.date_debut <= %s)")
        proj_params.append(date_fin)
    proj_sql = (
        "SELECT p.id, p.code, p.nom, p.date_debut, p.date_fin_prevue, "
        "p.avancement, p.statut, s.nom as service_nom "
        "FROM projets p "
        "LEFT JOIN services s ON s.id = p.service_id "
        "WHERE " + " AND ".join(proj_where) +
        " ORDER BY p.date_debut NULLS LAST"
    )
    try:
        projets = db.fetch_all(proj_sql, proj_params) or []
    except Exception:
        projets = []

    # ── Tâches ──────────────────────────────────────────────
    tache_where = ["t.date_echeance IS NOT NULL"]
    tache_params = []
    # Filtre visibilité tâches (non-admin)
    if role != 'admin':
        t_w, t_p = _tache_visibility_where(user_id, role, svc_id)
        tache_where.append(f"({t_w})")
        tache_params.extend(t_p)
    if projet_id:
        tache_where.append("t.projet_id = %s")
        tache_params.append(projet_id)
    elif service_id:
        tache_where.append("p.service_id = %s")
        tache_params.append(service_id)
    if date_debut:
        tache_where.append("(t.date_echeance IS NULL OR t.date_echeance >= %s)")
        tache_params.append(date_debut)
    if date_fin:
        tache_where.append("(t.date_debut IS NULL OR t.date_debut <= %s)")
        tache_params.append(date_fin)
    tache_sql = (
        "SELECT t.id, t.titre, t.statut, t.priorite, t.avancement, "
        "t.date_debut, t.date_echeance, t.responsable_label, "
        "t.projet_id, p.nom as projet_nom, p.code as projet_code "
        "FROM taches t "
        "JOIN projets p ON p.id = t.projet_id "
        "WHERE " + " AND ".join(tache_where) +
        " ORDER BY t.date_debut NULLS LAST, t.date_echeance"
    )
    try:
        taches = db.fetch_all(tache_sql, tache_params) or []
    except Exception:
        taches = []

    def _str(v):
        return str(v) if v is not None else None

    return jsonify({
        "projets": [
            {**dict(r), "date_debut": _str(r.get("date_debut")),
             "date_fin_prevue": _str(r.get("date_fin_prevue"))}
            for r in projets
        ],
        "taches": [
            {**dict(r), "date_debut": _str(r.get("date_debut")),
             "date_echeance": _str(r.get("date_echeance"))}
            for r in taches
        ],
    })
