"""
Point d'entrée — Budget Manager Pro V5
"""
import sys
import os
import shutil
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from app.ui.main_window import MainWindow
from config.settings import APP_TITLE

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'data', 'budget_manager.db')
BK_DIR   = os.path.join(BASE_DIR, 'backups')
MAX_BACKUPS = 7   # garder les 7 dernières sauvegardes auto


def auto_backup():
    """Sauvegarde automatique au lancement — conserve les MAX_BACKUPS dernières."""
    if not os.path.exists(DB_PATH):
        return
    os.makedirs(BK_DIR, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    dest  = os.path.join(BK_DIR, f'auto_backup_{stamp}.db')
    try:
        shutil.copy2(DB_PATH, dest)
        logger.info(f"✅ Sauvegarde auto : {os.path.basename(dest)}")
    except Exception as e:
        logger.warning(f"⚠️ Sauvegarde auto échouée : {e}")
        return

    # Rotation : supprimer les plus anciennes
    backups = sorted([
        f for f in os.listdir(BK_DIR)
        if f.startswith('auto_backup_') and f.endswith('.db')
    ])
    while len(backups) > MAX_BACKUPS:
        old = os.path.join(BK_DIR, backups.pop(0))
        try:
            os.remove(old)
            logger.info(f"🗑️  Ancienne sauvegarde supprimée : {os.path.basename(old)}")
        except Exception:
            pass


def update_contrats_expires():
    """Passe automatiquement en EXPIRE les contrats dont la date_fin est dépassée."""
    import sqlite3
    try:
        conn = sqlite3.connect(DB_PATH)
        cur  = conn.cursor()
        cur.execute("""
            UPDATE contrats
            SET statut = 'EXPIRE', date_maj = datetime('now')
            WHERE statut IN ('ACTIF', 'RECONDUIT')
            AND date_fin < date('now')
        """)
        n = cur.rowcount
        conn.commit()
        conn.close()
        if n > 0:
            logger.info(f"⚠️  {n} contrat(s) passé(s) en EXPIRE automatiquement")
    except Exception as e:
        logger.warning(f"Mise à jour statuts contrats : {e}")


def main():
    try:
        # Sauvegarde auto (#2)
        auto_backup()

        # Statuts contrats auto (#7)
        update_contrats_expires()

        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        app = QApplication(sys.argv)
        app.setApplicationName(APP_TITLE)

        window = MainWindow()
        window.show()

        sys.exit(app.exec_())
    except Exception as e:
        logging.error(f"Erreur lancement : {e}", exc_info=True)
        print(f"ERREUR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
