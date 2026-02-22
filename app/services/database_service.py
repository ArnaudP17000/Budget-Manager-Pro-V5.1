"""
Service de gestion de la base de données SQLite.
"""
import sqlite3
import logging
from pathlib import Path
from config.settings import DATABASE_PATH, DATA_DIR
from app.database.schema import init_database

logger = logging.getLogger(__name__)

class DatabaseService:
    """Service singleton pour gérer la connexion à la base de données."""
    
    _instance = None
    _connection = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._connection is None:
            self._connect()
    
    def _connect(self):
        """Établit la connexion à la base de données."""
        try:
            # Créer le dossier data s'il n'existe pas
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            
            # Connexion à la base
            self._connection = sqlite3.connect(
                str(DATABASE_PATH),
                check_same_thread=False
            )
            self._connection.row_factory = sqlite3.Row
            
            # Activer les foreign keys
            self._connection.execute("PRAGMA foreign_keys = ON")
            
            # Initialiser le schéma
            init_database(self._connection)
            
            logger.info(f"Base de données initialisée: {DATABASE_PATH}")
        except Exception as e:
            logger.error(f"Erreur connexion base de données: {e}")
            raise
    
    def get_connection(self):
        """Retourne la connexion à la base de données."""
        if self._connection is None:
            self._connect()
        return self._connection
    
    def execute(self, query, params=None):
        """Exécute une requête SQL."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            return cursor
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            import traceback
            logger.error(
                "ERREUR SQL: {}\nQUERY: {}\nPARAMS: {}\n{}".format(
                    e, query[:500], params, traceback.format_exc()
                )
            )
            raise
    
    def _log_sql_error(self, method, e, query, params):
        import traceback
        logger.error(
            "ERREUR {}: {}\nQUERY: {}\nPARAMS: {}\n{}".format(
                method, e, query[:500], params, traceback.format_exc()
            )
        )

    def fetch_one(self, query, params=None):
        """Exécute une requête et retourne un résultat."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params) if params else cursor.execute(query)
            return cursor.fetchone()
        except Exception as e:
            self._log_sql_error("fetch_one", e, query, params)
            raise

    def fetch_all(self, query, params=None):
        """Exécute une requête et retourne tous les résultats."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params) if params else cursor.execute(query)
            return cursor.fetchall()
        except Exception as e:
            self._log_sql_error("fetch_all", e, query, params)
            raise
    
    def insert(self, table, data):
        """Insert data into a table."""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        cursor = self.execute(query, tuple(data.values()))
        return cursor.lastrowid
    
    def update(self, table, data, where_clause, where_params):
        """Update data in a table."""
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
        params = tuple(data.values()) + tuple(where_params)
        self.execute(query, params)
    
    def delete(self, table, where_clause, where_params):
        """Delete data from a table."""
        query = f"DELETE FROM {table} WHERE {where_clause}"
        self.execute(query, where_params)
    
    def execute_query(self, query, params=None):
        """
        Exécute une requête SELECT et retourne tous les résultats.
        Alias pour fetch_all pour compatibilité avec certains services.
        """
        return self.fetch_all(query, params)
    
    def execute_update(self, query, params=None):
        """
        Exécute une requête INSERT/UPDATE/DELETE et retourne le lastrowid.
        Pour les INSERT, retourne l'ID de la ligne insérée.
        """
        cursor = self.execute(query, params)
        return cursor.lastrowid
    
    def close(self):
        """Ferme la connexion à la base de données."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("Connexion base de données fermée")

# Instance globale
db_service = DatabaseService()
