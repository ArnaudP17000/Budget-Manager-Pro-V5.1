"""
cleanup_db_v5.py - Nettoyage base Budget Manager V5
Supprime les tables et vues heritees de V4 plus utilisees.

Usage:
  python cleanup_db_v5.py           -> apercu (dry-run)
  python cleanup_db_v5.py --execute -> nettoyage reel
"""

import sqlite3, shutil, os, sys, logging
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "budget_manager.db")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("cleanup_db_v5.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger("cleanup_db_v5")

TABLES_TO_DROP = [
    ("budget_lines",    "Lignes budget V4 -> remplacees par lignes_budgetaires"),
    ("bons_commandes",  "Bons commande V4 -> remplaces par bons_commande"),
    ("depenses",        "Depenses V4 -> remplacees par lignes_budgetaires + BC"),
    ("marches",         "Marches V4 -> remplaces par contrats"),
    ("missions",        "Missions V4 -> non utilisees en V5"),
    ("projets_old",     "Sauvegarde projets migration -> inutile"),
    ("services_old",    "Sauvegarde services migration -> inutile"),
    ("equipe_membres",  "Membres equipe V4 -> remplaces par projet_membres"),
    ("chapitres_m57",   "Referentiel chapitres M57 V4 -> non utilise en V5"),
    ("fonctions_m57",   "Referentiel fonctions M57 V4 -> non utilise en V5"),
    ("engagements",     "Engagements V4 -> remplaces par bons_commande"),
    ("avenants",        "Avenants contrats V4 -> non utilises en V5"),
    ("cahiers_charges", "Cahiers charges V4 -> non utilises en V5"),
    ("commentaires",    "Commentaires V4 -> non utilises en V5"),
    ("collections",     "Collections V4 -> non utilisees en V5"),
    ("budgets_backup",  "Sauvegarde budgets migration V4->V5 -> inutile"),
    ("lignes_backup",   "Sauvegarde lignes migration V4->V5 -> inutile"),
    ("bc_backup",       "Sauvegarde BC migration V4->V5 -> inutile"),
]

VIEWS_TO_DROP = [
    ("v_budget_summary", "Vue synthese budget V4 -> remplacee par v_synthese_budget"),
    ("v_bc_details",     "Vue detail BC V4 -> remplacee par v_bons_commande"),
    ("v_depenses",       "Vue depenses V4 -> non utilisee en V5"),
    ("v_marches",        "Vue marches V4 -> non utilisee en V5"),
    ("v_missions",       "Vue missions V4 -> non utilisee en V5"),
    ("v_engagements",    "Vue engagements V4 -> non utilisee en V5"),
]

def get_existing(conn, obj_type):
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type=?", (obj_type,)
    ).fetchall()
    return {r[0].lower() for r in rows}

def row_count(conn, table):
    try:
        return conn.execute("SELECT COUNT(*) FROM [%s]" % table).fetchone()[0]
    except Exception:
        return 0

def backup_db(db_path):
    stamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = db_path.replace(".db", "_backup_avant_cleanup_%s.db" % stamp)
    shutil.copy2(db_path, backup)
    return backup

def run_cleanup(execute=False):
    if not os.path.exists(DB_PATH):
        logger.error("Base introuvable : %s" % DB_PATH)
        sys.exit(1)

    conn           = sqlite3.connect(DB_PATH)
    existing_tbl   = get_existing(conn, "table")
    existing_view  = get_existing(conn, "view")

    sep = "=" * 65
    print("\n" + sep)
    print("  BUDGET MANAGER V5 - Nettoyage base de donnees")
    print("  Mode : %s" % ("EXECUTION REELLE" if execute else "DRY-RUN (apercu)"))
    print(sep)

    tables_found, tables_absent = [], []
    print("\n TABLES A SUPPRIMER :")
    print("  %-25s %8s  %s" % ("Table", "Lignes", "Statut"))
    print("  %s %s  %s" % ("-"*25, "-"*8, "-"*20))
    for table, raison in TABLES_TO_DROP:
        if table.lower() in existing_tbl:
            nb = row_count(conn, table)
            tables_found.append((table, raison, nb))
            flag = "CONTIENT DONNEES" if nb > 0 else "vide"
            print("  %-25s %8d  %s" % (table, nb, flag))
        else:
            tables_absent.append(table)
            print("  %-25s %8s  absente (deja nettoyee)" % (table, "-"))

    views_found, views_absent = [], []
    print("\n VUES A SUPPRIMER :")
    for view, raison in VIEWS_TO_DROP:
        if view.lower() in existing_view:
            views_found.append((view, raison))
            print("  %-30s  presente -> sera supprimee" % view)
        else:
            views_absent.append(view)
            print("  %-30s  absente (deja nettoyee)" % view)

    print("\n RESUME :")
    print("  Tables a supprimer   : %d" % len(tables_found))
    print("  Tables deja absentes : %d" % len(tables_absent))
    print("  Vues a supprimer     : %d" % len(views_found))
    print("  Vues deja absentes   : %d" % len(views_absent))

    tables_data = [(t, r, n) for t, r, n in tables_found if n > 0]
    if tables_data:
        print("\n  ATTENTION - Tables avec donnees qui seront supprimees :")
        for t, r, n in tables_data:
            print("    * %s (%d ligne%s) : %s" % (t, n, "s" if n > 1 else "", r))

    conn.close()

    if not execute:
        print("\n" + sep)
        print("  DRY-RUN : aucune modification effectuee.")
        print("  Pour appliquer : python cleanup_db_v5.py --execute")
        print(sep + "\n")
        return

    if not tables_found and not views_found:
        print("\n  Base deja propre - rien a supprimer.\n")
        return

    if tables_data:
        rep = input("\n  Confirmer la suppression des donnees ? (oui/non) : ").strip().lower()
        if rep not in ("oui", "o", "yes", "y"):
            print("  Annule.\n")
            return

    backup_path = backup_db(DB_PATH)
    logger.info("Sauvegarde : %s" % backup_path)
    print("\n  Sauvegarde : %s" % os.path.basename(backup_path))

    conn     = sqlite3.connect(DB_PATH)
    errors   = []
    done     = []

    for view, raison in views_found:
        try:
            conn.execute("DROP VIEW IF EXISTS [%s]" % view)
            conn.commit()
            done.append(("VUE", view))
            logger.info("Vue supprimee : %s" % view)
        except Exception as e:
            errors.append("Vue %s : %s" % (view, e))
            logger.error("Erreur vue %s : %s" % (view, e))

    for table, raison, nb in tables_found:
        try:
            conn.execute("DROP TABLE IF EXISTS [%s]" % table)
            conn.commit()
            done.append(("TABLE", table))
            logger.info("Table supprimee : %s (%d lignes)" % (table, nb))
        except Exception as e:
            errors.append("Table %s : %s" % (table, e))
            logger.error("Erreur table %s : %s" % (table, e))

    print("  VACUUM en cours (compactage)...")
    try:
        conn.execute("VACUUM")
        conn.commit()
        logger.info("VACUUM execute")
    except Exception as e:
        logger.warning("VACUUM echoue : %s" % e)

    conn.close()

    taille_avant = os.path.getsize(backup_path)
    taille_apres = os.path.getsize(DB_PATH)
    gain = taille_avant - taille_apres

    print("\n" + sep)
    print("  NETTOYAGE TERMINE")
    print(sep)
    print("  Supprimes : %d objet(s)" % len(done))
    for typ, nom in done:
        print("    [%s] %s" % (typ, nom))
    print("\n  Taille avant  : %.1f Ko" % (taille_avant / 1024))
    print("  Taille apres  : %.1f Ko" % (taille_apres  / 1024))
    print("  Gain          : %.1f Ko" % (gain / 1024))
    if errors:
        print("\n  Erreurs (%d) :" % len(errors))
        for e in errors:
            print("    * %s" % e)
    print("  Log           : cleanup_db_v5.log")
    print("  Sauvegarde    : %s" % os.path.basename(backup_path))
    print(sep + "\n")


if __name__ == "__main__":
    execute = "--execute" in sys.argv
    run_cleanup(execute=execute)
