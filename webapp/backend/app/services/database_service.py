import os
import logging
import psycopg2
import psycopg2.extras
import psycopg2.pool

logger = logging.getLogger(__name__)

DB_HOST = os.getenv('DB_HOST', 'postgre.addict-gamers.fr')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'budget_manager')
DB_USER = os.getenv('DB_USER', 'admin')
DB_PASS = os.getenv('DB_PASS', '')

_POOL_MIN = int(os.getenv('DB_POOL_MIN', '2'))
_POOL_MAX = int(os.getenv('DB_POOL_MAX', '10'))


class DatabaseService:
    """
    Service d'accès PostgreSQL basé sur un ThreadedConnectionPool.
    Thread-safe : chaque opération emprunte une connexion du pool et la restitue.
    """
    _pool: psycopg2.pool.ThreadedConnectionPool | None = None

    def __new__(cls):
        # Singleton sur la classe, pas sur la connexion
        if not hasattr(cls, '_instance'):
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if DatabaseService._pool is None:
            self._init_pool()

    def _init_pool(self):
        try:
            DatabaseService._pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=_POOL_MIN,
                maxconn=_POOL_MAX,
                host=DB_HOST, port=int(DB_PORT),
                dbname=DB_NAME, user=DB_USER, password=DB_PASS,
                connect_timeout=10,
                options='-c statement_timeout=20000',
            )
            logger.info(f"Pool PostgreSQL initialisé ({_POOL_MIN}–{_POOL_MAX} connexions)")
        except Exception as e:
            logger.error(f"Erreur initialisation pool PostgreSQL: {e}")
            raise

    def _get_conn(self):
        """Emprunte une connexion au pool, réinitialise si nécessaire."""
        if DatabaseService._pool is None:
            self._init_pool()
        try:
            return DatabaseService._pool.getconn()
        except psycopg2.pool.PoolError:
            # Pool épuisé ou fermé — forcer la réinitialisation
            logger.warning("Pool épuisé ou fermé, réinitialisation…")
            DatabaseService._pool = None
            self._init_pool()
            return DatabaseService._pool.getconn()

    def _put_conn(self, conn, broken=False):
        """Restitue la connexion au pool."""
        try:
            DatabaseService._pool.putconn(conn, close=broken)
        except Exception:
            pass

    def fetch_all(self, query, params=None):
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params or [])
                rows = [dict(r) for r in cur.fetchall()]
        except Exception:
            try:
                conn.rollback()
            except Exception:
                self._put_conn(conn, broken=True)
                return None  # type: ignore
            self._put_conn(conn)
            raise
        else:
            self._put_conn(conn)
        return rows

    def fetch_one(self, query, params=None):
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params or [])
                row = cur.fetchone()
                result = dict(row) if row else None
        except Exception:
            try:
                conn.rollback()
            except Exception:
                self._put_conn(conn, broken=True)
                return None
            self._put_conn(conn)
            raise
        else:
            self._put_conn(conn)
        return result

    def execute(self, query, params=None):
        """Exécute une requête d'écriture (INSERT/UPDATE/DELETE/DDL) et commit."""
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(query, params or [])
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                self._put_conn(conn, broken=True)
                raise
            self._put_conn(conn)
            raise
        else:
            self._put_conn(conn)

    def execute_returning(self, query, params=None):
        """Exécute un INSERT ... RETURNING et retourne la première ligne."""
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(query, params or [])
                result = cur.fetchone()
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                self._put_conn(conn, broken=True)
                raise
            self._put_conn(conn)
            raise
        else:
            self._put_conn(conn)
        return result


# Singleton partagé entre tous les services
db_service = DatabaseService()
