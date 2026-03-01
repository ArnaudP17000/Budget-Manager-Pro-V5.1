import bcrypt as _bcrypt
from flask import Flask, send_from_directory
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
        ('objectifs',    'TEXT'),
        ('enjeux',       'TEXT'),
        ('gains',        'TEXT'),
        ('risques',      'TEXT'),
        ('contraintes',  'TEXT'),
        ('solutions',    'TEXT'),
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


@app.route('/')
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
