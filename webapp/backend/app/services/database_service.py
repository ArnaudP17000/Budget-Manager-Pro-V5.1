import os
import logging
import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

DB_HOST = os.getenv('DB_HOST', 'postgre.addict-gamers.fr')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'budget_manager')
DB_USER = os.getenv('DB_USER', 'admin')
DB_PASS = os.getenv('DB_PASS', 'ROOtsradics77')


class DatabaseService:
    _instance = None
    _connection = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._connection is None or self._connection.closed:
            self._connect()

    def _connect(self):
        try:
            self._connection = psycopg2.connect(
                host=DB_HOST, port=int(DB_PORT),
                dbname=DB_NAME, user=DB_USER, password=DB_PASS
            )
            logger.info("Connexion PostgreSQL établie")
        except Exception as e:
            logger.error(f"Erreur connexion PostgreSQL: {e}")
            raise

    def get_connection(self):
        if self._connection is None or self._connection.closed:
            self._connect()
        return self._connection

    def _reset_connection(self):
        """Force la fermeture et réinitialise la connexion."""
        try:
            if self._connection and not self._connection.closed:
                self._connection.close()
        except Exception:
            pass
        DatabaseService._connection = None

    def fetch_all(self, query, params=None):
        for attempt in range(2):
            conn = self.get_connection()
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(query, params or [])
                    return [dict(r) for r in cur.fetchall()]
            except psycopg2.InterfaceError:
                self._reset_connection()
                if attempt == 1:
                    raise
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    self._reset_connection()
                raise

    def fetch_one(self, query, params=None):
        for attempt in range(2):
            conn = self.get_connection()
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(query, params or [])
                    row = cur.fetchone()
                    return dict(row) if row else None
            except psycopg2.InterfaceError:
                self._reset_connection()
                if attempt == 1:
                    raise
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    self._reset_connection()
                raise

    def execute(self, query, params=None):
        """Exécute une requête d'écriture (INSERT/UPDATE/DELETE) et commit."""
        for attempt in range(2):
            conn = self.get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute(query, params or [])
                conn.commit()
                return
            except psycopg2.InterfaceError:
                self._reset_connection()
                if attempt == 1:
                    raise
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    self._reset_connection()
                raise

    def execute_returning(self, query, params=None):
        """Exécute un INSERT ... RETURNING et retourne la première ligne."""
        for attempt in range(2):
            conn = self.get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute(query, params or [])
                    result = cur.fetchone()
                conn.commit()
                return result
            except psycopg2.InterfaceError:
                self._reset_connection()
                if attempt == 1:
                    raise
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    self._reset_connection()
                raise


# Singleton partagé entre tous les services
db_service = DatabaseService()
