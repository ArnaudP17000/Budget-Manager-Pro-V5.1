"""
cleanup_py_v5.py - Nettoyage des fichiers .py orphelins Budget Manager V5
=========================================================================
Supprime (apres sauvegarde) les fichiers Python herites de V4
qui ne sont plus importes ni utilises dans le code V5.

Usage:
  python cleanup_py_v5.py           -> apercu (dry-run)
  python cleanup_py_v5.py --execute -> suppression reelle
"""

import os, sys, shutil, logging, re
from datetime import datetime

APP_DIR  = os.path.dirname(os.path.abspath(__file__))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("cleanup_py_v5.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger("cleanup_py_v5")

# ── Fichiers orphelins confirmes ───────────────────────────────────────────────

FILES_TO_REMOVE = [
    # Services V4 remplaces
    (
        os.path.join("app", "services", "portefeuille_service.py"),
        "Service portefeuilles V4 -> remplace par budget_v5_service.py",
        157,
    ),
    (
        os.path.join("app", "services", "reporting_service.py"),
        "Reporting V4 -> remplace par export_service.py",
        260,
    ),
    # Dialogs V4 remplaces
    (
        os.path.join("app", "ui", "dialogs", "bdc_dialog.py"),
        "Dialog bons de commande V4 -> remplace par bon_commande_view.py",
        320,
    ),
    (
        os.path.join("app", "ui", "dialogs", "todo_dialog.py"),
        "Dialog todos V4 -> non utilise en V5",
        9,
    ),
    # Widgets V4 non utilises
    (
        os.path.join("app", "ui", "widgets", "alert_widget.py"),
        "Widget alertes V4 -> non utilise en V5",
        217,
    ),
    (
        os.path.join("app", "ui", "widgets", "kpi_widget.py"),
        "Widget KPI V4 -> non utilise en V5",
        247,
    ),
    (
        os.path.join("app", "ui", "widgets", "meteo_widget.py"),
        "Widget meteo V4 -> non utilise en V5",
        154,
    ),
    (
        os.path.join("app", "ui", "widgets", "notification_widget.py"),
        "Widget notifications V4 -> non utilise en V5",
        203,
    ),
    (
        os.path.join("app", "ui", "widgets", "project_widget.py"),
        "Widget projets V4 -> non utilise en V5",
        167,
    ),
    (
        os.path.join("app", "ui", "widgets", "widget_manager.py"),
        "Gestionnaire de widgets V4 -> non utilise en V5",
        696,
    ),
]

# ── Verification de securite ───────────────────────────────────────────────────

def is_still_imported(rel_path, app_dir):
    """Verifie si un fichier est encore importe quelque part dans le code."""
    short = os.path.basename(rel_path).replace(".py", "")
    module = rel_path.replace(os.sep, ".").replace(".py", "")

    for root, dirs, files in os.walk(app_dir):
        for f in files:
            if not f.endswith(".py"):
                continue
            fpath = os.path.join(root, f)
            # Ignorer le fichier lui-meme
            if os.path.relpath(fpath, app_dir) == rel_path:
                continue
            content = open(fpath, errors="ignore").read()
            # Chercher import ou from ... import
            if re.search(r'(?:import|from)\s+[^\n]*\b' + re.escape(short) + r'\b', content):
                return fpath
    return None

# ── Sauvegarde ────────────────────────────────────────────────────────────────

def backup_files(files_to_backup, app_dir):
    stamp      = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(app_dir, "backup_py_v4_" + stamp)
    os.makedirs(backup_dir, exist_ok=True)
    for rel_path, _, _ in files_to_backup:
        src = os.path.join(app_dir, rel_path)
        if os.path.exists(src):
            dst_dir = os.path.join(backup_dir, os.path.dirname(rel_path))
            os.makedirs(dst_dir, exist_ok=True)
            shutil.copy2(src, os.path.join(dst_dir, os.path.basename(rel_path)))
    return backup_dir

# ── Main ──────────────────────────────────────────────────────────────────────

def run_cleanup(execute=False):
    sep = "=" * 65

    print("\n" + sep)
    print("  BUDGET MANAGER V5 - Nettoyage fichiers Python")
    print("  Mode : %s" % ("EXECUTION REELLE" if execute else "DRY-RUN (apercu)"))
    print(sep)

    presents   = []
    absents    = []
    surprises  = []   # fichiers marques orphelins mais encore importes quelque part

    total_lignes = 0

    print("\n FICHIERS A SUPPRIMER :\n")
    print("  %-42s %6s  %s" % ("Fichier", "Lignes", "Statut"))
    print("  %s %s  %s" % ("-"*42, "-"*6, "-"*22))

    for rel_path, raison, lignes_ref in FILES_TO_REMOVE:
        full_path = os.path.join(APP_DIR, rel_path)

        if not os.path.exists(full_path):
            absents.append(rel_path)
            print("  %-42s %6s  absent (deja supprime)" % (rel_path, "-"))
            continue

        # Verif securite : encore importe ?
        ref_file = is_still_imported(rel_path, APP_DIR)
        if ref_file:
            ref_short = os.path.relpath(ref_file, APP_DIR)
            surprises.append((rel_path, ref_short))
            print("  %-42s %6d  ATTENTION : importe dans %s" % (
                rel_path, lignes_ref, os.path.basename(ref_short)))
            continue

        nb_lignes = len(open(full_path, errors="ignore").readlines())
        presents.append((rel_path, raison, nb_lignes))
        total_lignes += nb_lignes
        print("  %-42s %6d  -> a supprimer" % (rel_path, nb_lignes))

    print("\n RESUME :")
    print("  Fichiers a supprimer  : %d  (%d lignes au total)" % (len(presents), total_lignes))
    print("  Deja absents          : %d" % len(absents))
    if surprises:
        print("  CONSERVES (encore importes) : %d" % len(surprises))
        for rel, ref in surprises:
            print("    * %s <- %s" % (os.path.basename(rel), ref))

    if not execute:
        print("\n" + sep)
        print("  DRY-RUN : aucune modification effectuee.")
        print("  Pour appliquer : python cleanup_py_v5.py --execute")
        print(sep + "\n")
        return

    if not presents:
        print("\n  Rien a supprimer - code deja propre.\n")
        return

    # Sauvegarde
    backup_dir = backup_files(presents, APP_DIR)
    logger.info("Sauvegarde dans : %s" % backup_dir)
    print("\n  Sauvegarde : %s" % os.path.basename(backup_dir))

    # Suppression
    errors  = []
    done    = []

    for rel_path, raison, nb_lignes in presents:
        full_path = os.path.join(APP_DIR, rel_path)
        try:
            os.remove(full_path)
            done.append((rel_path, nb_lignes))
            logger.info("Supprime : %s (%d lignes)" % (rel_path, nb_lignes))
        except Exception as e:
            errors.append("%s : %s" % (rel_path, e))
            logger.error("Erreur %s : %s" % (rel_path, e))

    # Nettoyer les __pycache__ associes
    cleaned_pycache = 0
    for rel_path, _ in done:
        full_path = os.path.join(APP_DIR, rel_path)
        pycache   = os.path.join(os.path.dirname(full_path), "__pycache__")
        if os.path.exists(pycache):
            basename = os.path.basename(full_path).replace(".py", "")
            for f in os.listdir(pycache):
                if f.startswith(basename + "."):
                    try:
                        os.remove(os.path.join(pycache, f))
                        cleaned_pycache += 1
                    except Exception:
                        pass

    print("\n" + sep)
    print("  NETTOYAGE TERMINE")
    print(sep)
    print("  Supprimes : %d fichier(s)" % len(done))
    for rel, nb in done:
        print("    - %s (%d lignes)" % (os.path.basename(rel), nb))
    print("  Cache .pyc nettoyes : %d" % cleaned_pycache)
    total_done = sum(nb for _, nb in done)
    print("  Lignes supprimees   : %d" % total_done)
    if errors:
        print("  Erreurs (%d) :" % len(errors))
        for e in errors:
            print("    * %s" % e)
    print("  Log       : cleanup_py_v5.log")
    print("  Sauvegarde: %s" % os.path.basename(backup_dir))
    print(sep + "\n")


if __name__ == "__main__":
    execute = "--execute" in sys.argv
    run_cleanup(execute=execute)
