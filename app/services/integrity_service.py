"""
integrity_service.py — Intégrité référentielle et journal d'audit
"""
import logging
from datetime import datetime
from app.services.database_service import db_service

logger = logging.getLogger(__name__)


def _d(row):
    if row is None: return None
    return dict(row) if hasattr(row, 'keys') else row


class IntegrityService:
    """
    Vérifie les contraintes avant suppression et journalise les événements métier.
    """

    def __init__(self):
        self.db = db_service
        self._ensure_audit_table()

    def _ensure_audit_table(self):
        """
        Cree ou migre la table audit_log.
        Gere les bases avec table_name (ancienne version) ou objet_type (nouvelle).
        """
        conn = self.db.get_connection()
        try:
            cols_rows = conn.execute("PRAGMA table_info(audit_log)").fetchall()
            cols_existantes = {r[1] for r in cols_rows}

            if not cols_existantes:
                # Table absente -> creer proprement
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS audit_log (
                        id           INTEGER PRIMARY KEY AUTOINCREMENT,
                        objet_type   TEXT,
                        objet_id     INTEGER,
                        action       TEXT NOT NULL,
                        detail       TEXT,
                        valeur_avant TEXT,
                        valeur_apres TEXT,
                        utilisateur  TEXT,
                        date_action  TEXT DEFAULT (datetime('now'))
                    )
                """)
                conn.commit()
                logger.info("audit_log cree")
                return

            # Ancienne table avec table_name -> migrer vers objet_type
            if 'table_name' in cols_existantes and 'objet_type' not in cols_existantes:
                try:
                    conn.execute("""
                        CREATE TABLE audit_log_new (
                            id           INTEGER PRIMARY KEY AUTOINCREMENT,
                            objet_type   TEXT,
                            objet_id     INTEGER,
                            action       TEXT NOT NULL,
                            detail       TEXT,
                            valeur_avant TEXT,
                            valeur_apres TEXT,
                            utilisateur  TEXT,
                            date_action  TEXT DEFAULT (datetime('now'))
                        )
                    """)
                    # Copier les donnees en mappant table_name -> objet_type
                    conn.execute("""
                        INSERT INTO audit_log_new
                            (id, objet_type, objet_id, action, detail,
                             valeur_avant, valeur_apres, utilisateur, date_action)
                        SELECT
                            id,
                            COALESCE(table_name, ''),
                            record_id,
                            COALESCE(action, 'ACTION'),
                            detail,
                            NULL, NULL,
                            utilisateur,
                            COALESCE(date_action, created_at, datetime('now'))
                        FROM audit_log
                    """)
                    conn.execute("DROP TABLE audit_log")
                    conn.execute("ALTER TABLE audit_log_new RENAME TO audit_log")
                    conn.commit()
                    logger.info("audit_log migre (table_name -> objet_type)")
                except Exception as e:
                    conn.rollback()
                    logger.warning("Migration audit_log echouee : %s", e)
                    # Plan B : juste ajouter la colonne objet_type
                    try:
                        conn.execute("ALTER TABLE audit_log ADD COLUMN objet_type TEXT")
                        conn.execute("UPDATE audit_log SET objet_type = table_name WHERE objet_type IS NULL")
                        conn.commit()
                        logger.info("audit_log : colonne objet_type ajoutee (plan B)")
                    except Exception as e2:
                        logger.warning("Plan B audit_log : %s", e2)
                return

            # Ajouter les colonnes manquantes si necessaire
            colonnes_requises = {
                'objet_type':   'TEXT',
                'objet_id':     'INTEGER',
                'action':       'TEXT',
                'detail':       'TEXT',
                'valeur_avant': 'TEXT',
                'valeur_apres': 'TEXT',
                'utilisateur':  'TEXT',
                'date_action':  "TEXT DEFAULT (datetime('now'))",
            }
            for col, typ in colonnes_requises.items():
                if col not in cols_existantes:
                    try:
                        conn.execute(f"ALTER TABLE audit_log ADD COLUMN {col} {typ}")
                        logger.info("audit_log : colonne '%s' ajoutee", col)
                    except Exception as e:
                        logger.warning("audit_log ALTER %s : %s", col, e)
            conn.commit()

        except Exception as e:
            logger.warning("_ensure_audit_table : %s", e)

    # =========================================================================
    # VÉRIFICATIONS AVANT SUPPRESSION
    # =========================================================================

    def check_fournisseur(self, fournisseur_id):
        """Bloque si le fournisseur a des contrats actifs ou des BC non annulés."""
        conn = self.db.get_connection()
        errors = []

        n_contrats = _d(conn.execute("""
            SELECT COUNT(*) as n FROM contrats
            WHERE fournisseur_id=? AND statut IN ('ACTIF','RECONDUIT','BROUILLON')
        """, (fournisseur_id,)).fetchone())
        if n_contrats and n_contrats['n'] > 0:
            errors.append(f"{n_contrats['n']} contrat(s) actif(s) rattaché(s)")

        n_bc = _d(conn.execute("""
            SELECT COUNT(*) as n FROM bons_commande
            WHERE fournisseur_id=? AND statut NOT IN ('ANNULE','SOLDE')
        """, (fournisseur_id,)).fetchone())
        if n_bc and n_bc['n'] > 0:
            errors.append(f"{n_bc['n']} bon(s) de commande actif(s)")

        return (True, None) if not errors else (False, "Impossible de supprimer ce fournisseur :\n• " + "\n• ".join(errors))

    def check_contrat(self, contrat_id):
        """Bloque si le contrat a des BC rattachés non annulés."""
        conn = self.db.get_connection()
        n = _d(conn.execute("""
            SELECT COUNT(*) as n FROM bons_commande
            WHERE contrat_id=? AND statut NOT IN ('ANNULE')
        """, (contrat_id,)).fetchone())
        if n and n['n'] > 0:
            return False, f"Impossible de supprimer ce contrat :\n• {n['n']} bon(s) de commande rattaché(s)\n\nAnnulez d'abord les BC avant de supprimer le contrat."
        return True, None

    def check_ligne_budgetaire(self, ligne_id):
        """Bloque si la ligne a des BC imputés ou validés."""
        conn = self.db.get_connection()
        n = _d(conn.execute("""
            SELECT COUNT(*) as n FROM bons_commande
            WHERE ligne_budgetaire_id=? AND statut IN ('VALIDE','IMPUTE','SOLDE')
        """, (ligne_id,)).fetchone())
        if n and n['n'] > 0:
            return False, f"Impossible de supprimer cette ligne budgétaire :\n• {n['n']} BC validé(s) ou imputé(s) sur cette ligne\n\nAnnulez ou désimputez les BC avant de supprimer la ligne."
        return True, None

    def check_application(self, application_id):
        """Bloque si l'application est rattachée à des lignes budgétaires ou BC actifs."""
        conn = self.db.get_connection()
        errors = []

        n_lb = _d(conn.execute("""
            SELECT COUNT(*) as n FROM lignes_budgetaires
            WHERE application_id=? AND statut='ACTIF'
        """, (application_id,)).fetchone())
        if n_lb and n_lb['n'] > 0:
            errors.append(f"{n_lb['n']} ligne(s) budgétaire(s) active(s)")

        n_bc = _d(conn.execute("""
            SELECT COUNT(*) as n FROM bons_commande
            WHERE application_id=? AND statut NOT IN ('ANNULE','SOLDE')
        """, (application_id,)).fetchone())
        if n_bc and n_bc['n'] > 0:
            errors.append(f"{n_bc['n']} bon(s) de commande actif(s)")

        return (True, None) if not errors else (False, "Impossible de supprimer cette application :\n• " + "\n• ".join(errors))

    def check_entite(self, entite_id):
        """Bloque si l'entité a des budgets non clôturés."""
        conn = self.db.get_connection()
        n = _d(conn.execute("""
            SELECT COUNT(*) as n FROM budgets_annuels
            WHERE entite_id=? AND statut NOT IN ('CLOTURE')
        """, (entite_id,)).fetchone())
        if n and n['n'] > 0:
            return False, f"Impossible de supprimer cette entité :\n• {n['n']} budget(s) non clôturé(s)\n\nClôturez tous les budgets de l'entité avant de la supprimer."
        return True, None

    # =========================================================================
    # JOURNAL D'AUDIT
    # =========================================================================

    def log(self, objet_type, objet_id, action, detail=None, ancien=None, nouveau=None):
        """
        Enregistre un événement dans le journal d'audit.
        objet_type : 'BC' | 'CONTRAT' | 'BUDGET' | 'LIGNE' | 'FOURNISSEUR' | ...
        action     : 'STATUT_CHANGE' | 'IMPUTATION' | 'RECONDUCTION' | 'VOTE' | 'SUPPRESSION' | ...
        """
        try:
            conn = self.db.get_connection()
            conn.execute("""
                INSERT INTO audit_log
                    (objet_type, objet_id, action, detail, valeur_avant, valeur_apres, date_action)
                VALUES (?,?,?,?,?,?,?)
            """, (
                objet_type, objet_id, action,
                detail or '',
                str(ancien) if ancien is not None else None,
                str(nouveau) if nouveau is not None else None,
                datetime.now().isoformat()
            ))
            conn.commit()
        except Exception as e:
            logger.warning(f"Audit log échoué ({objet_type}/{action}) : {e}")

    def get_logs(self, objet_type=None, objet_id=None, limit=200):
        """Récupère les entrées du journal."""
        conds, params = [], []
        if objet_type:
            conds.append("objet_type=?"); params.append(objet_type)
        if objet_id:
            conds.append("objet_id=?"); params.append(objet_id)
        where = "WHERE " + " AND ".join(conds) if conds else ""
        rows = self.db.fetch_all(f"""
            SELECT * FROM audit_log {where}
            ORDER BY date_action DESC LIMIT ?
        """, params + [limit])
        return [_d(r) for r in rows] if rows else []


integrity_service = IntegrityService()
