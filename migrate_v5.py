"""
migrate_v5.py — Migration Budget Manager Pro V4 → V5
Exécuter UNE SEULE FOIS depuis la racine du projet :
    python migrate_v5.py

Ce script :
  1. Sauvegarde l'ancienne base
  2. Crée les nouvelles tables sans supprimer les anciennes
  3. Migre les données récupérables (fournisseurs, projets, contrats, BC)
  4. Crée les 2 entités et un budget 2026 vide pour démarrer
"""

import sqlite3
import shutil
import os
import sys
from datetime import datetime, date

# ── Chemins ──────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'data', 'budget_manager.db')
BK_PATH  = os.path.join(BASE_DIR, 'backups',
    f"budget_manager_AVANT_V5_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")

# ── Nouveau schéma ────────────────────────────────────────────────────────────
TABLES_SQL = """
-- Entités
CREATE TABLE IF NOT EXISTS entites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    nom TEXT NOT NULL,
    siret TEXT,
    adresse TEXT,
    actif BOOLEAN DEFAULT 1
);

-- Applications
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    nom TEXT NOT NULL,
    description TEXT,
    type_app TEXT DEFAULT 'METIER'
        CHECK(type_app IN ('METIER','INFRASTRUCTURE','TRANSVERSE','SECURITE')),
    entite_id INTEGER,
    fournisseur_id INTEGER,
    version_actuelle TEXT,
    date_fin_support DATE,
    statut TEXT DEFAULT 'ACTIF'
        CHECK(statut IN ('ACTIF','EN_MIGRATION','OBSOLETE','ABANDONNE')),
    notes TEXT,
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (entite_id) REFERENCES entites(id),
    FOREIGN KEY (fournisseur_id) REFERENCES fournisseurs(id)
);

-- Budgets annuels
CREATE TABLE IF NOT EXISTS budgets_annuels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entite_id INTEGER NOT NULL,
    exercice INTEGER NOT NULL,
    nature TEXT NOT NULL CHECK(nature IN ('FONCTIONNEMENT','INVESTISSEMENT')),
    montant_previsionnel REAL DEFAULT 0,
    date_soumission DATE,
    note_presentation TEXT,
    montant_vote REAL DEFAULT 0,
    date_vote DATE,
    montant_engage REAL DEFAULT 0,
    montant_solde REAL DEFAULT 0,
    statut TEXT DEFAULT 'EN_PREPARATION'
        CHECK(statut IN ('EN_PREPARATION','SOUMIS','VOTE','CLOTURE')),
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_maj TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (entite_id) REFERENCES entites(id),
    UNIQUE (entite_id, exercice, nature)
);

-- Lignes budgétaires
CREATE TABLE IF NOT EXISTS lignes_budgetaires (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    budget_id INTEGER NOT NULL,
    libelle TEXT NOT NULL,
    application_id INTEGER,
    projet_id INTEGER,
    montant_prevu REAL DEFAULT 0,
    montant_vote REAL DEFAULT 0,
    montant_engage REAL DEFAULT 0,
    montant_solde REAL DEFAULT 0,
    montant_paye REAL DEFAULT 0,
    montant_prevu_n1 REAL DEFAULT 0,
    nature TEXT NOT NULL CHECK(nature IN ('FONCTIONNEMENT','INVESTISSEMENT')),
    seuil_alerte_pct INTEGER DEFAULT 80,
    note TEXT,
    statut TEXT DEFAULT 'ACTIF' CHECK(statut IN ('ACTIF','GELE','CLOTURE')),
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_maj TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (budget_id) REFERENCES budgets_annuels(id) ON DELETE CASCADE,
    FOREIGN KEY (application_id) REFERENCES applications(id),
    FOREIGN KEY (projet_id) REFERENCES projets(id)
);
"""

VIEWS_SQL = """
-- Vues
CREATE VIEW IF NOT EXISTS v_synthese_budget AS
SELECT
    e.code AS entite_code, e.nom AS entite_nom,
    ba.exercice, ba.nature, ba.statut AS statut_budget,
    ba.montant_previsionnel, ba.montant_vote,
    COALESCE(SUM(lb.montant_engage), 0) AS montant_engage,
    ba.montant_vote - COALESCE(SUM(lb.montant_engage), 0) AS montant_solde,
    COALESCE(SUM(lb.montant_paye), 0) AS montant_paye,
    COUNT(lb.id) AS nb_lignes
FROM budgets_annuels ba
JOIN entites e ON e.id = ba.entite_id
LEFT JOIN lignes_budgetaires lb ON lb.budget_id = ba.id
GROUP BY ba.id;

CREATE VIEW IF NOT EXISTS v_lignes_budget AS
SELECT lb.*, ba.exercice, ba.nature,
    e.code AS entite_code, e.nom AS entite_nom,
    a.nom AS application_nom, a.code AS application_code,
    p.nom AS projet_nom, p.code AS projet_code,
    CASE WHEN lb.montant_vote > 0
         THEN ROUND(lb.montant_engage * 100.0 / lb.montant_vote, 1)
         ELSE 0 END AS taux_engagement_pct,
    CASE WHEN lb.montant_engage >= lb.montant_vote * lb.seuil_alerte_pct / 100.0
         THEN 1 ELSE 0 END AS alerte_seuil
FROM lignes_budgetaires lb
JOIN budgets_annuels ba ON ba.id = lb.budget_id
JOIN entites e ON e.id = ba.entite_id
LEFT JOIN applications a ON a.id = lb.application_id
LEFT JOIN projets p ON p.id = lb.projet_id;

CREATE VIEW IF NOT EXISTS v_contrats_alertes AS
SELECT c.*, e.code AS entite_code, e.nom AS entite_nom,
    f.nom AS fournisseur_nom, a.nom AS application_nom,
    CAST(julianday(c.date_fin) - julianday('now') AS INTEGER) AS jours_restants,
    CASE
        WHEN julianday(c.date_fin) < julianday('now') THEN 'EXPIRE'
        WHEN julianday(c.date_fin) - julianday('now') <= 30  THEN 'CRITIQUE'
        WHEN julianday(c.date_fin) - julianday('now') <= 90  THEN 'ATTENTION'
        WHEN julianday(c.date_fin) - julianday('now') <= 180 THEN 'INFO'
        ELSE 'OK'
    END AS niveau_alerte,
    c.montant_max_ht - c.montant_engage_cumul AS capacite_restante
FROM contrats c
JOIN entites e ON e.id = c.entite_id
JOIN fournisseurs f ON f.id = c.fournisseur_id
LEFT JOIN applications a ON a.id = c.application_id
WHERE c.statut IN ('ACTIF','RECONDUIT');

CREATE VIEW IF NOT EXISTS v_bons_commande AS
SELECT bc.*, e.code AS entite_code, e.nom AS entite_nom,
    f.nom AS fournisseur_nom,
    lb.libelle AS ligne_budgetaire_libelle,
    lb.montant_vote AS lb_vote, lb.montant_engage AS lb_engage,
    lb.montant_solde AS lb_solde,
    c.numero_contrat, c.type_contrat,
    a.nom AS application_nom, p.nom AS projet_nom
FROM bons_commande bc
JOIN entites e ON e.id = bc.entite_id
JOIN fournisseurs f ON f.id = bc.fournisseur_id
LEFT JOIN lignes_budgetaires lb ON lb.id = bc.ligne_budgetaire_id
LEFT JOIN contrats c ON c.id = bc.contrat_id
LEFT JOIN applications a ON a.id = bc.application_id
LEFT JOIN projets p ON p.id = bc.projet_id;

-- Index
CREATE INDEX IF NOT EXISTS idx_bc_entite       ON bons_commande(entite_id);
CREATE INDEX IF NOT EXISTS idx_bc_ligne        ON bons_commande(ligne_budgetaire_id);
CREATE INDEX IF NOT EXISTS idx_lb_budget       ON lignes_budgetaires(budget_id);
CREATE INDEX IF NOT EXISTS idx_lb_application  ON lignes_budgetaires(application_id);
CREATE INDEX IF NOT EXISTS idx_lb_projet       ON lignes_budgetaires(projet_id);
CREATE INDEX IF NOT EXISTS idx_ba_entite       ON budgets_annuels(entite_id);
CREATE INDEX IF NOT EXISTS idx_ba_exercice     ON budgets_annuels(exercice);
CREATE INDEX IF NOT EXISTS idx_contrats_fin    ON contrats(date_fin);
CREATE INDEX IF NOT EXISTS idx_projets_entite  ON projets(entite_id);
"""

# ── Modifications colonnes existantes ─────────────────────────────────────────
ALTER_STATEMENTS = [
    # contrats : ajouter entite_id, application_id, nature, type_contrat étendu
    "ALTER TABLE contrats ADD COLUMN entite_id INTEGER REFERENCES entites(id)",
    "ALTER TABLE contrats ADD COLUMN application_id INTEGER REFERENCES applications(id)",
    "ALTER TABLE contrats ADD COLUMN nature TEXT DEFAULT 'FONCTIONNEMENT'",
    "ALTER TABLE contrats ADD COLUMN montant_max_ht REAL",
    "ALTER TABLE contrats ADD COLUMN montant_engage_cumul REAL DEFAULT 0",
    "ALTER TABLE contrats ADD COLUMN montant_restant REAL DEFAULT 0",
    "ALTER TABLE contrats ADD COLUMN alerte_echeance_jours INTEGER DEFAULT 90",
    "ALTER TABLE contrats ADD COLUMN tva REAL DEFAULT 20.0",
    # bons_commande : ajouter entite_id, nature, ligne_budgetaire_id, application_id
    "ALTER TABLE bons_commande ADD COLUMN entite_id INTEGER REFERENCES entites(id)",
    "ALTER TABLE bons_commande ADD COLUMN nature TEXT DEFAULT 'FONCTIONNEMENT'",
    "ALTER TABLE bons_commande ADD COLUMN ligne_budgetaire_id INTEGER REFERENCES lignes_budgetaires(id)",
    "ALTER TABLE bons_commande ADD COLUMN application_id INTEGER REFERENCES applications(id)",
    "ALTER TABLE bons_commande ADD COLUMN montant_facture REAL DEFAULT 0",
    "ALTER TABLE bons_commande ADD COLUMN montant_paye REAL DEFAULT 0",
    "ALTER TABLE bons_commande ADD COLUMN reception_ok BOOLEAN DEFAULT 0",
    "ALTER TABLE bons_commande ADD COLUMN notes TEXT",
    # projets : ajouter entite_id, montant_paye, montant_solde
    "ALTER TABLE projets ADD COLUMN entite_id INTEGER REFERENCES entites(id)",
    "ALTER TABLE projets ADD COLUMN montant_paye REAL DEFAULT 0",
    "ALTER TABLE projets ADD COLUMN montant_solde REAL DEFAULT 0",
]


def run():
    print("=" * 60)
    print("  MIGRATION Budget Manager Pro V4 → V5")
    print("=" * 60)

    if not os.path.exists(DB_PATH):
        print(f"❌  Base introuvable : {DB_PATH}")
        sys.exit(1)

    # ── 1. Sauvegarde ─────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(BK_PATH), exist_ok=True)
    shutil.copy2(DB_PATH, BK_PATH)
    print(f"✅  Sauvegarde : {os.path.basename(BK_PATH)}")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = OFF")
    cur  = conn.cursor()

    # ── 2. Nouvelles tables ───────────────────────────────────────────────────
    print("   Création des nouvelles tables...")
    conn.executescript(TABLES_SQL)
    print("✅  Nouvelles tables créées")

    # ── 3. ALTER TABLE (ignorer si colonne déjà présente) ─────────────────────
    print("   Ajout des nouvelles colonnes...")
    for stmt in ALTER_STATEMENTS:
        try:
            cur.execute(stmt)
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                pass  # déjà présente
            else:
                print(f"   ⚠  {e}")
    conn.commit()
    print("✅  Colonnes ajoutées")

    # ── 3b. Créer les vues APRÈS les ALTER (elles référencent entite_id) ──────
    print("   Création des vues...")
    try:
        conn.executescript(VIEWS_SQL)
        conn.commit()
        print("✅  Vues créées")
    except Exception as e:
        print(f"   ⚠  Vues (non bloquant) : {e}")

    # ── 4. Données de référence ───────────────────────────────────────────────
    print("   Insertion des entités...")
    cur.executemany(
        "INSERT OR IGNORE INTO entites (code, nom) VALUES (?, ?)",
        [("VILLE", "Ville de La Rochelle"),
         ("CDA",   "Communauté d'Agglomération de La Rochelle")]
    )
    conn.commit()

    ville_id = cur.execute("SELECT id FROM entites WHERE code='VILLE'").fetchone()[0]
    cda_id   = cur.execute("SELECT id FROM entites WHERE code='CDA'").fetchone()[0]
    print(f"✅  Entités : VILLE (id={ville_id}), CDA (id={cda_id})")

    # ── 5. Rattacher les BC existants à VILLE par défaut ─────────────────────
    cur.execute("UPDATE bons_commande SET entite_id=? WHERE entite_id IS NULL", (ville_id,))
    cur.execute("UPDATE bons_commande SET nature=type_budget WHERE nature='FONCTIONNEMENT' AND type_budget IS NOT NULL")
    n = cur.rowcount
    print(f"✅  {cur.execute('SELECT COUNT(*) FROM bons_commande').fetchone()[0]} BC rattachés à VILLE par défaut")

    # ── 6. Rattacher les contrats existants à VILLE ───────────────────────────
    cur.execute("UPDATE contrats SET entite_id=? WHERE entite_id IS NULL", (ville_id,))
    cur.execute("UPDATE contrats SET nature=type_budget WHERE nature IS NULL AND type_budget IS NOT NULL")
    print(f"✅  {cur.execute('SELECT COUNT(*) FROM contrats').fetchone()[0]} contrats rattachés à VILLE")

    # ── 7. Rattacher les projets existants à VILLE ────────────────────────────
    cur.execute("UPDATE projets SET entite_id=? WHERE entite_id IS NULL", (ville_id,))
    print(f"✅  {cur.execute('SELECT COUNT(*) FROM projets').fetchone()[0]} projets rattachés à VILLE")

    # ── 8. Créer budgets 2026 vides (4 : VILLE fonct/invest + CDA fonct/invest)
    exercice = 2026
    budgets_init = [
        (ville_id, exercice, 'FONCTIONNEMENT'),
        (ville_id, exercice, 'INVESTISSEMENT'),
        (cda_id,   exercice, 'FONCTIONNEMENT'),
        (cda_id,   exercice, 'INVESTISSEMENT'),
    ]
    cur.executemany("""
        INSERT OR IGNORE INTO budgets_annuels (entite_id, exercice, nature, statut)
        VALUES (?, ?, ?, 'EN_PREPARATION')
    """, budgets_init)
    conn.commit()
    print(f"✅  4 budgets {exercice} créés (VILLE + CDA × FONCT + INVEST)")

    # ── 9. Recalculer montant_engage des projets via BC ───────────────────────
    # Recalculer budget_consomme des projets via BC
    cur.execute("""
        UPDATE projets SET
            budget_consomme = COALESCE((
                SELECT SUM(montant_ttc) FROM bons_commande
                WHERE projet_id = projets.id
                AND statut IN ('IMPUTE','SOLDE','VALIDE')
            ), 0)
    """)
    conn.commit()
    print("✅  Montants projets recalculés")

    conn.execute("PRAGMA foreign_keys = ON")
    conn.close()

    print()
    print("=" * 60)
    print("  MIGRATION TERMINÉE ✅")
    print("  Prochaines étapes :")
    print("  1. Configurer vos budgets 2026 (Onglet Budget)")
    print("  2. Créer vos applications (Onglet Applications)")
    print("  3. Créer vos lignes budgétaires")
    print("  4. Rattacher vos BC aux lignes budgétaires")
    print("=" * 60)


if __name__ == "__main__":
    run()
