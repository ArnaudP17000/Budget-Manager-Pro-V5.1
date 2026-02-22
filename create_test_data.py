"""
Script de création de données de test réalistes pour Budget Manager Pro.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from app.services.database_service import db_service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_data():
    """Crée des données de test réalistes."""
    
    try:
        conn = db_service.get_connection()
        
        # Supprimer les données existantes (pour tests)
        tables = [
            'notifications', 'todos', 'factures', 'avenants', 'contrats',
            'bons_commande', 'engagements', 'credits_paiement', 'autorisations_programme',
            'commentaires', 'pieces_jointes', 'cahiers_charges', 'documents',
            'jalons', 'taches',
            'projet_documents', 'projet_prestataires', 'projet_equipe', 'projet_contacts',
            'projets',
            'equipe_membres', 'equipes', 'utilisateurs',
            'contacts', 'services',
            'prestataires', 'fournisseurs',
            'fonctions_m57', 'chapitres_m57'
        ]
        
        for table in tables:
            try:
                conn.execute(f"DELETE FROM {table}")
            except:
                pass
        
        conn.commit()
        
        logger.info("=== Création des données de test ===")
        
        # ==================== UTILISATEURS ====================
        logger.info("Création des utilisateurs...")
        
        utilisateurs = [
            ('Dupont', 'Jean', 'jean.dupont@collectivite.fr', 'Chef de projet DSI', '0123456789'),
            ('Martin', 'Sophie', 'sophie.martin@collectivite.fr', 'Responsable budget', '0123456790'),
            ('Bernard', 'Pierre', 'pierre.bernard@collectivite.fr', 'Développeur', '0123456791'),
        ]
        
        user_ids = []
        for nom, prenom, email, fonction, tel in utilisateurs:
            user_id = db_service.insert('utilisateurs', {
                'nom': nom,
                'prenom': prenom,
                'email': email,
                'fonction': fonction,
                'telephone': tel,
                'actif': True,
            })
            user_ids.append(user_id)
        
        logger.info(f"✓ {len(user_ids)} utilisateurs créés")
        
        # ==================== SERVICES ====================
        logger.info("Création des services...")
        
        services = [
            ('DGS', 'Direction Générale des Services'),
            ('DSI', 'Direction des Systèmes d\'Information'),
            ('DRH', 'Direction des Ressources Humaines'),
            ('DFIN', 'Direction Financière'),
            ('DCULT', 'Direction Culturelle'),
            ('DSPORTS', 'Direction des Sports'),
            ('DURBA', 'Direction de l\'Urbanisme'),
            ('DENV', 'Direction de l\'Environnement'),
        ]
        
        service_ids = []
        for code, nom in services:
            service_id = db_service.insert('services', {
                'code': code,
                'nom': nom,
            })
            service_ids.append(service_id)
        
        logger.info(f"✓ {len(service_ids)} services créés")
        
        # ==================== CONTACTS ====================
        logger.info("Création des contacts...")
        
        contacts = [
            # Élus
            ('Durand', 'Marie', 'ELU', 'Maire', '0123450001', 'maire@collectivite.fr', None, None),
            ('Lefebvre', 'Jacques', 'ELU', 'Adjoint au Maire', '0123450002', 'adjoint@collectivite.fr', None, None),
            # Directions
            ('Moreau', 'Christine', 'DIRECTION', 'Directrice DSI', '0123450003', 'c.moreau@collectivite.fr', service_ids[1], None),
            ('Petit', 'François', 'DIRECTION', 'Directeur DRH', '0123450004', 'f.petit@collectivite.fr', service_ids[2], None),
            ('Roux', 'Isabelle', 'DIRECTION', 'Directrice Financière', '0123450005', 'i.roux@collectivite.fr', service_ids[3], None),
            # Prestataires
            ('Dubois', 'Laurent', 'PRESTATAIRE', 'Consultant', '0123450006', 'l.dubois@techconsulting.fr', None, 'Tech Consulting'),
            ('Thomas', 'Nathalie', 'PRESTATAIRE', 'Support technique', '0123450007', 'n.thomas@itsupport.fr', None, 'IT Support Pro'),
            # AMO
            ('Laurent', 'Philippe', 'AMO', 'Assistant MOA', '0123450008', 'p.laurent@amoconseil.fr', None, 'AMO Conseil'),
            ('Simon', 'Véronique', 'AMO', 'Conduite du changement', '0123450009', 'v.simon@changemanagement.fr', None, 'Change Management'),
            ('Michel', 'Éric', 'AMO', 'Auditeur sécurité', '0123450010', 'e.michel@securityaudit.fr', None, 'Security Audit Experts'),
        ]
        
        contact_ids = []
        for nom, prenom, type_c, fonction, tel, email, service_id, organisation in contacts:
            contact_id = db_service.insert('contacts', {
                'nom': nom,
                'prenom': prenom,
                'type': type_c,
                'fonction': fonction,
                'telephone': tel,
                'email': email,
                'service_id': service_id,
                'organisation': organisation,
            })
            contact_ids.append(contact_id)
        
        logger.info(f"✓ {len(contact_ids)} contacts créés")
        
        # ==================== FOURNISSEURS ====================
        logger.info("Création des fournisseurs...")
        
        fournisseurs = [
            ('Dell France', '12345678901234', '1 rue de Paris', '75001', 'Paris', '0144556677', 'contact@dell.fr', 'Jean Vente', 'ACTIF', 'Matériel informatique'),
            ('Microsoft France', '98765432109876', '39 quai Président Roosevelt', '92130', 'Issy-les-Moulineaux', '0155667788', 'contact@microsoft.fr', 'Marie Compte', 'ACTIF', 'Licences logicielles'),
            ('Orange Business', '11122233344455', '111 quai Président Roosevelt', '92130', 'Issy-les-Moulineaux', '0166778899', 'contact@orange.fr', 'Paul Réseau', 'ACTIF', 'Télécommunications et réseau'),
            ('Sopra Steria', '55566677788899', '9-11 allée de l\'Arche', '92671', 'Courbevoie', '0177889900', 'contact@sopra.fr', 'Luc Projet', 'INACTIF', 'ESN - Contrat terminé'),
            ('IBM France', '99988877766655', '17 avenue de l\'Europe', '92275', 'Bois-Colombes', '0188990011', 'contact@ibm.fr', 'Anne Support', 'ACTIF', 'Infrastructure et cloud'),
        ]
        
        fournisseur_ids = []
        for nom, siret, adresse, cp, ville, tel, email, contact, statut, notes in fournisseurs:
            f_id = db_service.insert('fournisseurs', {
                'nom': nom,
                'siret': siret,
                'adresse': adresse,
                'code_postal': cp,
                'ville': ville,
                'telephone': tel,
                'email': email,
                'contact_principal': contact,
                'actif': True,
                'statut': statut,
                'notes': notes,
            })
            fournisseur_ids.append(f_id)
        
        logger.info(f"✓ {len(fournisseur_ids)} fournisseurs créés")
        
        # ==================== CHAPITRES M57 ====================
        logger.info("Création des chapitres M57...")
        
        chapitres = [
            ('20', 'Immobilisations incorporelles', 'INVESTISSEMENT', 'Investissement'),
            ('21', 'Immobilisations corporelles', 'INVESTISSEMENT', 'Investissement'),
            ('2313', 'Matériels informatiques', 'INVESTISSEMENT', 'Investissement'),
            ('011', 'Charges à caractère général', 'FONCTIONNEMENT', 'Fonctionnement'),
            ('012', 'Charges de personnel', 'FONCTIONNEMENT', 'Fonctionnement'),
            ('65', 'Autres charges de gestion courante', 'FONCTIONNEMENT', 'Fonctionnement'),
            ('66', 'Charges financières', 'FONCTIONNEMENT', 'Fonctionnement'),
        ]
        
        for code, libelle, type_budget, section in chapitres:
            db_service.insert('chapitres_m57', {
                'code': code,
                'libelle': libelle,
                'type_budget': type_budget,
                'section': section,
            })
        
        logger.info(f"✓ {len(chapitres)} chapitres M57 créés")
        
        # ==================== FONCTIONS M57 ====================
        logger.info("Création des fonctions M57...")
        
        fonctions = [
            ('01', 'Services généraux des administrations publiques locales'),
            ('020', 'Enseignement'),
            ('30', 'Culture'),
            ('40', 'Sport et jeunesse'),
            ('50', 'Interventions sociales et santé'),
            ('60', 'Famille'),
            ('70', 'Logement'),
            ('80', 'Aménagement et services urbains, environnement'),
        ]
        
        for code, libelle in fonctions:
            db_service.insert('fonctions_m57', {
                'code': code,
                'libelle': libelle,
            })
        
        logger.info(f"✓ {len(fonctions)} fonctions M57 créées")
        
        # ==================== AUTORISATIONS PROGRAMME ====================
        logger.info("Création des AP...")
        
        aps = [
            ('AP-2024-001', 'Modernisation infrastructure réseau', 500000, 2024, 2026, '2313', '01', 'OP-2024-INF-001'),
            ('AP-2024-002', 'Déploiement nouvel ERP', 800000, 2024, 2025, '2313', '01', 'OP-2024-APP-001'),
            ('AP-2024-003', 'Sécurisation SI', 300000, 2024, 2025, '2313', '01', 'OP-2024-SEC-001'),
            ('AP-2024-004', 'Renouvellement parc informatique', 400000, 2024, 2026, '21', '01', 'OP-2024-MAT-001'),
            ('AP-2024-005', 'Projet Cloud', 600000, 2024, 2027, '20', '01', 'OP-2024-CLOUD-001'),
        ]
        
        ap_ids = []
        for numero, libelle, montant, ex_debut, ex_fin, chapitre, fonction, operation in aps:
            ap_id = db_service.insert('autorisations_programme', {
                'numero_ap': numero,
                'libelle': libelle,
                'montant_total': montant,
                'exercice_debut': ex_debut,
                'exercice_fin': ex_fin,
                'chapitre_m57_code': chapitre,
                'fonction_m57_code': fonction,
                'operation': operation,
                'statut': 'ACTIVE',
            })
            ap_ids.append(ap_id)
        
        logger.info(f"✓ {len(ap_ids)} AP créées")
        
        # ==================== CRÉDITS DE PAIEMENT ====================
        logger.info("Création des CP...")
        
        # 2 CP par AP (exercices 2024 et 2025)
        cp_ids = []
        for i, ap_id in enumerate(ap_ids):
            for exercice in [2024, 2025]:
                montant_vote = aps[i][2] / 3  # Un tiers du montant total par exercice
                cp_id = db_service.insert('credits_paiement', {
                    'ap_id': ap_id,
                    'exercice': exercice,
                    'montant_vote': montant_vote,
                    'montant_disponible': montant_vote * 0.7,  # 70% disponible
                    'montant_engage': montant_vote * 0.3,  # 30% engagé
                    'montant_mandate': montant_vote * 0.1,  # 10% mandaté
                    'statut': 'ACTIF',
                })
                cp_ids.append(cp_id)
        
        logger.info(f"✓ {len(cp_ids)} CP créés")
        
        # ==================== PROJETS ====================
        logger.info("Création des projets...")
        
        projets = [
            ('PRJ2024-001', 'Migration infrastructure réseau', 'Migration vers une nouvelle infrastructure réseau haute performance', 'Infrastructure', 'REALISATION', 'HAUTE', 'ACTIF', -30, 180, 45, 250000),
            ('PRJ2024-002', 'Déploiement ERP', 'Déploiement du nouvel ERP pour tous les services', 'Application', 'CONCEPTION', 'CRITIQUE', 'ACTIF', -60, 365, 25, 500000),
            ('PRJ2024-003', 'Audit sécurité SI', 'Audit complet de la sécurité du système d\'information', 'Sécurité', 'ETUDE', 'HAUTE', 'ACTIF', -15, 90, 60, 80000),
            ('PRJ2024-004', 'Renouvellement postes de travail', 'Renouvellement de 200 postes de travail', 'Infrastructure', 'REALISATION', 'MOYENNE', 'ACTIF', 0, 120, 70, 300000),
            ('PRJ2024-005', 'Migration vers le Cloud', 'Migration des applications vers le Cloud', 'Infrastructure', 'ETUDE', 'HAUTE', 'EN_ATTENTE', 30, 730, 10, 450000),
        ]
        
        projet_ids = []
        for i, (code, nom, desc, type_p, phase, prio, statut, jours_debut, duree, avanc, budget) in enumerate(projets):
            date_debut = datetime.now() + timedelta(days=jours_debut)
            date_fin = date_debut + timedelta(days=duree)
            
            projet_id = db_service.insert('projets', {
                'code': code,
                'nom': nom,
                'description': desc,
                'type_projet': type_p,
                'phase': phase,
                'priorite': prio,
                'statut': statut,
                'date_debut': date_debut.strftime('%Y-%m-%d'),
                'date_fin_prevue': date_fin.strftime('%Y-%m-%d'),
                'avancement': avanc,
                'budget_estime': budget,
                'budget_initial': budget,
                'budget_actuel': budget,
                'budget_consomme': budget * avanc / 100,
                'chef_projet_id': user_ids[i % len(user_ids)],
                'responsable_id': user_ids[(i + 1) % len(user_ids)],
                'ap_id': ap_ids[i] if i < len(ap_ids) else None,
            })
            projet_ids.append(projet_id)
        
        logger.info(f"✓ {len(projet_ids)} projets créés")
        
        # ==================== PROJET ASSOCIATIONS ====================
        logger.info("Création des associations projets...")
        
        # projet_contacts
        projet_contacts_data = [
            # PRJ2024-001
            (projet_ids[0], contact_ids[0], 'SPONSOR'),
            (projet_ids[0], contact_ids[2], 'REFERENT'),
            (projet_ids[0], contact_ids[5], 'INFORME'),
            # PRJ2024-002
            (projet_ids[1], contact_ids[1], 'SPONSOR'),
            (projet_ids[1], contact_ids[2], 'VALIDEUR'),
            (projet_ids[1], contact_ids[7], 'REFERENT'),
            # PRJ2024-003
            (projet_ids[2], contact_ids[2], 'SPONSOR'),
            (projet_ids[2], contact_ids[9], 'REFERENT'),
            # PRJ2024-004
            (projet_ids[3], contact_ids[4], 'VALIDEUR'),
            (projet_ids[3], contact_ids[2], 'REFERENT'),
            # PRJ2024-005
            (projet_ids[4], contact_ids[0], 'SPONSOR'),
            (projet_ids[4], contact_ids[2], 'VALIDEUR'),
            (projet_ids[4], contact_ids[8], 'REFERENT'),
        ]
        
        for projet_id, contact_id, role in projet_contacts_data:
            db_service.insert('projet_contacts', {
                'projet_id': projet_id,
                'contact_id': contact_id,
                'role': role,
            })
        
        logger.info(f"✓ {len(projet_contacts_data)} associations projet-contacts créées")
        
        # projet_equipe
        projet_equipe_data = [
            (projet_ids[0], user_ids[0]),
            (projet_ids[0], user_ids[2]),
            (projet_ids[1], user_ids[1]),
            (projet_ids[1], user_ids[2]),
            (projet_ids[2], user_ids[0]),
            (projet_ids[3], user_ids[1]),
            (projet_ids[4], user_ids[0]),
            (projet_ids[4], user_ids[1]),
        ]
        
        for projet_id, utilisateur_id in projet_equipe_data:
            db_service.insert('projet_equipe', {
                'projet_id': projet_id,
                'utilisateur_id': utilisateur_id,
            })
        
        logger.info(f"✓ {len(projet_equipe_data)} associations projet-équipe créées")
        
        # projet_prestataires (only ACTIF fournisseurs)
        # Get ACTIF fournisseur IDs based on statut field
        actif_fournisseur_ids = []
        for i, f_id in enumerate(fournisseur_ids):
            # fournisseurs tuple: (nom, siret, adresse, cp, ville, tel, email, contact, statut, notes)
            # Index 8 is statut
            if fournisseurs[i][8] == 'ACTIF':
                actif_fournisseur_ids.append(f_id)
        projet_prestataires_data = [
            (projet_ids[0], actif_fournisseur_ids[0]),  # Dell France
            (projet_ids[1], actif_fournisseur_ids[1]),  # Microsoft France
            (projet_ids[2], actif_fournisseur_ids[2]),  # Orange Business
            (projet_ids[3], actif_fournisseur_ids[0]),  # Dell France
            (projet_ids[4], actif_fournisseur_ids[3]),  # IBM France
        ]
        
        for projet_id, fournisseur_id in projet_prestataires_data:
            db_service.insert('projet_prestataires', {
                'projet_id': projet_id,
                'fournisseur_id': fournisseur_id,
            })
        
        logger.info(f"✓ {len(projet_prestataires_data)} associations projet-prestataires créées")
        
        # ==================== TÂCHES ====================
        logger.info("Création des tâches...")
        
        taches_par_projet = [
            [
                ('Analyse de l\'existant', 'A_FAIRE', 'HAUTE', -10, 14, 40, 'urgent, réseau'),
                ('Choix fournisseur', 'EN_COURS', 'HAUTE', 4, 21, 35, 'réseau, infrastructure'),
                ('Installation matériel', 'EN_ATTENTE', 'MOYENNE', 25, 30, 80, 'infrastructure, déploiement'),
                ('Tests et recette', 'EN_ATTENTE', 'CRITIQUE', 55, 14, 20, 'urgent, test'),
            ],
            [
                ('Rédaction cahier des charges', 'TERMINE', 'CRITIQUE', -30, 30, 120, 'application, documentation'),
                ('Consultation fournisseurs', 'EN_COURS', 'CRITIQUE', 0, 45, 60, 'application, marché'),
                ('Déploiement pilote', 'EN_ATTENTE', 'HAUTE', 45, 60, 100, 'application, backend'),
                ('Formation utilisateurs', 'EN_ATTENTE', 'MOYENNE', 105, 30, 40, 'application, formation'),
            ],
            [
                ('Audit technique', 'EN_COURS', 'HAUTE', 0, 15, 50, 'infrastructure, sécurité'),
                ('Rapport d\'audit', 'EN_ATTENTE', 'HAUTE', 15, 10, 30, 'sécurité, documentation'),
                ('Plan d\'action', 'EN_ATTENTE', 'CRITIQUE', 25, 15, 40, 'urgent, sécurité'),
            ],
            [
                ('Inventaire matériel actuel', 'TERMINE', 'HAUTE', -20, 10, 20, 'infrastructure, inventaire'),
                ('Commande nouveaux postes', 'EN_COURS', 'HAUTE', -5, 30, 60, 'infrastructure, matériel'),
                ('Installation et déploiement', 'A_FAIRE', 'MOYENNE', 25, 45, 150, 'infrastructure, déploiement'),
            ],
            [
                ('Étude faisabilité Cloud', 'A_FAIRE', 'HAUTE', 30, 45, 80, 'infrastructure, cloud'),
                ('Sélection prestataire Cloud', 'A_FAIRE', 'HAUTE', 75, 30, 40, 'cloud, marché'),
            ],
        ]
        
        tache_count = 0
        for i, taches in enumerate(taches_par_projet):
            if i >= len(projet_ids):
                break
            for titre, statut, prio, jours_debut, duree, estimation_h, tags in taches:
                date_debut = datetime.now() + timedelta(days=jours_debut)
                date_fin = date_debut + timedelta(days=duree)
                date_echeance = date_fin
                avancement = 100 if statut == 'TERMINE' else (50 if statut == 'EN_COURS' else 0)
                
                db_service.insert('taches', {
                    'projet_id': projet_ids[i],
                    'titre': titre,
                    'statut': statut,
                    'priorite': prio,
                    'date_debut': date_debut.strftime('%Y-%m-%d'),
                    'date_fin_prevue': date_fin.strftime('%Y-%m-%d'),
                    'date_echeance': date_echeance.strftime('%Y-%m-%d'),
                    'duree_estimee': duree,
                    'estimation_heures': estimation_h,
                    'heures_reelles': float(estimation_h) * float(avancement) / 100.0 if avancement > 0 else 0,
                    'avancement': avancement,
                    'assignee_id': user_ids[tache_count % len(user_ids)],
                    'assigne_a': user_ids[tache_count % len(user_ids)],
                    'ordre': tache_count,
                    'tags': tags,
                })
                tache_count += 1
        
        logger.info(f"✓ {tache_count} tâches créées")
        
        # ==================== CONTRATS ====================
        logger.info("Création des contrats...")
        
        contrats = [
            ('2024-DSI-001', 'MARCHE_PUBLIC', 'Maintenance infrastructure réseau', 'INVESTISSEMENT', '2313', '01', 0, 120000, 120000, -60, 36),
            ('2024-DSI-002', 'ACCORD_CADRE', 'Licences Microsoft Enterprise', 'FONCTIONNEMENT', '011', '01', 1, 180000, 180000, -90, 24),
            ('2024-DSI-003', 'MAPA', 'Support technique niveau 3', 'FONCTIONNEMENT', '011', '01', 2, 90000, 90000, -30, 12),
            ('2024-DSI-004', 'CONVENTION', 'Hébergement Cloud', 'FONCTIONNEMENT', '011', '01', 3, 150000, 150000, 0, 36),
            ('2024-DSI-005', 'MARCHE_PUBLIC', 'Développement application métier', 'INVESTISSEMENT', '20', '01', 4, 250000, 250000, 30, 18),
        ]
        
        contrat_ids = []
        for numero, type_c, objet, type_b, nature, fonction, f_idx, montant, montant_t, jours_debut, duree_mois in contrats:
            date_debut = datetime.now() + timedelta(days=jours_debut)
            date_fin = date_debut + timedelta(days=duree_mois * 30)
            
            contrat_id = db_service.insert('contrats', {
                'numero_contrat': numero,
                'type_contrat': type_c,
                'objet': objet,
                'type_budget': type_b,
                'nature_comptable': nature,
                'fonction': fonction,
                'fournisseur_id': fournisseur_ids[f_idx],
                'montant_initial_ht': montant,
                'montant_total_ht': montant_t,
                'montant_ttc': montant_t * 1.20,
                'date_debut': date_debut.strftime('%Y-%m-%d'),
                'date_fin': date_fin.strftime('%Y-%m-%d'),
                'duree_mois': duree_mois,
                'reconduction_tacite': True,
                'nombre_reconductions': 1,
                'statut': 'ACTIF',
                'ap_id': ap_ids[0] if type_b == 'INVESTISSEMENT' else None,
            })
            contrat_ids.append(contrat_id)
        
        logger.info(f"✓ {len(contrat_ids)} contrats créés")
        
        # ==================== BONS DE COMMANDE ====================
        logger.info("Création des bons de commande...")
        
        bcs = [
            ('BC2024-0001', 'INVESTISSEMENT', '2313', '01', 'OP-2024-INF-001', 'Serveurs Dell PowerEdge', 0, 45000, 20, -5, 30, 'VALIDE', True),
            ('BC2024-0002', 'FONCTIONNEMENT', '011', '01', '', 'Licences Office 365', 1, 25000, 20, -10, 15, 'VALIDE', True),
            ('BC2024-0003', 'INVESTISSEMENT', '2313', '01', 'OP-2024-INF-001', 'Switchs réseau Cisco', 2, 32000, 20, 0, 45, 'EN_ATTENTE', False),
            ('BC2024-0004', 'FONCTIONNEMENT', '011', '01', '', 'Support technique annuel', 3, 18000, 20, -30, 365, 'IMPUTE', True),
            ('BC2024-0005', 'INVESTISSEMENT', '2313', '01', 'OP-2024-APP-001', 'Serveurs application', 0, 55000, 20, 5, 60, 'BROUILLON', False),
            ('BC2024-0006', 'FONCTIONNEMENT', '011', '01', '', 'Formation utilisateurs ERP', 3, 12000, 20, 10, 30, 'BROUILLON', False),
            ('BC2024-0007', 'INVESTISSEMENT', '21', '01', 'OP-2024-MAT-001', 'Postes de travail Dell', 0, 180000, 20, -15, 45, 'VALIDE', True),
            ('BC2024-0008', 'FONCTIONNEMENT', '011', '01', '', 'Maintenance préventive', 4, 8500, 20, 15, 90, 'BROUILLON', False),
        ]
        
        bc_ids = []
        for numero, type_b, nature, fonction, operation, objet, f_idx, montant_ht, tva, jours_creation, jours_livraison, statut, valide in bcs:
            date_creation = datetime.now() + timedelta(days=jours_creation)
            date_livraison = date_creation + timedelta(days=jours_livraison)
            montant_ttc = montant_ht * (1 + tva/100)
            
            bc_data = {
                'numero_bc': numero,
                'date_creation': date_creation.strftime('%Y-%m-%d'),
                'type_budget': type_b,
                'nature_comptable': nature,
                'fonction': fonction,
                'operation': operation if operation else None,
                'objet': objet,
                'description': f'Description détaillée du BC {numero}',
                'fournisseur_id': fournisseur_ids[f_idx],
                'montant_ht': montant_ht,
                'montant_ttc': montant_ttc,
                'tva': tva,
                'statut': statut,
                'valide': valide,
                'date_livraison_prevue': date_livraison.strftime('%Y-%m-%d'),
            }
            
            # Si validé, ajouter les infos d'imputation
            if valide:
                bc_data['impute'] = True
                bc_data['date_validation'] = date_creation.isoformat()
                bc_data['date_imputation'] = date_creation.isoformat()
                bc_data['montant_engage'] = montant_ttc
                bc_data['valideur_id'] = user_ids[1]
            
            bc_id = db_service.insert('bons_commande', bc_data)
            bc_ids.append(bc_id)
        
        logger.info(f"✓ {len(bc_ids)} bons de commande créés")
        
        # ==================== TO-DO ====================
        logger.info("Création des to-do...")
        
        todos = [
            ('Valider le BC2024-0003', 'BC en attente de validation pour switchs réseau', 'HAUTE', 'A_FAIRE', 2),
            ('Préparer réunion ERP', 'Organiser la réunion de lancement du projet ERP', 'MOYENNE', 'EN_COURS', 5),
            ('Réviser budget DSI', 'Révision du budget pour le prochain exercice', 'CRITIQUE', 'A_FAIRE', 7),
            ('Suivre livraison serveurs', 'Vérifier l\'avancement de la livraison des serveurs Dell', 'HAUTE', 'A_FAIRE', 3),
            ('Audit sécurité - rapport', 'Finaliser le rapport d\'audit de sécurité', 'HAUTE', 'EN_COURS', 10),
            ('Formation équipe Cloud', 'Organiser formation Cloud pour l\'équipe technique', 'MOYENNE', 'A_FAIRE', 15),
            ('Renouveler contrat Orange', 'Le contrat arrive à échéance dans 3 mois', 'CRITIQUE', 'A_FAIRE', 30),
        ]
        
        for titre, desc, prio, statut, jours_echeance in todos:
            date_echeance = datetime.now() + timedelta(days=jours_echeance)
            
            db_service.insert('todos', {
                'titre': titre,
                'description': desc,
                'priorite': prio,
                'statut': statut,
                'date_echeance': date_echeance.strftime('%Y-%m-%d'),
                'assignee_id': user_ids[0],
                'tags': '["DSI", "Budget"]',
            })
        
        logger.info(f"✓ {len(todos)} to-do créés")
        
        # ==================== NOTIFICATIONS ====================
        logger.info("Création des notifications...")
        
        notifications = [
            ('BC_VALIDATION', 'BC en attente de validation', 'Le bon de commande BC2024-0003 est en attente de validation', 'HAUTE', 0),
            ('CONTRAT_ECHEANCE', 'Contrat arrive à échéance', 'Le contrat 2024-DSI-002 arrive à échéance dans 2 mois', 'MOYENNE', 1),
            ('BUDGET_ALERTE', 'Alerte budget', 'Le budget de l\'AP-2024-001 est consommé à 85%', 'CRITIQUE', 1),
        ]
        
        for type_n, titre, message, prio, user_idx in notifications:
            db_service.insert('notifications', {
                'type_notification': type_n,
                'titre': titre,
                'message': message,
                'priorite': prio,
                'utilisateur_id': user_ids[user_idx],
                'lue': False,
            })
        
        logger.info(f"✓ {len(notifications)} notifications créées")
        
        conn.commit()
        
        logger.info("\n" + "="*50)
        logger.info("✅ DONNÉES DE TEST CRÉÉES AVEC SUCCÈS !")
        logger.info("="*50)
        logger.info(f"- {len(user_ids)} utilisateurs")
        logger.info(f"- {len(service_ids)} services")
        logger.info(f"- {len(contact_ids)} contacts")
        logger.info(f"- {len(fournisseur_ids)} fournisseurs")
        logger.info(f"- {len(ap_ids)} autorisations de programme")
        logger.info(f"- {len(cp_ids)} crédits de paiement")
        logger.info(f"- {len(projet_ids)} projets")
        logger.info(f"- {len(projet_contacts_data)} associations projet-contacts")
        logger.info(f"- {len(projet_equipe_data)} associations projet-équipe")
        logger.info(f"- {len(projet_prestataires_data)} associations projet-prestataires")
        logger.info(f"- {tache_count} tâches")
        logger.info(f"- {len(contrat_ids)} contrats")
        logger.info(f"- {len(bc_ids)} bons de commande")
        logger.info(f"- {len(todos)} to-do")
        logger.info(f"- {len(notifications)} notifications")
        logger.info("="*50)
        
    except Exception as e:
        logger.error(f"Erreur création données de test: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    print("Création des données de test...")
    create_test_data()
    print("\nDonnées créées ! Vous pouvez maintenant lancer l'application avec: python run.py")
