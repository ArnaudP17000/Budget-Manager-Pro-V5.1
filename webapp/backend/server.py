import bcrypt as _bcrypt
import logging
from flask import Flask, send_from_directory, jsonify
import os
from routes import routes
from tpe_routes import tpe_routes  # TPE MODULE — retirer cette ligne pour désinstaller

_mlog = logging.getLogger('migrations')

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
app.register_blueprint(routes, url_prefix='/api')
app.register_blueprint(tpe_routes, url_prefix='/api')  # TPE MODULE


def run_migrations():
    """Ajoute les colonnes manquantes sans casser l'existant."""
    from app.services.database_service import DatabaseService
    db = DatabaseService()

    # ── Colonnes projets ────────────────────────────────────
    new_cols = [
        ('objectifs',             'TEXT'),
        ('enjeux',                'TEXT'),
        ('gains',                 'TEXT'),
        ('risques',               'TEXT'),
        ('contraintes',           'TEXT'),
        ('solutions',             'TEXT'),
        ('financement',           'TEXT'),
        ('registre_risques',      'TEXT'),
        ('contraintes_6axes',     'TEXT'),
        ('triangle_tensions',     'TEXT'),
        ('arbitrage',             'TEXT'),
        ('chef_projet_contact_id','INTEGER'),
        ('responsable_contact_id','INTEGER'),
        ('note',                  'TEXT'),
    ]
    for col, typ in new_cols:
        try:
            db.execute(
                f"ALTER TABLE projets ADD COLUMN IF NOT EXISTS {col} {typ}"
            )
        except Exception as _me:
            _mlog.warning("Migration skipped: %s", _me)

    # ── Colonnes utilisateurs (auth) ────────────────────────
    auth_cols = [
        ('login',        'VARCHAR(100) UNIQUE'),
        ('mot_de_passe', 'TEXT'),
        ('role',         "VARCHAR(20) DEFAULT 'lecteur'"),
        ('service_id',   'INTEGER'),
    ]
    for col, typ in auth_cols:
        try:
            db.execute(
                f"ALTER TABLE utilisateurs ADD COLUMN IF NOT EXISTS {col} {typ}"
            )
        except Exception as _me:
            _mlog.warning("Migration skipped: %s", _me)

    # ── Colonne projet_equipe ────────────────────────────────
    try:
        db.execute(
            "ALTER TABLE projet_equipe ADD COLUMN IF NOT EXISTS membre_label TEXT"
        )
    except Exception as _me:
        _mlog.warning("Migration skipped: %s", _me)

    # ── Colonnes taches (Gantt) ─────────────────────────────
    try:
        db.execute(
            "ALTER TABLE taches ADD COLUMN IF NOT EXISTS date_debut DATE"
        )
    except Exception as _me:
        _mlog.warning("Migration skipped: %s", _me)
    try:
        db.execute(
            "ALTER TABLE taches ADD COLUMN IF NOT EXISTS responsable_label TEXT"
        )
    except Exception as _me:
        _mlog.warning("Migration skipped: %s", _me)
    try:
        db.execute(
            "ALTER TABLE taches ADD COLUMN IF NOT EXISTS assignee_id INTEGER"
        )
    except Exception as _me:
        _mlog.warning("Migration skipped: %s", _me)
    try:
        db.execute(
            "ALTER TABLE taches ADD COLUMN IF NOT EXISTS type_tache VARCHAR(50) DEFAULT 'autre'"
        )
    except Exception as _me:
        _mlog.warning("Migration skipped: %s", _me)
    try:
        db.execute(
            "ALTER TABLE taches ADD COLUMN IF NOT EXISTS rapport_reunion TEXT"
        )
    except Exception as _me:
        _mlog.warning("Migration skipped: %s", _me)

    # ── Colonnes services (Unités) ──────────────────────────
    try:
        db.execute(
            "ALTER TABLE services ADD COLUMN IF NOT EXISTS nb_personnes INTEGER"
        )
    except Exception as _me:
        _mlog.warning("Migration skipped: %s", _me)
    try:
        db.execute(
            "ALTER TABLE services ADD COLUMN IF NOT EXISTS membres_label TEXT"
        )
    except Exception as _me:
        _mlog.warning("Migration skipped: %s", _me)
    try:
        db.execute(
            "ALTER TABLE services ADD COLUMN IF NOT EXISTS is_unite BOOLEAN DEFAULT FALSE"
        )
    except Exception as _me:
        _mlog.warning("Migration skipped: %s", _me)
    try:
        db.execute(
            "ALTER TABLE services ADD COLUMN IF NOT EXISTS is_direction BOOLEAN DEFAULT FALSE"
        )
    except Exception as _me:
        _mlog.warning("Migration skipped: %s", _me)

    # ── Colonne projet_contacts (contact libre + contact_id nullable) ─────
    try:
        db.execute(
            "ALTER TABLE projet_contacts ADD COLUMN IF NOT EXISTS contact_libre TEXT"
        )
    except Exception as _me:
        _mlog.warning("Migration skipped: %s", _me)
    try:
        db.execute(
            "ALTER TABLE projet_contacts ALTER COLUMN contact_id DROP NOT NULL"
        )
    except Exception as _me:
        _mlog.warning("Migration skipped: %s", _me)

    # ── Email optionnel : supprimer NOT NULL + nettoyer valeurs vides ─
    try:
        db.execute(
            "ALTER TABLE utilisateurs ALTER COLUMN email DROP NOT NULL"
        )
    except Exception as _me:
        _mlog.warning("Migration skipped: %s", _me)
    try:
        db.execute(
            "UPDATE utilisateurs SET email = NULL WHERE email = ''"
        )
    except Exception as _me:
        _mlog.warning("Migration skipped: %s", _me)

    # ── Colonne societe dans contacts ───────────────────────────
    try:
        db.execute(
            "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS societe VARCHAR(200)"
        )
    except Exception as _me:
        _mlog.warning("Migration skipped: %s", _me)

    # ── Propriété des enregistrements (created_by_id) ───────────
    for tbl in ['bons_commande', 'contrats', 'projets', 'contacts', 'taches', 'fournisseurs']:
        try:
            db.execute(f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS created_by_id INTEGER")
        except Exception as _me:
            _mlog.warning("Migration skipped: %s", _me)

    # ── Contacts liés aux fournisseurs ──────────────────────────
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS fournisseur_contacts (
                fournisseur_id INTEGER NOT NULL,
                contact_id     INTEGER NOT NULL,
                PRIMARY KEY (fournisseur_id, contact_id)
            )
        """)
    except Exception as _me:
        _mlog.warning("Migration skipped: %s", _me)

    # ── Journal d'audit ─────────────────────────────────────
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                user_login VARCHAR(100),
                action VARCHAR(50),
                table_name VARCHAR(50),
                record_id INTEGER,
                details TEXT,
                date_creation TIMESTAMP DEFAULT NOW()
            )
        """)
    except Exception as _me:
        _mlog.warning("Migration skipped: %s", _me)

    # ── Colonne motif_refus sur bons_commande ───────────────
    try:
        db.execute(
            "ALTER TABLE bons_commande ADD COLUMN IF NOT EXISTS motif_refus TEXT"
        )
    except Exception as _me:
        _mlog.warning("Migration skipped: %s", _me)

    # ── Colonne type_marche sur contrats ─────────────────────
    try:
        db.execute(
            "ALTER TABLE contrats ADD COLUMN IF NOT EXISTS type_marche VARCHAR(50)"
        )
    except Exception as _me:
        _mlog.warning("Migration skipped: %s", _me)

    # ── Permissions budgets (accès explicite par utilisateur) ───
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS budget_permissions (
                id SERIAL PRIMARY KEY,
                budget_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role VARCHAR(20) DEFAULT 'lecteur',
                date_creation TIMESTAMP DEFAULT NOW(),
                UNIQUE(budget_id, user_id)
            )
        """)
    except Exception as _me:
        _mlog.warning("Migration skipped: %s", _me)

    # ── Jalons projet (dates clés / livrables critiques) ────────
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS jalons (
                id SERIAL PRIMARY KEY,
                projet_id INTEGER NOT NULL,
                titre VARCHAR(300) NOT NULL,
                date_echeance DATE,
                statut VARCHAR(30) DEFAULT 'A_VENIR',
                description TEXT,
                created_by_id INTEGER,
                date_creation TIMESTAMP DEFAULT NOW()
            )
        """)
    except Exception as _me:
        _mlog.warning("Migration skipped: %s", _me)

    # ── Journal de bord projet ───────────────────────────────────
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS journal_projet (
                id SERIAL PRIMARY KEY,
                projet_id INTEGER NOT NULL,
                date_entree TIMESTAMP DEFAULT NOW(),
                auteur VARCHAR(200),
                type_entree VARCHAR(50) DEFAULT 'EVENEMENT',
                contenu TEXT NOT NULL,
                created_by_id INTEGER
            )
        """)
    except Exception as _me:
        _mlog.warning("Migration skipped: %s", _me)

    # ── Statut RAG sur projets ───────────────────────────────────
    try:
        db.execute(
            "ALTER TABLE projets ADD COLUMN IF NOT EXISTS statut_rag VARCHAR(10) DEFAULT 'VERT'"
        )
    except Exception as _me:
        _mlog.warning("Migration skipped: %s", _me)

    # ── TPE MODULE : tables + données initiales ──────────────────
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS modules_config (
                module_name VARCHAR(50) PRIMARY KEY,
                enabled     BOOLEAN DEFAULT FALSE,
                date_activation TIMESTAMP DEFAULT NOW()
            )
        """)
    except Exception as _me:
        _mlog.warning("Migration skipped: %s", _me)
    try:
        db.execute("""
            INSERT INTO modules_config (module_name, enabled)
            VALUES ('tpe', FALSE)
            ON CONFLICT (module_name) DO NOTHING
        """)
    except Exception as _me:
        _mlog.warning("Migration skipped: %s", _me)
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS tpe (
                id                   SERIAL PRIMARY KEY,
                service              VARCHAR(300) NOT NULL,
                regisseur_prenom     VARCHAR(100),
                regisseur_nom        VARCHAR(100),
                regisseur_telephone  VARCHAR(30),
                regisseurs_suppleants TEXT,
                shop_id              BIGINT DEFAULT 0,
                backoffice_actif     BOOLEAN DEFAULT FALSE,
                backoffice_email     VARCHAR(200),
                modele_tpe           VARCHAR(100),
                type_ethernet        BOOLEAN DEFAULT FALSE,
                type_4_5g            BOOLEAN DEFAULT FALSE,
                reseau_ip            VARCHAR(20),
                reseau_masque        VARCHAR(20),
                reseau_passerelle    VARCHAR(20),
                nombre_tpe           INTEGER DEFAULT 1,
                created_by_id        INTEGER,
                date_creation        TIMESTAMP DEFAULT NOW(),
                date_maj             TIMESTAMP
            )
        """)
    except Exception as _me:
        _mlog.warning("Migration skipped: %s", _me)
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS tpe_cartes (
                id               SERIAL PRIMARY KEY,
                tpe_id           INTEGER NOT NULL REFERENCES tpe(id) ON DELETE CASCADE,
                numero           VARCHAR(100) NOT NULL,
                numero_serie_tpe VARCHAR(100),
                modele_tpe       VARCHAR(100)
            )
        """)
    except Exception as _me:
        _mlog.warning("Migration skipped: %s", _me)
    # ── Colonne email régisseur sur tpe ──────────────────────────────────
    try:
        db.execute(
            "ALTER TABLE tpe ADD COLUMN IF NOT EXISTS regisseur_email VARCHAR(200)"
        )
    except Exception as _me:
        _mlog.warning("Migration skipped: %s", _me)
    # Import données initiales si la table est vide
    try:
        _import_path = os.path.join(os.path.dirname(__file__), 'data', 'tpe_import.json')
        if os.path.exists(_import_path):
            from app.services.tpe_service import TpeService as _TpeSvc
            _n = _TpeSvc().import_from_json(_import_path)
            if _n:
                _mlog.info("TPE: %d enregistrements importés", _n)
    except Exception as _me:
        _mlog.warning("TPE import skipped: %s", _me)
    # ── /TPE MODULE ───────────────────────────────────────────────

    # ── Resync séquences (évite duplicate key après import CSV) ─
    for table in ['projets', 'services', 'utilisateurs', 'contacts',
                  'taches', 'contrats', 'bons_commande', 'fournisseurs']:
        try:
            db.execute(
                f"SELECT setval('{table}_id_seq', "
                f"GREATEST(1, (SELECT COALESCE(MAX(id), 1) FROM {table})))"
            )
        except Exception as _me:
            _mlog.warning("Migration skipped: %s", _me)

    # ── Compte admin par défaut (idempotent) ────────────────
    try:
        existing = db.fetch_one(
            "SELECT id FROM utilisateurs WHERE login = %s", ['admin']
        )
        if not existing:
            hashed = _bcrypt.hashpw(b'Admin1234!', _bcrypt.gensalt()).decode('utf-8')
            db.execute(
                "INSERT INTO utilisateurs "
                "(nom, prenom, email, login, mot_de_passe, role, actif) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                ['Administrateur', 'Système', 'admin@local.fr',
                 'admin', hashed, 'admin', True]
            )
    except Exception as _me:
        _mlog.warning("Migration skipped: %s", _me)

    # ── Notes (post-its et notes de projet) ─────────────────────
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id            SERIAL PRIMARY KEY,
                titre         VARCHAR(200),
                contenu       TEXT,
                type          VARCHAR(20)  DEFAULT 'postit',
                projet_id     INTEGER,
                couleur       VARCHAR(20)  DEFAULT '#fff9c4',
                created_by_id INTEGER,
                created_at    TIMESTAMP    DEFAULT NOW(),
                updated_at    TIMESTAMP    DEFAULT NOW()
            )
        """)
    except Exception as _me:
        _mlog.warning("Migration skipped: %s", _me)

    # ── Table notifications (créer si absente) + colonnes ref_type/ref_id/niveau ─
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id            SERIAL PRIMARY KEY,
                titre         VARCHAR(300),
                message       TEXT,
                lue           BOOLEAN DEFAULT FALSE,
                user_id       INTEGER,
                date_creation TIMESTAMP DEFAULT NOW()
            )
        """)
    except Exception as _me:
        _mlog.warning("Migration skipped: %s", _me)
    for _col, _typ in [('ref_type', 'VARCHAR(50)'), ('ref_id', 'INTEGER'),
                        ('niveau', "VARCHAR(20) DEFAULT 'INFO'")]:
        try:
            db.execute(f"ALTER TABLE notifications ADD COLUMN IF NOT EXISTS {_col} {_typ}")
        except Exception as _me:
            _mlog.warning("Migration skipped: %s", _me)


run_migrations()

# Fermer le pool après les migrations — chaque worker Gunicorn crée le sien au démarrage
# (psycopg2.pool.ThreadedConnectionPool n'est pas fork-safe)
try:
    from app.services.database_service import DatabaseService
    if DatabaseService._pool is not None:
        DatabaseService._pool.closeall()
        DatabaseService._pool = None
except Exception as _me:
    _mlog.warning("Pool reset after migrations: %s", _me)


@app.after_request
def security_headers(response):
    response.headers['X-Frame-Options']           = 'DENY'
    response.headers['X-Content-Type-Options']    = 'nosniff'
    response.headers['X-XSS-Protection']          = '1; mode=block'
    response.headers['Referrer-Policy']           = 'strict-origin-when-cross-origin'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Permissions-Policy']        = (
        'geolocation=(), microphone=(), camera=(), payment=(), usb=(), magnetometer=()'
    )
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "img-src 'self' data:; "
        "font-src 'self' https://cdn.jsdelivr.net; "
        "connect-src 'self' https://cdn.jsdelivr.net"
    )
    return response


@app.errorhandler(404)
def not_found(e):
    from flask import request as req
    return jsonify({"error": f"Route introuvable: {req.path}"}), 404


@app.route('/')
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
