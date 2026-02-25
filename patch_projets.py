"""
patch_projets.py — Ajoute les colonnes manquantes dans la table projets.
Lancer UNE FOIS depuis la racine du projet :
    cd D:\Budget-Manager-Pro-V5
    python patch_projets.py
"""
import sqlite3
from pathlib import Path

DB = Path(__file__).parent / 'data' / 'budget_manager.db'

COLONNES = [
    ("objectifs",          "TEXT"),
    ("enjeux",             "TEXT"),
    ("risques",            "TEXT"),
    ("gains",              "TEXT"),
    ("contraintes",        "TEXT"),
    ("solutions",          "TEXT"),
    ("registre_risques",   "TEXT"),
    ("contraintes_6axes",  "TEXT"),
    ("triangle_tensions",  "TEXT"),
    ("arbitrage",          "TEXT"),
    ("entite_id",          "INTEGER"),
    ("ligne_budgetaire_id","INTEGER"),
    ("montant_prevu",      "REAL DEFAULT 0"),
    ("montant_engage",     "REAL DEFAULT 0"),
    ("montant_solde",      "REAL DEFAULT 0"),
    ("montant_paye",       "REAL DEFAULT 0"),
]

conn = sqlite3.connect(DB)
existantes = {r[1] for r in conn.execute("PRAGMA table_info(projets)").fetchall()}

print(f"Base : {DB}")
print(f"Colonnes existantes : {len(existantes)}\n")

ajouts = 0
for col, typ in COLONNES:
    if col not in existantes:
        try:
            conn.execute(f"ALTER TABLE projets ADD COLUMN {col} {typ}")
            print(f"  ✅ {col} ajoutee")
            ajouts += 1
        except Exception as e:
            print(f"  ⚠️  {col} : {e}")
    else:
        print(f"  -- {col} (deja presente)")

conn.commit()
conn.close()

print(f"\n{ajouts} colonne(s) ajoutee(s).")
print("Relancez l application.")
