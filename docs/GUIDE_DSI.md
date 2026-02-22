# Guide DSI - Budget Manager Pro V4.2

## 🎯 Introduction

Ce guide s'adresse aux responsables DSI des collectivités territoriales pour la gestion complète des projets informatiques avec le budget en nomenclature M57.

## 📋 Workflow projet DSI complet

### 1. Planification budgétaire

#### Créer une Autorisation de Programme (AP)

```
Début d'exercice → Nouvelle AP → Classification M57
```

**Exemple** : Modernisation infrastructure réseau
- Numéro : AP-2024-001
- Montant : 500 000 €
- Exercices : 2024-2026 (3 ans)
- Chapitre M57 : 2313 (Matériels informatiques)
- Fonction : 01 (Services généraux)
- Opération : OP-2024-INF-001

#### Créer les Crédits de Paiement (CP)

Pour chaque exercice de l'AP :

**Exercice 2024** :
- Montant voté : 150 000 € (30%)
- Montant disponible : 150 000 €

**Exercice 2025** :
- Montant voté : 200 000 € (40%)

**Exercice 2026** :
- Montant voté : 150 000 € (30%)

### 2. Création du projet

```
AP créée → Nouveau projet → Rattacher à l'AP
```

**Champs importants** :
- Nom du projet
- Type : Infrastructure, Application, Réseau, Sécurité
- Phase initiale : ETUDE
- Chef de projet : Affecter un agent DSI
- Budget estimé : Doit correspondre à l'AP
- AP : Sélectionner l'AP créée

### 3. Phase d'étude

**Actions** :
1. Créer le **Cahier des Charges** (CDC)
2. Créer des **tâches** :
   - Analyse de l'existant
   - Rédaction CDC
   - Consultation marché
3. Affecter les tâches aux agents
4. Créer des **to-do** liées au projet

**Documents** :
- Étude de faisabilité
- Analyse des besoins
- CDC finalisé

### 4. Consultation et contractualisation

#### Créer le contrat/marché

```
Projet en phase CONCEPTION → Nouveau contrat → Type marché
```

**Exemple** : Marché public infrastructure réseau
- Numéro : 2024-DSI-001
- Type : MARCHE_PUBLIC
- Montant : 400 000 € HT
- Durée : 36 mois
- Classification : INVESTISSEMENT
- Chapitre M57 : 2313
- Fonction : 01
- Rattachement : AP-2024-001

**Alertes automatiques** :
- 6 mois avant échéance
- 3 mois avant échéance
- 1 mois avant échéance

### 5. Phase de réalisation

#### Créer les Bons de Commande

```
Contrat actif → Nouveau BC → Rattacher au contrat
```

**BC1 : Matériel initial**
- Numéro : BC2024-0001 (manuel !)
- Type budget : **INVESTISSEMENT**
- Nature comptable : 2313
- Fonction : 01
- Opération : OP-2024-INF-001
- Objet : Serveurs Dell PowerEdge
- Montant HT : 45 000 €
- Fournisseur : Dell France
- Contrat : 2024-DSI-001
- ✅ **Cocher "BC Validé"**
- → **Imputation automatique** sur CP 2024 !

**BC2 : Installation**
- Numéro : BC2024-0015
- Montant : 25 000 €
- Validation → Imputation automatique

**Suivi** :
- Total BC : 70 000 €
- CP disponible : 150 000 - 70 000 = 80 000 €
- Taux d'engagement : 46,7%

#### Mettre à jour le projet

- Passer en phase **REALISATION**
- Mettre à jour l'avancement : 25% → 50% → 75%
- Budget consommé : Synchronisé avec les BC
- Créer des jalons (milestones)

### 6. Phase de recette

**Actions** :
1. Passer le projet en phase **RECETTE**
2. Créer des tâches de validation :
   - Tests techniques
   - Tests utilisateurs
   - Recette fonctionnelle
   - Formation
3. Créer le document de recette
4. Valider la livraison des BC
5. Mettre à jour l'avancement : 90% → 100%

### 7. Clôture

**Vérifications** :
- ✅ Tous les BC sont réceptionnés
- ✅ Toutes les factures sont payées
- ✅ Budget consommé = Budget prévu (ou ajusté)
- ✅ Documentation complète
- ✅ Formation effectuée

**Actions** :
1. Passer le projet en phase **CLOTURE**
2. Statut : TERMINE
3. Date de fin réelle
4. Rapport de clôture
5. Archiver les documents

## 📊 Suivi budgétaire M57

### Structure budgétaire

```
AP (Pluriannuelle)
  ├─ CP Exercice 2024
  │   ├─ Engagement BC2024-0001
  │   ├─ Engagement BC2024-0002
  │   └─ Mandatement Facture
  │
  ├─ CP Exercice 2025
  │   └─ Engagement BC2025-0001
  │
  └─ CP Exercice 2026
      └─ Engagement BC2026-0001
```

### Contrôles automatiques

Le système vérifie **automatiquement** :

1. **Disponibilité budgétaire** :
   - CP disponible ≥ Montant BC
   - Sinon : ❌ Blocage

2. **Alertes dépassement** :
   - Engagement > 80% → ⚠️ Alerte
   - Engagement > 95% → 🔴 Critique

3. **Cohérence AP/CP** :
   - Σ CP ≤ AP
   - Exercices dans la période AP

### Imputation automatique BC

Lors de la **validation d'un BC** (case cochée) :

1. **Vérification** :
   - CP disponible pour l'exercice en cours ?
   - Classification M57 cohérente ?

2. **Imputation** :
   - Création d'un **engagement budgétaire**
   - Montant engagé = Montant TTC du BC
   - CP disponible = CP disponible - Montant TTC
   - Date d'imputation = Date de validation

3. **Traçabilité** :
   - BC.impute = True
   - BC.date_imputation = Now()
   - BC.montant_engage = Montant TTC
   - BC.cp_id = CP de l'exercice

4. **Notification** :
   - Notification au responsable budget
   - Mise à jour du Dashboard

### RAR (Reste à Réaliser)

```
RAR = CP voté - (Engagements + Mandatements)
```

Calcul automatique dans le Dashboard.

## 🔔 Système d'alertes

### Alertes budgétaires

1. **Dépassement imminent** :
   - CP engagé > 80% → Alerte HAUTE
   - CP engagé > 95% → Alerte CRITIQUE

2. **AP bientôt consommée** :
   - Σ CP > 90% AP → Alerte

3. **BC bloqué** :
   - Montant BC > CP disponible → ❌ Blocage

### Alertes contrats

1. **Échéance proche** :
   - < 6 mois → ⚠️ Info
   - < 3 mois → 🔴 Critique
   - < 1 mois → 🔴🔴 Urgence

2. **Consommation élevée** :
   - Σ BC > 80% montant contrat → Alerte
   - Risque de dépassement

### Alertes projets

1. **Retard** :
   - Date fin prévue < Aujourd'hui + Avancement < 100%
   - Tâches en retard

2. **Dépassement budget** :
   - Budget consommé > Budget estimé

## 📈 Tableaux de bord DSI

### Dashboard principal

**KPI** :
- Projets actifs : 5
- Budget total AP : 2 600 000 €
- BC en attente : 3
- Contrats actifs : 12

**Budget** :
- Crédits votés : 850 000 €
- Disponibles : 510 000 €
- Engagés : 340 000 €
- Taux : 40%

**Alertes** :
- 3 BC en attente de validation
- 2 contrats à échéance < 3 mois
- 1 projet en retard

### Vue Budget détaillée

**Par exercice** :
```
Exercice 2024
  AP-2024-001 : 150 000 € (70% consommé)
  AP-2024-002 : 200 000 € (45% consommé)
  AP-2024-003 : 100 000 € (30% consommé)
```

**Par chapitre M57** :
```
2313 - Matériels informatiques : 350 000 €
20 - Immobilisations incorporelles : 180 000 €
011 - Charges générales : 120 000 €
```

### Vue Projets

**Par phase** :
- Étude : 2 projets
- Conception : 1 projet
- Réalisation : 3 projets
- Recette : 1 projet
- Clôture : 0 projet

**Par priorité** :
- Critique : 2
- Haute : 3
- Moyenne : 2

## 🔄 Processus spécifiques

### Virement de crédits

1. Identifier le CP source (excédent)
2. Identifier le CP cible (insuffisant)
3. Créer une décision modificative (DM)
4. Ajuster les CP :
   - CP source : -X €
   - CP cible : +X €

### Report de crédits N-1

Début d'exercice N :
1. Calculer le RAR de l'exercice N-1
2. Créer les CP de report :
   - Exercice : N
   - Montant : RAR N-1
   - Statut : Report

### Annulation d'engagement

Si BC annulé :
1. BC.statut = ANNULE
2. Libérer le crédit :
   - CP disponible += Montant BC
   - CP engagé -= Montant BC

## 💼 Bonnes pratiques DSI

### Organisation

1. **Prévoir les AP** :
   - En décembre N-1 pour N
   - Vote en conseil

2. **Créer les projets tôt** :
   - Dès l'AP votée
   - Planification complète

3. **Suivre régulièrement** :
   - Dashboard chaque jour
   - Réunion budget hebdomadaire
   - Mise à jour projets hebdomadaire

### Classification M57

**Fonctionnement** :
- 011 : Achats (licences, matériels < 500€)
- 012 : Personnel (formation)
- 65 : Autres charges (maintenance)

**Investissement** :
- 20 : Incorporel (logiciels, licences > 500€)
- 21 : Corporel (matériels > 500€)
- 2313 : Matériels informatiques

**Fonctions** :
- 01 : Services généraux (DSI)
- 020 : Enseignement (si école)
- 30 : Culture (si médiathèque)

### Sécurité budgétaire

1. **Ne jamais engager sans vérifier** :
   - CP disponible ✅
   - Classification correcte ✅

2. **Valider les BC rapidement** :
   - Éviter les blocages
   - Fluidifier les achats

3. **Anticiper les échéances** :
   - Contrats
   - Fin d'exercice
   - Clôtures

## 🆘 Dépannage

### BC bloqué "Crédit insuffisant"

**Problème** : Montant BC > CP disponible

**Solutions** :
1. Virement de crédits depuis autre CP
2. DM (Décision Modificative)
3. Réduire le montant du BC
4. Reporter au prochain exercice

### Contrat bientôt à échéance

**Actions** :
1. Dashboard → Alertes → Cliquer sur l'alerte
2. Consulter le contrat
3. Décider : Renouveler ou Résilier
4. Si renouvellement :
   - Créer avenant
   - Ou créer nouveau contrat

### Projet en retard

**Analyse** :
1. Voir les tâches en retard
2. Identifier les blocages
3. Actions correctives :
   - Réaffecter ressources
   - Ajuster planning
   - Escalade si nécessaire

---

**Pour toute question technique, consulter le README.md ou contacter le support.**
