import bcrypt as _bcrypt
from flask import Flask, send_from_directory, jsonify
import os
from routes import routes

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
app.register_blueprint(routes, url_prefix='/api')


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
    ]
    for col, typ in new_cols:
        try:
            db.execute(
                f"ALTER TABLE projets ADD COLUMN IF NOT EXISTS {col} {typ}"
            )
        except Exception:
            pass

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
        except Exception:
            pass

    # ── Colonne projet_equipe ────────────────────────────────
    try:
        db.execute(
            "ALTER TABLE projet_equipe ADD COLUMN IF NOT EXISTS membre_label TEXT"
        )
    except Exception:
        pass

    # ── Colonnes taches (Gantt) ─────────────────────────────
    try:
        db.execute(
            "ALTER TABLE taches ADD COLUMN IF NOT EXISTS date_debut DATE"
        )
    except Exception:
        pass
    try:
        db.execute(
            "ALTER TABLE taches ADD COLUMN IF NOT EXISTS responsable_label TEXT"
        )
    except Exception:
        pass
    try:
        db.execute(
            "ALTER TABLE taches ADD COLUMN IF NOT EXISTS assignee_id INTEGER"
        )
    except Exception:
        pass

    # ── Colonnes services (Unités) ──────────────────────────
    try:
        db.execute(
            "ALTER TABLE services ADD COLUMN IF NOT EXISTS nb_personnes INTEGER"
        )
    except Exception:
        pass
    try:
        db.execute(
            "ALTER TABLE services ADD COLUMN IF NOT EXISTS membres_label TEXT"
        )
    except Exception:
        pass
    try:
        db.execute(
            "ALTER TABLE services ADD COLUMN IF NOT EXISTS is_unite BOOLEAN DEFAULT FALSE"
        )
    except Exception:
        pass

    # ── Colonne projet_contacts (contact libre + contact_id nullable) ─────
    try:
        db.execute(
            "ALTER TABLE projet_contacts ADD COLUMN IF NOT EXISTS contact_libre TEXT"
        )
    except Exception:
        pass
    try:
        db.execute(
            "ALTER TABLE projet_contacts ALTER COLUMN contact_id DROP NOT NULL"
        )
    except Exception:
        pass

    # ── Email optionnel : supprimer NOT NULL + nettoyer valeurs vides ─
    try:
        db.execute(
            "ALTER TABLE utilisateurs ALTER COLUMN email DROP NOT NULL"
        )
    except Exception:
        pass
    try:
        db.execute(
            "UPDATE utilisateurs SET email = NULL WHERE email = ''"
        )
    except Exception:
        pass

    # ── Colonne societe dans contacts ───────────────────────────
    try:
        db.execute(
            "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS societe VARCHAR(200)"
        )
    except Exception:
        pass

    # ── Propriété des enregistrements (created_by_id) ───────────
    for tbl in ['bons_commande', 'contrats', 'projets', 'contacts', 'taches', 'fournisseurs']:
        try:
            db.execute(f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS created_by_id INTEGER")
        except Exception:
            pass

    # ── Contacts liés aux fournisseurs ──────────────────────────
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS fournisseur_contacts (
                fournisseur_id INTEGER NOT NULL,
                contact_id     INTEGER NOT NULL,
                PRIMARY KEY (fournisseur_id, contact_id)
            )
        """)
    except Exception:
        pass

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
    except Exception:
        pass

    # ── Colonne motif_refus sur bons_commande ───────────────
    try:
        db.execute(
            "ALTER TABLE bons_commande ADD COLUMN IF NOT EXISTS motif_refus TEXT"
        )
    except Exception:
        pass

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
    except Exception:
        pass

    # ── Resync séquences (évite duplicate key après import CSV) ─
    for table in ['projets', 'services', 'utilisateurs', 'contacts',
                  'taches', 'contrats', 'bons_commande', 'fournisseurs']:
        try:
            db.execute(
                f"SELECT setval('{table}_id_seq', "
                f"GREATEST(1, (SELECT COALESCE(MAX(id), 1) FROM {table})))"
            )
        except Exception:
            pass

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
    except Exception:
        pass


run_migrations()

# Réinitialiser la connexion DB après les migrations
# (psycopg2 n'est pas fork-safe : chaque worker gunicorn doit créer sa propre connexion)
try:
    from app.services.database_service import DatabaseService
    if DatabaseService._connection and not DatabaseService._connection.closed:
        DatabaseService._connection.close()
    DatabaseService._connection = None
    DatabaseService._instance = None
except Exception:
    pass


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
