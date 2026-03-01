import os
import jwt
import bcrypt
from datetime import datetime, timezone, timedelta
from app.services.database_service import DatabaseService

SECRET_KEY   = os.getenv('SECRET_KEY', 'dev-insecure-key-change-in-prod')
EXPIRY_HOURS = int(os.getenv('JWT_EXPIRY_HOURS', '8'))


class AuthService:
    def __init__(self):
        self.db = DatabaseService()

    # ── LOGIN ────────────────────────────────────────────────

    def login(self, login: str, password: str):
        user = self.db.fetch_one(
            "SELECT id, nom, prenom, email, login, mot_de_passe, "
            "role, service_id, actif "
            "FROM utilisateurs WHERE login = %s",
            [login]
        )
        if not user or not user.get('actif'):
            return None

        stored_hash = user['mot_de_passe']
        if isinstance(stored_hash, str):
            stored_hash = stored_hash.encode('utf-8')

        if not bcrypt.checkpw(password.encode('utf-8'), stored_hash):
            return None

        payload = {
            'sub':        user['id'],
            'login':      user['login'],
            'nom':        user['nom'],
            'prenom':     user['prenom'],
            'role':       user['role'],
            'service_id': user['service_id'],
            'iat':        datetime.now(timezone.utc),
            'exp':        datetime.now(timezone.utc) + timedelta(hours=EXPIRY_HOURS),
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
        return {
            'token': token,
            'user': {k: user[k] for k in ['id', 'nom', 'prenom', 'login', 'role', 'service_id']}
        }

    # ── VERIFY TOKEN ────────────────────────────────────────

    def verify_token(self, token: str):
        try:
            return jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    # ── USER CRUD (admin only) ───────────────────────────────

    def get_all_users(self):
        return self.db.fetch_all(
            "SELECT id, nom, prenom, email, login, role, service_id, actif, date_creation "
            "FROM utilisateurs ORDER BY nom, prenom"
        ) or []

    def get_user_by_id(self, user_id: int):
        return self.db.fetch_one(
            "SELECT id, nom, prenom, email, login, role, service_id, actif "
            "FROM utilisateurs WHERE id = %s",
            [user_id]
        )

    def create_user(self, data: dict):
        if len(data.get('mot_de_passe', '')) < 8:
            raise ValueError('Le mot de passe doit contenir au moins 8 caractères')
        hashed = bcrypt.hashpw(
            data['mot_de_passe'].encode('utf-8'), bcrypt.gensalt()
        ).decode('utf-8')
        self.db.execute(
            "INSERT INTO utilisateurs "
            "(nom, prenom, email, login, mot_de_passe, role, service_id, actif) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            [data.get('nom'), data.get('prenom'), data.get('email'),
             data['login'], hashed,
             data.get('role', 'lecteur'),
             data.get('service_id') or None,
             data.get('actif', True)]
        )

    def update_user(self, user_id: int, data: dict):
        if data.get('mot_de_passe'):
            if len(data['mot_de_passe']) < 8:
                raise ValueError('Le mot de passe doit contenir au moins 8 caractères')
            hashed = bcrypt.hashpw(
                data['mot_de_passe'].encode('utf-8'), bcrypt.gensalt()
            ).decode('utf-8')
            self.db.execute(
                "UPDATE utilisateurs SET nom=%s, prenom=%s, email=%s, login=%s, "
                "mot_de_passe=%s, role=%s, service_id=%s, actif=%s WHERE id=%s",
                [data.get('nom'), data.get('prenom'), data.get('email'),
                 data.get('login'), hashed, data.get('role'),
                 data.get('service_id') or None, data.get('actif', True), user_id]
            )
        else:
            self.db.execute(
                "UPDATE utilisateurs SET nom=%s, prenom=%s, email=%s, login=%s, "
                "role=%s, service_id=%s, actif=%s WHERE id=%s",
                [data.get('nom'), data.get('prenom'), data.get('email'),
                 data.get('login'), data.get('role'),
                 data.get('service_id') or None, data.get('actif', True), user_id]
            )

    def delete_user(self, user_id: int):
        self.db.execute("DELETE FROM utilisateurs WHERE id=%s", [user_id])

    def set_active(self, user_id: int, actif: bool):
        self.db.execute(
            "UPDATE utilisateurs SET actif=%s WHERE id=%s", [actif, user_id]
        )
