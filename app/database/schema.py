"""
Schéma de base de données SQLite pour Budget Manager Pro.
Gestion complète M57, projets, bons de commande, contrats, etc.
"""

SCHEMA_SQL = """
-- ============================================================================
-- UTILISATEURS ET ÉQUIPES
-- ============================================================================

CREATE TABLE IF NOT EXISTS utilisateurs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    prenom TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    fonction TEXT,
    telephone TEXT,
    actif BOOLEAN DEFAULT 1,
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS equipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    description TEXT,
    chef_equipe_id INTEGER,
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chef_equipe_id) REFERENCES utilisateurs(id)
);

CREATE TABLE IF NOT EXISTS equipe_membres (
    equipe_id INTEGER,
    utilisateur_id INTEGER,
    role TEXT,
    PRIMARY KEY (equipe_id, utilisateur_id),
    FOREIGN KEY (equipe_id) REFERENCES equipes(id),
    FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id)
);

-- ============================================================================
-- FOURNISSEURS ET PRESTATAIRES
-- ============================================================================

CREATE TABLE IF NOT EXISTS fournisseurs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    statut TEXT DEFAULT 'ACTIF' CHECK(statut IN ('ACTIF', 'INACTIF')),
    notes TEXT,
    siret TEXT,
    adresse TEXT,
    code_postal TEXT,
    ville TEXT,
    telephone TEXT,
    email TEXT,
    contact_principal TEXT,
    iban TEXT,
    actif BOOLEAN DEFAULT 1,
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prestataires (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    type_prestataire TEXT,  -- AMO, AMOA, ESN, etc.
    siret TEXT,
    adresse TEXT,
    code_postal TEXT,
    ville TEXT,
    telephone TEXT,
    email TEXT,
    contact_principal TEXT,
    actif BOOLEAN DEFAULT 1,
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- SERVICES ET CONTACTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    nom TEXT NOT NULL,
    responsable_id INTEGER,
    parent_id INTEGER,
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (responsable_id) REFERENCES contacts(id),
    FOREIGN KEY (parent_id) REFERENCES services(id)
);

CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    prenom TEXT NOT NULL,
    fonction TEXT,
    type TEXT NOT NULL CHECK(type IN ('ELU', 'DIRECTION', 'PRESTATAIRE', 'AMO')),
    telephone TEXT,
    email TEXT,
    service_id INTEGER,
    organisation TEXT,
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (service_id) REFERENCES services(id)
);

-- ============================================================================
-- BUDGET M57
-- ============================================================================

CREATE TABLE IF NOT EXISTS chapitres_m57 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    libelle TEXT NOT NULL,
    type_budget TEXT CHECK(type_budget IN ('FONCTIONNEMENT', 'INVESTISSEMENT')),
    section TEXT,
    description TEXT
);

CREATE TABLE IF NOT EXISTS fonctions_m57 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    libelle TEXT NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS autorisations_programme (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_ap TEXT UNIQUE NOT NULL,
    libelle TEXT NOT NULL,
    montant_total REAL NOT NULL,
    exercice_debut INTEGER NOT NULL,
    exercice_fin INTEGER NOT NULL,
    chapitre_m57_code TEXT,
    fonction_m57_code TEXT,
    operation TEXT,
    description TEXT,
    statut TEXT DEFAULT 'ACTIVE' CHECK(statut IN ('ACTIVE', 'CLOTUREE', 'ANNULEE')),
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chapitre_m57_code) REFERENCES chapitres_m57(code),
    FOREIGN KEY (fonction_m57_code) REFERENCES fonctions_m57(code)
);

CREATE TABLE IF NOT EXISTS credits_paiement (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ap_id INTEGER NOT NULL,
    exercice INTEGER NOT NULL,
    montant_vote REAL NOT NULL,
    montant_disponible REAL NOT NULL,
    montant_engage REAL DEFAULT 0,
    montant_mandate REAL DEFAULT 0,
    date_vote TIMESTAMP,
    statut TEXT DEFAULT 'ACTIF' CHECK(statut IN ('ACTIF', 'CLOTURE', 'ANNULE')),
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ap_id) REFERENCES autorisations_programme(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS engagements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cp_id INTEGER NOT NULL,
    numero_engagement TEXT UNIQUE NOT NULL,
    montant REAL NOT NULL,
    date_engagement TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    objet TEXT,
    fournisseur_id INTEGER,
    statut TEXT DEFAULT 'ENGAGE' CHECK(statut IN ('ENGAGE', 'MANDATE', 'PAYE', 'ANNULE')),
    FOREIGN KEY (cp_id) REFERENCES credits_paiement(id),
    FOREIGN KEY (fournisseur_id) REFERENCES fournisseurs(id)
);

-- ============================================================================
-- PROJETS
-- ============================================================================

CREATE TABLE IF NOT EXISTS projets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE,  -- Code projet (ex: PRJ2024-001)
    nom TEXT NOT NULL,
    description TEXT,
    phase TEXT CHECK(phase IN ('ETUDE', 'CONCEPTION', 'REALISATION', 'RECETTE', 'CLOTURE')),
    priorite TEXT CHECK(priorite IN ('CRITIQUE', 'HAUTE', 'MOYENNE', 'BASSE')),
    type_projet TEXT,  -- Infrastructure, Application, Réseau, Sécurité, etc.
    statut TEXT DEFAULT 'ACTIF' CHECK(statut IN ('ACTIF', 'EN_ATTENTE', 'TERMINE', 'ANNULE')),
    date_debut DATE,
    date_fin_prevue DATE,
    date_fin_reelle DATE,
    avancement INTEGER DEFAULT 0,  -- Pourcentage
    budget_estime REAL,
    budget_consomme REAL DEFAULT 0,
    budget_initial REAL,  -- Budget initial
    budget_actuel REAL,  -- Budget actuel
    chef_projet_id INTEGER,
    responsable_id INTEGER,  -- Responsable projet
    equipe_id INTEGER,
    ap_id INTEGER,
    service_id INTEGER,  -- Service bénéficiaire
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chef_projet_id) REFERENCES utilisateurs(id),
    FOREIGN KEY (responsable_id) REFERENCES utilisateurs(id),
    FOREIGN KEY (equipe_id) REFERENCES equipes(id),
    FOREIGN KEY (ap_id) REFERENCES autorisations_programme(id),
    FOREIGN KEY (service_id) REFERENCES services(id)
);

CREATE TABLE IF NOT EXISTS taches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    projet_id INTEGER NOT NULL,
    titre TEXT NOT NULL,
    description TEXT,
    statut TEXT DEFAULT 'A_FAIRE' CHECK(statut IN ('A_FAIRE', 'EN_COURS', 'EN_ATTENTE', 'BLOQUE', 'TERMINE', 'ANNULE')),
    priorite TEXT CHECK(priorite IN ('CRITIQUE', 'HAUTE', 'MOYENNE', 'BASSE')),
    date_creation DATE DEFAULT CURRENT_DATE,
    date_echeance DATE,  -- Date d'échéance
    date_debut DATE,
    date_fin_prevue DATE,
    date_fin_reelle DATE,
    duree_estimee INTEGER,  -- En jours
    estimation_heures REAL DEFAULT 0,  -- Estimation en heures
    heures_reelles REAL DEFAULT 0,  -- Heures réelles
    avancement INTEGER DEFAULT 0,
    assignee_id INTEGER,
    assigne_a INTEGER,  -- Alias pour assignee_id
    ordre INTEGER DEFAULT 0,  -- Pour le Kanban
    etiquettes TEXT,  -- JSON array
    tags TEXT,  -- Tags séparés par virgules
    commentaires TEXT,  -- Commentaires
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (projet_id) REFERENCES projets(id) ON DELETE CASCADE,
    FOREIGN KEY (assignee_id) REFERENCES utilisateurs(id),
    FOREIGN KEY (assigne_a) REFERENCES utilisateurs(id)
);

CREATE TABLE IF NOT EXISTS jalons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    projet_id INTEGER NOT NULL,
    nom TEXT NOT NULL,
    description TEXT,
    date_prevue DATE NOT NULL,
    date_reelle DATE,
    statut TEXT DEFAULT 'PREVU' CHECK(statut IN ('PREVU', 'EN_COURS', 'ATTEINT', 'DEPASSE')),
    critique BOOLEAN DEFAULT 0,
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (projet_id) REFERENCES projets(id) ON DELETE CASCADE
);

-- ============================================================================
-- ASSOCIATIONS PROJET
-- ============================================================================

CREATE TABLE IF NOT EXISTS projet_contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    projet_id INTEGER NOT NULL,
    contact_id INTEGER NOT NULL,
    role TEXT CHECK(role IN ('SPONSOR', 'VALIDEUR', 'REFERENT', 'INFORME')),
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (projet_id) REFERENCES projets(id) ON DELETE CASCADE,
    FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE,
    UNIQUE(projet_id, contact_id)
);

CREATE TABLE IF NOT EXISTS projet_equipe (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    projet_id INTEGER NOT NULL,
    utilisateur_id INTEGER NOT NULL,
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (projet_id) REFERENCES projets(id) ON DELETE CASCADE,
    FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id) ON DELETE CASCADE,
    UNIQUE(projet_id, utilisateur_id)
);

CREATE TABLE IF NOT EXISTS projet_prestataires (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    projet_id INTEGER NOT NULL,
    fournisseur_id INTEGER NOT NULL,
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (projet_id) REFERENCES projets(id) ON DELETE CASCADE,
    FOREIGN KEY (fournisseur_id) REFERENCES fournisseurs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS projet_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    projet_id INTEGER NOT NULL,
    nom_fichier TEXT NOT NULL,
    type_document TEXT,
    chemin_fichier TEXT,
    taille INTEGER,
    ajoute_par INTEGER,
    date_ajout TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (projet_id) REFERENCES projets(id) ON DELETE CASCADE,
    FOREIGN KEY (ajoute_par) REFERENCES utilisateurs(id)
);

-- ============================================================================
-- DOCUMENTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    projet_id INTEGER,
    type_document TEXT,  -- CDC, Rapport, PV, Fiche, etc.
    titre TEXT NOT NULL,
    description TEXT,
    chemin_fichier TEXT,
    taille_fichier INTEGER,
    extension TEXT,
    version TEXT DEFAULT '1.0',
    auteur_id INTEGER,
    date_upload TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_modification TIMESTAMP,
    FOREIGN KEY (projet_id) REFERENCES projets(id) ON DELETE CASCADE,
    FOREIGN KEY (auteur_id) REFERENCES utilisateurs(id)
);

CREATE TABLE IF NOT EXISTS cahiers_charges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    projet_id INTEGER NOT NULL,
    version TEXT DEFAULT '1.0',
    date_redaction DATE,
    contexte TEXT,
    objectifs TEXT,
    perimetre TEXT,
    contraintes TEXT,
    exigences_fonctionnelles TEXT,
    exigences_techniques TEXT,
    delais TEXT,
    budget_previsionnel REAL,
    criteres_acceptation TEXT,
    redacteur_id INTEGER,
    statut TEXT DEFAULT 'BROUILLON' CHECK(statut IN ('BROUILLON', 'EN_VALIDATION', 'VALIDE', 'ARCHIVE')),
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (projet_id) REFERENCES projets(id) ON DELETE CASCADE,
    FOREIGN KEY (redacteur_id) REFERENCES utilisateurs(id)
);

CREATE TABLE IF NOT EXISTS pieces_jointes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entite_type TEXT NOT NULL,  -- projet, tache, contrat, bc, etc.
    entite_id INTEGER NOT NULL,
    nom_fichier TEXT NOT NULL,
    chemin_fichier TEXT NOT NULL,
    taille_fichier INTEGER,
    extension TEXT,
    date_upload TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    uploadeur_id INTEGER,
    FOREIGN KEY (uploadeur_id) REFERENCES utilisateurs(id)
);

CREATE TABLE IF NOT EXISTS commentaires (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entite_type TEXT NOT NULL,
    entite_id INTEGER NOT NULL,
    contenu TEXT NOT NULL,
    auteur_id INTEGER NOT NULL,
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (auteur_id) REFERENCES utilisateurs(id)
);

-- ============================================================================
-- BONS DE COMMANDE
-- ============================================================================

CREATE TABLE IF NOT EXISTS bons_commande (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_bc TEXT UNIQUE NOT NULL,  -- SAISIE MANUELLE
    date_creation DATE NOT NULL,
    
    -- Classification
    type_budget TEXT NOT NULL CHECK(type_budget IN ('FONCTIONNEMENT', 'INVESTISSEMENT')),
    nature_comptable TEXT,  -- Chapitre M57
    fonction TEXT,  -- Fonction M57
    operation TEXT,  -- Si investissement
    
    -- Objet
    objet TEXT NOT NULL,
    description TEXT,
    projet_id INTEGER,
    contrat_id INTEGER,
    
    -- Fournisseur
    fournisseur_id INTEGER NOT NULL,
    
    -- Montants
    montant_ht REAL NOT NULL,
    montant_ttc REAL NOT NULL,
    tva REAL DEFAULT 20.0,
    
    -- Workflow validation
    statut TEXT DEFAULT 'BROUILLON' CHECK(statut IN ('BROUILLON', 'EN_ATTENTE', 'VALIDE', 'IMPUTE', 'ANNULE')),
    valide BOOLEAN DEFAULT 0,
    date_validation TIMESTAMP,
    valideur_id INTEGER,
    
    -- Imputation budgétaire
    impute BOOLEAN DEFAULT 0,
    date_imputation TIMESTAMP,
    montant_engage REAL DEFAULT 0,
    cp_id INTEGER,
    engagement_id INTEGER,
    
    -- Suivi livraison
    date_livraison_prevue DATE,
    date_livraison_reelle DATE,
    reception_partielle BOOLEAN DEFAULT 0,
    montant_receptionne REAL DEFAULT 0,
    
    date_maj TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (projet_id) REFERENCES projets(id),
    FOREIGN KEY (contrat_id) REFERENCES contrats(id),
    FOREIGN KEY (fournisseur_id) REFERENCES fournisseurs(id),
    FOREIGN KEY (valideur_id) REFERENCES utilisateurs(id),
    FOREIGN KEY (cp_id) REFERENCES credits_paiement(id),
    FOREIGN KEY (engagement_id) REFERENCES engagements(id)
);

-- ============================================================================
-- CONTRATS
-- ============================================================================

CREATE TABLE IF NOT EXISTS contrats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_contrat TEXT UNIQUE NOT NULL,
    type_contrat TEXT CHECK(type_contrat IN ('MARCHE_PUBLIC', 'MAPA', 'APPEL_OFFRES', 'ACCORD_CADRE', 'CONVENTION', 'DSP')),
    objet TEXT NOT NULL,
    
    -- Classification
    type_budget TEXT NOT NULL CHECK(type_budget IN ('FONCTIONNEMENT', 'INVESTISSEMENT')),
    nature_comptable TEXT,
    fonction TEXT,
    
    -- Fournisseur
    fournisseur_id INTEGER NOT NULL,
    
    -- Montants
    montant_initial_ht REAL NOT NULL,
    montant_total_ht REAL NOT NULL,
    montant_ttc REAL NOT NULL,
    
    -- Période
    date_debut DATE NOT NULL,
    date_fin DATE NOT NULL,
    duree_mois INTEGER,
    reconduction_tacite BOOLEAN DEFAULT 0,
    nombre_reconductions INTEGER DEFAULT 0,
    
    -- Budget
    ap_id INTEGER,
    montant_engage REAL DEFAULT 0,
    montant_mandate REAL DEFAULT 0,
    
    -- Statut
    statut TEXT DEFAULT 'BROUILLON' CHECK(statut IN ('BROUILLON', 'ACTIF', 'RECONDUIT', 'RESILIE', 'TERMINE')),
    
    -- Alertes
    date_notification TIMESTAMP,
    date_echeance_resiliation DATE,
    
    -- Documents
    piece_marche TEXT,
    deliberation TEXT,
    
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_maj TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (fournisseur_id) REFERENCES fournisseurs(id),
    FOREIGN KEY (ap_id) REFERENCES autorisations_programme(id)
);

CREATE TABLE IF NOT EXISTS avenants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contrat_id INTEGER NOT NULL,
    numero_avenant TEXT NOT NULL,
    date_signature DATE,
    objet TEXT NOT NULL,
    type_avenant TEXT CHECK(type_avenant IN ('MONTANT', 'DELAI', 'PRESTATION', 'MIXTE')),
    montant_supplementaire REAL DEFAULT 0,
    nouvelle_date_fin DATE,
    description TEXT,
    statut TEXT DEFAULT 'BROUILLON' CHECK(statut IN ('BROUILLON', 'VALIDE', 'ANNULE')),
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contrat_id) REFERENCES contrats(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS factures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_facture TEXT UNIQUE NOT NULL,
    bc_id INTEGER,
    contrat_id INTEGER,
    fournisseur_id INTEGER NOT NULL,
    date_facture DATE NOT NULL,
    date_echeance DATE,
    montant_ht REAL NOT NULL,
    montant_ttc REAL NOT NULL,
    tva REAL,
    statut TEXT DEFAULT 'RECUE' CHECK(statut IN ('RECUE', 'EN_VALIDATION', 'VALIDEE', 'PAYEE', 'LITIGE')),
    date_paiement DATE,
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bc_id) REFERENCES bons_commande(id),
    FOREIGN KEY (contrat_id) REFERENCES contrats(id),
    FOREIGN KEY (fournisseur_id) REFERENCES fournisseurs(id)
);

-- ============================================================================
-- TO-DO LIST
-- ============================================================================

CREATE TABLE IF NOT EXISTS todos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titre TEXT NOT NULL,
    description TEXT,
    priorite TEXT CHECK(priorite IN ('CRITIQUE', 'HAUTE', 'MOYENNE', 'BASSE')),
    statut TEXT DEFAULT 'A_FAIRE' CHECK(statut IN ('A_FAIRE', 'EN_COURS', 'TERMINE', 'ANNULE')),
    date_echeance DATE,
    date_rappel TIMESTAMP,
    projet_id INTEGER,
    tache_id INTEGER,
    assignee_id INTEGER NOT NULL,
    tags TEXT,  -- JSON array
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_completion TIMESTAMP,
    FOREIGN KEY (projet_id) REFERENCES projets(id) ON DELETE CASCADE,
    FOREIGN KEY (tache_id) REFERENCES taches(id) ON DELETE CASCADE,
    FOREIGN KEY (assignee_id) REFERENCES utilisateurs(id)
);

-- ============================================================================
-- NOTIFICATIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type_notification TEXT NOT NULL,  -- BC_VALIDATION, CONTRAT_ECHEANCE, BUDGET_ALERTE, etc.
    titre TEXT NOT NULL,
    message TEXT NOT NULL,
    priorite TEXT CHECK(priorite IN ('CRITIQUE', 'HAUTE', 'MOYENNE', 'BASSE')),
    utilisateur_id INTEGER NOT NULL,
    lue BOOLEAN DEFAULT 0,
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    entite_type TEXT,
    entite_id INTEGER,
    FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id)
);

-- ============================================================================
-- INDEX POUR PERFORMANCES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_projets_statut ON projets(statut);
CREATE INDEX IF NOT EXISTS idx_projets_chef ON projets(chef_projet_id);
CREATE INDEX IF NOT EXISTS idx_projets_code ON projets(code);
CREATE INDEX IF NOT EXISTS idx_projets_service ON projets(service_id);
CREATE INDEX IF NOT EXISTS idx_taches_projet ON taches(projet_id);
CREATE INDEX IF NOT EXISTS idx_taches_assignee ON taches(assignee_id);
CREATE INDEX IF NOT EXISTS idx_taches_statut ON taches(statut);
CREATE INDEX IF NOT EXISTS idx_taches_priorite ON taches(priorite);
CREATE INDEX IF NOT EXISTS idx_bc_statut ON bons_commande(statut);
CREATE INDEX IF NOT EXISTS idx_bc_fournisseur ON bons_commande(fournisseur_id);
CREATE INDEX IF NOT EXISTS idx_bc_projet ON bons_commande(projet_id);
CREATE INDEX IF NOT EXISTS idx_contrats_statut ON contrats(statut);
CREATE INDEX IF NOT EXISTS idx_contrats_fournisseur ON contrats(fournisseur_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(utilisateur_id, lue);
CREATE INDEX IF NOT EXISTS idx_todos_assignee ON todos(assignee_id);
CREATE INDEX IF NOT EXISTS idx_cp_ap ON credits_paiement(ap_id);
CREATE INDEX IF NOT EXISTS idx_contacts_type ON contacts(type);
CREATE INDEX IF NOT EXISTS idx_contacts_service ON contacts(service_id);
CREATE INDEX IF NOT EXISTS idx_services_code ON services(code);
CREATE INDEX IF NOT EXISTS idx_services_parent ON services(parent_id);
CREATE INDEX IF NOT EXISTS idx_projet_contacts_projet ON projet_contacts(projet_id);
CREATE INDEX IF NOT EXISTS idx_projet_contacts_contact ON projet_contacts(contact_id);
CREATE INDEX IF NOT EXISTS idx_projet_equipe_projet ON projet_equipe(projet_id);
CREATE INDEX IF NOT EXISTS idx_projet_prestataires_projet ON projet_prestataires(projet_id);
CREATE INDEX IF NOT EXISTS idx_projet_documents_projet ON projet_documents(projet_id);
"""

def init_database(conn):
    """Initialise la base de données avec le schéma."""
    cursor = conn.cursor()
    cursor.executescript(SCHEMA_SQL)
    conn.commit()
