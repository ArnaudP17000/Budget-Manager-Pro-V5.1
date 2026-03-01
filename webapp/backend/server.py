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


@app.route('/')
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')


if __name__ == '__main__':
    run_migrations()
    app.run(host='0.0.0.0', port=5000, debug=False)

