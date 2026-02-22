"""
repair_v5.py — Répare la base V5 (tables vides + vues manquantes)
Placer à la racine du projet et exécuter : python repair_v5.py
"""
import sqlite3, os, sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'data', 'budget_manager.db')

TABLES_SQL = """
CREATE TABLE IF NOT EXISTS entites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    nom TEXT NOT NULL,
    siret TEXT,
    adresse TEXT,
    actif BOOLEAN DEFAULT 1
);

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

ALTER_SQL = [
    "ALTER TABLE contrats ADD COLUMN entite_id INTEGER REFERENCES entites(id)",
    "ALTER TABLE contrats ADD COLUMN application_id INTEGER REFERENCES applications(id)",
    "ALTER TABLE contrats ADD COLUMN nature TEXT DEFAULT 'FONCTIONNEMENT'",
    "ALTER TABLE contrats ADD COLUMN type_budget TEXT DEFAULT 'FONCTIONNEMENT'",
    "ALTER TABLE contrats ADD COLUMN montant_annuel_ht REAL DEFAULT 0",
    # --- audit_log ---
    """CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        table_name TEXT NOT NULL,
        record_id INTEGER,
        action TEXT NOT NULL,
        description TEXT,
        valeur_avant TEXT,
        valeur_apres TEXT,
        utilisateur TEXT DEFAULT 'system',
        date_action TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS taches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        projet_id INTEGER NOT NULL,
        titre TEXT NOT NULL,
        description TEXT,
        statut TEXT DEFAULT 'A_FAIRE',
        priorite TEXT,
        date_creation DATE DEFAULT CURRENT_DATE,
        date_echeance DATE,
        date_debut DATE,
        date_fin_prevue DATE,
        date_fin_reelle DATE,
        duree_estimee INTEGER,
        estimation_heures REAL DEFAULT 0,
        heures_reelles REAL DEFAULT 0,
        avancement INTEGER DEFAULT 0,
        assignee_id INTEGER,
        assigne_a INTEGER,
        ordre INTEGER DEFAULT 0,
        etiquettes TEXT,
        tags TEXT,
        commentaires TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    "ALTER TABLE contrats ADD COLUMN montant_max_ht REAL",
    "ALTER TABLE contrats ADD COLUMN montant_engage_cumul REAL DEFAULT 0",
    "ALTER TABLE contrats ADD COLUMN montant_restant REAL DEFAULT 0",
    "ALTER TABLE contrats ADD COLUMN alerte_echeance_jours INTEGER DEFAULT 90",
    "ALTER TABLE contrats ADD COLUMN tva REAL DEFAULT 20.0",
    # --- bons_commande ---
    "ALTER TABLE bons_commande ADD COLUMN entite_id INTEGER REFERENCES entites(id)",
    "ALTER TABLE bons_commande ADD COLUMN nature TEXT DEFAULT 'FONCTIONNEMENT'",
    "ALTER TABLE bons_commande ADD COLUMN ligne_budgetaire_id INTEGER REFERENCES lignes_budgetaires(id)",
    "ALTER TABLE bons_commande ADD COLUMN application_id INTEGER REFERENCES applications(id)",
    "ALTER TABLE bons_commande ADD COLUMN montant_facture REAL DEFAULT 0",
    "ALTER TABLE bons_commande ADD COLUMN montant_paye REAL DEFAULT 0",
    "ALTER TABLE bons_commande ADD COLUMN reception_ok BOOLEAN DEFAULT 0",
    "ALTER TABLE bons_commande ADD COLUMN notes TEXT",
    "ALTER TABLE bons_commande ADD COLUMN ref_dsi TEXT",
    "ALTER TABLE bons_commande ADD COLUMN budget_impute TEXT",
    # --- projets ---
    "ALTER TABLE projets ADD COLUMN entite_id INTEGER REFERENCES entites(id)",
    "ALTER TABLE projets ADD COLUMN ligne_budgetaire_id INTEGER REFERENCES lignes_budgetaires(id)",
    "ALTER TABLE projets ADD COLUMN objectifs TEXT",
    "ALTER TABLE projets ADD COLUMN enjeux TEXT",
    "ALTER TABLE projets ADD COLUMN risques TEXT",
    "ALTER TABLE projets ADD COLUMN gains TEXT",
    "ALTER TABLE projets ADD COLUMN contraintes TEXT",
    "ALTER TABLE projets ADD COLUMN solutions TEXT",
    # --- projet_membres : coordonnées acteurs ---
    "ALTER TABLE projet_membres ADD COLUMN fonction TEXT",
    "ALTER TABLE projet_membres ADD COLUMN email TEXT",
    "ALTER TABLE projet_membres ADD COLUMN telephone TEXT",
    "ALTER TABLE projet_membres ADD COLUMN role_projet TEXT",
    # --- entites ---
    "ALTER TABLE entites ADD COLUMN statut TEXT DEFAULT 'ACTIF'",
    "ALTER TABLE entites ADD COLUMN actif INTEGER DEFAULT 1",
    "ALTER TABLE entites ADD COLUMN siret TEXT",
    # --- budgets_annuels ---
    "ALTER TABLE budgets_annuels ADD COLUMN statut TEXT DEFAULT 'EN_PREPARATION'",
    "ALTER TABLE budgets_annuels ADD COLUMN montant_previsionnel REAL DEFAULT 0",
    "ALTER TABLE budgets_annuels ADD COLUMN montant_engage REAL DEFAULT 0",
    "ALTER TABLE budgets_annuels ADD COLUMN montant_solde REAL DEFAULT 0",
    "ALTER TABLE budgets_annuels ADD COLUMN montant_paye REAL DEFAULT 0",
    "ALTER TABLE budgets_annuels ADD COLUMN entite_id INTEGER REFERENCES entites(id)",
    "ALTER TABLE budgets_annuels ADD COLUMN date_vote TEXT",
    "ALTER TABLE budgets_annuels ADD COLUMN cree_par INTEGER",
    "ALTER TABLE projets ADD COLUMN montant_prevu REAL DEFAULT 0",
    "ALTER TABLE projets ADD COLUMN montant_engage REAL DEFAULT 0",
    "ALTER TABLE projets ADD COLUMN montant_solde REAL DEFAULT 0",
    "ALTER TABLE projets ADD COLUMN montant_paye REAL DEFAULT 0",
    # --- lignes_budgetaires ---
    "ALTER TABLE lignes_budgetaires ADD COLUMN fournisseur_id INTEGER REFERENCES fournisseurs(id)",
    "ALTER TABLE lignes_budgetaires ADD COLUMN statut TEXT DEFAULT 'ACTIF'",
    "ALTER TABLE lignes_budgetaires ADD COLUMN montant_engage REAL DEFAULT 0",
    "ALTER TABLE lignes_budgetaires ADD COLUMN seuil_alerte_pct INTEGER DEFAULT 80",
    "ALTER TABLE lignes_budgetaires ADD COLUMN montant_solde REAL DEFAULT 0",
    "ALTER TABLE lignes_budgetaires ADD COLUMN montant_paye REAL DEFAULT 0",
    "ALTER TABLE contrats ADD COLUMN nb_reconductions_faites INTEGER DEFAULT 0",
    "ALTER TABLE contrats ADD COLUMN nb_reconductions_max INTEGER DEFAULT 3",
    "ALTER TABLE projets ADD COLUMN responsable_contact_id INTEGER REFERENCES contacts(id)",
    "ALTER TABLE contacts ADD COLUMN fournisseur_id INTEGER REFERENCES fournisseurs(id)",
    "ALTER TABLE projet_equipe ADD COLUMN contact_id INTEGER REFERENCES contacts(id)",
    "ALTER TABLE projet_equipe ADD COLUMN membre_label TEXT",
    "ALTER TABLE projets ADD COLUMN chef_projet_contact_id INTEGER REFERENCES contacts(id)",
    # --- Correction CHECK constraint bons_commande statut ---
    """CREATE TABLE IF NOT EXISTS bons_commande_new (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_bc TEXT UNIQUE,
        entite_id INTEGER REFERENCES entites(id),
        fournisseur_id INTEGER REFERENCES fournisseurs(id),
        contrat_id INTEGER REFERENCES contrats(id),
        projet_id INTEGER REFERENCES projets(id),
        application_id INTEGER REFERENCES applications(id),
        ligne_budgetaire_id INTEGER REFERENCES lignes_budgetaires(id),
        objet TEXT,
        description TEXT,
        montant_ht REAL DEFAULT 0,
        montant_ttc REAL DEFAULT 0,
        tva REAL DEFAULT 20,
        statut TEXT DEFAULT 'BROUILLON' CHECK(statut IN ('BROUILLON','EN_ATTENTE','VALIDE','IMPUTE','SOLDE','ANNULE')),
        nature TEXT DEFAULT 'FONCTIONNEMENT',
        nature_comptable TEXT,
        type_budget TEXT,
        fonction TEXT,
        operation TEXT,
        date_creation TEXT,
        date_validation TEXT,
        date_imputation TEXT,
        date_solde TEXT,
        date_maj TEXT,
        date_livraison_prevue TEXT,
        date_livraison_reelle TEXT,
        impute INTEGER DEFAULT 0,
        valide INTEGER DEFAULT 0,
        valideur_id INTEGER,
        montant_engage REAL DEFAULT 0,
        montant_facture REAL DEFAULT 0,
        montant_paye REAL DEFAULT 0,
        montant_receptionne REAL DEFAULT 0,
        reception_ok INTEGER DEFAULT 0,
        reception_partielle INTEGER DEFAULT 0,
        cp_id INTEGER,
        engagement_id INTEGER,
        ref_dsi TEXT,
        budget_impute TEXT,
        notes TEXT,
        note TEXT
    )""",
    "ALTER TABLE contrats ADD COLUMN notes TEXT",
    "ALTER TABLE contrats ADD COLUMN statut TEXT DEFAULT 'ACTIF'",
    "ALTER TABLE contrats ADD COLUMN montant_total_ht REAL DEFAULT 0",
    "ALTER TABLE contrats ADD COLUMN montant_ttc REAL DEFAULT 0",
    "ALTER TABLE contrats ADD COLUMN montant_initial_ht REAL DEFAULT 0",
    "ALTER TABLE contrats ADD COLUMN reconductions INTEGER DEFAULT 0",
]

VIEWS_SQL = [
("v_synthese_budget", """
CREATE VIEW v_synthese_budget AS
SELECT
    e.code AS entite_code, e.nom AS entite_nom,
    ba.exercice, ba.nature, ba.statut AS statut_budget,
    ba.montant_previsionnel, ba.montant_vote,
    COALESCE(SUM(lb.montant_engage), 0) AS montant_engage,
    ba.montant_vote - COALESCE(SUM(lb.montant_engage), 0) AS montant_solde,
    COALESCE(SUM(lb.montant_paye), 0) AS montant_paye,
    COUNT(lb.id) AS nb_lignes,
    ba.id AS budget_id
FROM budgets_annuels ba
JOIN entites e ON e.id = ba.entite_id
LEFT JOIN lignes_budgetaires lb ON lb.budget_id = ba.id
GROUP BY ba.id
"""),
("v_lignes_budget", """
CREATE VIEW v_lignes_budget AS
SELECT
    lb.id, lb.budget_id, lb.libelle, lb.application_id, lb.projet_id,
    lb.montant_prevu, lb.montant_vote, lb.montant_engage, lb.montant_solde,
    lb.montant_paye, lb.montant_prevu_n1, lb.nature,
    COALESCE(lb.seuil_alerte_pct, 80) AS seuil_alerte_pct,
    lb.note, COALESCE(lb.statut, 'ACTIF') AS statut,
    lb.date_creation, lb.date_maj,
    lb.fournisseur_id,
    ba.exercice, ba.nature AS budget_nature,
    e.code AS entite_code, e.nom AS entite_nom,
    e.id AS entite_id,
    a.nom AS application_nom, a.code AS application_code,
    p.nom AS projet_nom, p.code AS projet_code,
    f.nom AS fournisseur_nom,
    CASE WHEN lb.montant_vote > 0
         THEN ROUND(lb.montant_engage * 100.0 / lb.montant_vote, 1)
         ELSE 0 END AS taux_engagement_pct,
    CASE WHEN lb.montant_vote > 0
         AND lb.montant_engage >= lb.montant_vote * lb.seuil_alerte_pct / 100.0
         THEN 1 ELSE 0 END AS alerte_seuil
FROM lignes_budgetaires lb
JOIN budgets_annuels ba ON ba.id = lb.budget_id
JOIN entites e ON e.id = ba.entite_id
LEFT JOIN applications a ON a.id = lb.application_id
LEFT JOIN projets p ON p.id = lb.projet_id
LEFT JOIN fournisseurs f ON f.id = lb.fournisseur_id
"""),
("v_contrats_alertes", """
CREATE VIEW v_contrats_alertes AS
SELECT
    c.id, c.numero_contrat, c.objet, c.type_contrat,
    c.fournisseur_id, c.date_debut, c.date_fin, c.statut,
    COALESCE(c.montant_total_ht, 0) AS montant_ht,
    COALESCE(c.montant_ttc, 0) AS montant_ttc,
    c.montant_max_ht,
    c.montant_engage_cumul, c.montant_restant, c.nature,
    c.entite_id, c.application_id,
    e.code AS entite_code, e.nom AS entite_nom,
    f.nom AS fournisseur_nom,
    a.nom AS application_nom,
    CAST(julianday(c.date_fin) - julianday('now') AS INTEGER) AS jours_restants,
    CASE
        WHEN julianday(c.date_fin) < julianday('now') THEN 'EXPIRE'
        WHEN julianday(c.date_fin) - julianday('now') <= 30  THEN 'CRITIQUE'
        WHEN julianday(c.date_fin) - julianday('now') <= 90  THEN 'ATTENTION'
        WHEN julianday(c.date_fin) - julianday('now') <= 180 THEN 'INFO'
        ELSE 'OK'
    END AS niveau_alerte,
    COALESCE(c.montant_max_ht, 0) - COALESCE(c.montant_engage_cumul, 0) AS capacite_restante
FROM contrats c
LEFT JOIN entites e ON e.id = c.entite_id
JOIN fournisseurs f ON f.id = c.fournisseur_id
LEFT JOIN applications a ON a.id = c.application_id
WHERE c.statut IN ('ACTIF','RECONDUIT')
"""),
("v_bons_commande", """
CREATE VIEW v_bons_commande AS
SELECT
    bc.id, bc.numero_bc, bc.entite_id, bc.objet, bc.description,
    bc.nature, bc.ligne_budgetaire_id, bc.contrat_id,
    bc.application_id, bc.projet_id, bc.fournisseur_id,
    bc.montant_ht, bc.tva, bc.montant_ttc, bc.statut,
    bc.date_creation AS date_commande, bc.date_livraison_prevue, bc.date_creation,
    e.code AS entite_code, e.nom AS entite_nom,
    f.nom AS fournisseur_nom,
    lb.libelle AS ligne_budgetaire_libelle,
    lb.montant_vote AS lb_vote,
    lb.montant_engage AS lb_engage,
    lb.montant_solde AS lb_solde,
    c.numero_contrat, c.type_contrat,
    a.nom AS application_nom,
    p.nom AS projet_nom
FROM bons_commande bc
LEFT JOIN entites e ON e.id = bc.entite_id
JOIN fournisseurs f ON f.id = bc.fournisseur_id
LEFT JOIN lignes_budgetaires lb ON lb.id = bc.ligne_budgetaire_id
LEFT JOIN contrats c ON c.id = bc.contrat_id
LEFT JOIN applications a ON a.id = bc.application_id
LEFT JOIN projets p ON p.id = bc.projet_id
"""),
]

INDEX_SQL = """
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

def run():
    print("=" * 55)
    print("  RÉPARATION BASE V5")
    print("=" * 55)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")
    cur = conn.cursor()

    # 1. Tables
    print("  Création tables manquantes...")
    conn.executescript(TABLES_SQL)
    conn.commit()
    print("  ✅ Tables OK")

    # 2. ALTER colonnes
    print("  Ajout colonnes manquantes...")
    for stmt in ALTER_SQL:
        try:
            cur.execute(stmt)
        except sqlite3.OperationalError as e:
            if "duplicate column" not in str(e).lower():
                print(f"     ⚠  {e}")
    conn.commit()
    print("  ✅ Colonnes OK")

    # 3. Vues — DROP + RECREATE pour s'assurer qu'elles sont à jour
    print("  Recréation des vues...")
    for name, sql in VIEWS_SQL:
        try:
            cur.execute(f"DROP VIEW IF EXISTS {name}")
            cur.execute(sql.strip())
            print(f"     ✅ {name}")
        except Exception as e:
            print(f"     ❌ {name} : {e}")
    conn.commit()

    # 4. Index
    conn.executescript(INDEX_SQL)
    conn.commit()
    print("  ✅ Index OK")

    # 5. Données de référence
    cur.executemany(
        "INSERT OR IGNORE INTO entites (code, nom) VALUES (?,?)",
        [("VILLE","Ville de La Rochelle"),
         ("CDA","Communauté d'Agglomération de La Rochelle")]
    )
    conn.commit()

    ville_id = cur.execute("SELECT id FROM entites WHERE code='VILLE'").fetchone()[0]
    cda_id   = cur.execute("SELECT id FROM entites WHERE code='CDA'").fetchone()[0]

    # Rattacher BC / contrats / projets à VILLE
    cur.execute("UPDATE bons_commande SET entite_id=? WHERE entite_id IS NULL", (ville_id,))
    cur.execute("UPDATE contrats SET entite_id=? WHERE entite_id IS NULL", (ville_id,))
    cur.execute("UPDATE projets SET entite_id=? WHERE entite_id IS NULL", (ville_id,))

    # Budgets 2026
    for eid, nature in [(ville_id,'FONCTIONNEMENT'),(ville_id,'INVESTISSEMENT'),
                        (cda_id,'FONCTIONNEMENT'),(cda_id,'INVESTISSEMENT')]:
        cur.execute("""
            INSERT OR IGNORE INTO budgets_annuels
                (entite_id, exercice, nature, statut, date_creation, date_maj)
            VALUES (?,2026,?,'EN_PREPARATION',?,?)
        """, (eid, nature, datetime.now().isoformat(), datetime.now().isoformat()))
    conn.commit()

    # Validation
    print()
    print("  Validation...")
    for name, _ in VIEWS_SQL:
        try:
            conn.execute(f"SELECT * FROM {name} LIMIT 1").fetchone()
            print(f"     ✅ {name} opérationnelle")
        except Exception as e:
            print(f"     ❌ {name} : {e}")

    # ── Migration bons_commande : correction CHECK constraint statut ──
    try:
        cur2 = conn.cursor()
        exists = cur2.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='bons_commande_new'"
        ).fetchone()
        if exists:
            # 1. Supprimer les vues qui dépendent de bons_commande
            views_dep = [r[0] for r in cur2.execute(
                "SELECT name FROM sqlite_master WHERE type='view'"
            ).fetchall()]
            for v in views_dep:
                cur2.execute(f"DROP VIEW IF EXISTS [{v}]")
            conn.commit()

            # 2. Copier données, supprimer ancienne table, renommer
            cols_src = [r[1] for r in cur2.execute("PRAGMA table_info(bons_commande)").fetchall()]
            cols_dst = [r[1] for r in cur2.execute("PRAGMA table_info(bons_commande_new)").fetchall()]
            cols_common = [c for c in cols_src if c in cols_dst]
            cols_str = ", ".join(cols_common)
            cur2.execute(f"INSERT OR IGNORE INTO bons_commande_new ({cols_str}) SELECT {cols_str} FROM bons_commande")
            cur2.execute("DROP TABLE bons_commande")
            cur2.execute("ALTER TABLE bons_commande_new RENAME TO bons_commande")
            conn.commit()

            # 3. Recréer les vues
            for name, sql in VIEWS_SQL:
                try:
                    cur2.execute(f"DROP VIEW IF EXISTS [{name}]")
                    cur2.execute(sql)
                    conn.commit()
                except Exception as ve:
                    print(f"    ⚠️  Vue {name} : {ve}")

            print("  ✅ Table bons_commande migrée (CHECK statut corrigé)")
        else:
            print("  ℹ️  bons_commande : CHECK constraint déjà OK")
    except Exception as e:
        print(f"  ⚠️  Migration bons_commande : {e}")

    conn.execute("PRAGMA foreign_keys = ON")
    conn.close()

    print()
    print("=" * 55)
    print("  RÉPARATION TERMINÉE — relancer python run.py")
    print("=" * 55)

if __name__ == "__main__":
    run()
