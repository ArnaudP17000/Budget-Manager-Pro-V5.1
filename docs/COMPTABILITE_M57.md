# Comptabilité M57 - Budget Manager Pro

## 📚 Introduction à la M57

La nomenclature M57 est l'instruction budgétaire et comptable des collectivités territoriales et de leurs établissements publics. Elle régit la comptabilité publique locale.

## 🏛️ Structure de la M57

### Organisation budgétaire

```
BUDGET
  ├─ SECTION INVESTISSEMENT
  │   ├─ Opérations
  │   │   ├─ Chapitre
  │   │   │   └─ Article
  │   │   └─ Fonction
  │   └─ AP (Autorisations de Programme)
  │       └─ CP (Crédits de Paiement)
  │
  └─ SECTION FONCTIONNEMENT
      ├─ Chapitre
      │   └─ Article
      └─ Fonction
```

## 📊 Chapitres M57

### Section Investissement

**Dépenses** :

| Chapitre | Libellé | Utilisation DSI |
|----------|---------|-----------------|
| **20** | Immobilisations incorporelles | Logiciels, licences |
| **21** | Immobilisations corporelles | Matériels informatiques |
| **2313** | Matériels informatiques | Serveurs, postes, réseau |
| **23** | Immobilisations en cours | Projets en cours |

**Recettes** :
- 10 : Dotations, fonds divers
- 13 : Subventions d'investissement
- 16 : Emprunts

### Section Fonctionnement

**Dépenses** :

| Chapitre | Libellé | Utilisation DSI |
|----------|---------|-----------------|
| **011** | Charges à caractère général | Fournitures, services extérieurs |
| **012** | Charges de personnel | Salaires, formations |
| **65** | Autres charges de gestion | Maintenance, abonnements |
| **66** | Charges financières | Intérêts emprunts |
| **67** | Charges exceptionnelles | Imprévus |

**Recettes** :
- 70 : Produits des services
- 73 : Impôts et taxes
- 74 : Dotations et participations

## 🎯 Fonctions M57

Les fonctions permettent de classer les dépenses par domaine d'intervention :

| Code | Libellé | Exemples DSI |
|------|---------|--------------|
| **01** | Services généraux | Infrastructure DSI, support |
| **020** | Enseignement | SI des écoles |
| **30** | Culture | SI médiathèque, musées |
| **40** | Sport et jeunesse | SI centres sportifs |
| **50** | Interventions sociales | SI CCAS |
| **60** | Famille | SI crèches |
| **70** | Logement | SI logements sociaux |
| **80** | Aménagement urbain | SI urbanisme |
| **90** | Environnement | SI environnement |

## 💰 Autorisations de Programme (AP)

### Définition

Une **AP** est une enveloppe budgétaire **pluriannuelle** qui autorise la réalisation d'un investissement sur plusieurs exercices.

### Caractéristiques

- **Pluriannuelle** : 2 à 5 ans généralement
- **Investissement uniquement**
- **Vote du conseil**
- **Montant global** de l'opération
- **Découpage en CP** par exercice

### Exemple

**AP-2024-001 : Modernisation infrastructure réseau**

```
Montant total : 500 000 €
Période : 2024-2026

Chapitre : 2313 (Matériels informatiques)
Fonction : 01 (Services généraux)
Opération : OP-2024-INF-001

Détail :
- Étude et conception : 50 000 €
- Matériels : 300 000 €
- Installation : 100 000 €
- Formation et doc : 50 000 €
```

### Cycle de vie

1. **Création** : Vote du conseil
2. **Active** : Consommation via CP
3. **Clôturée** : Opération terminée
4. **Annulée** : Projet abandonné

## 💳 Crédits de Paiement (CP)

### Définition

Un **CP** est le crédit budgétaire **annuel** rattaché à une AP, correspondant aux dépenses de l'exercice.

### Caractéristiques

- **Annuel** : Un CP par exercice
- **Rattaché à une AP**
- **Montant voté** au BP (Budget Primitif)
- **Ajustable** par DM (Décision Modificative)
- **Consommé** par les engagements

### Exemple

Pour l'AP-2024-001 (500 000 €) :

**CP 2024** :
```
Montant voté : 150 000 € (30%)
Affectation :
- Étude : 50 000 €
- Premiers matériels : 100 000 €
```

**CP 2025** :
```
Montant voté : 200 000 € (40%)
Affectation :
- Matériels principaux : 200 000 €
```

**CP 2026** :
```
Montant voté : 150 000 € (30%)
Affectation :
- Installation : 100 000 €
- Formation : 50 000 €
```

### Gestion

```
CP voté
  ├─ Disponible (non engagé)
  ├─ Engagé (BC validés, contrats)
  │   ├─ Non mandaté
  │   └─ Mandaté (factures payées)
  └─ RAR (Reste à Réaliser)
```

## 📝 Engagements budgétaires

### Définition

Un **engagement** réserve un crédit budgétaire pour une dépense future (BC, contrat).

### Moment de l'engagement

- **BC** : À la validation (case cochée)
- **Contrat** : À la signature
- **Marché** : À la notification

### Impact

```
AVANT engagement :
CP disponible = 150 000 €
CP engagé = 0 €

APRÈS engagement BC 45 000 € :
CP disponible = 105 000 €
CP engagé = 45 000 €

Taux d'engagement = 45 000 / 150 000 = 30%
```

### Contrôle

Le système vérifie **automatiquement** :
- CP disponible ≥ Montant à engager
- Sinon : ❌ **Blocage** + Message

## 🔄 Processus budgétaire

### 1. Préparation du budget

**Septembre-Octobre N-1** :
1. Recensement des besoins DSI
2. Priorisation des projets
3. Estimation des coûts
4. Constitution des AP

**Exemple** :
- AP-2024-001 : Infrastructure (500 k€)
- AP-2024-002 : ERP (800 k€)
- AP-2024-003 : Sécurité (300 k€)

### 2. Vote du budget

**Décembre N-1** :
1. Présentation au conseil
2. Vote du Budget Primitif (BP)
3. AP autorisées
4. CP de l'exercice N votés

### 3. Exécution

**Janvier-Décembre N** :

1. **Engagement** :
   - Validation BC → Engagement
   - Signature contrat → Engagement

2. **Liquidation** :
   - Réception marchandise/service
   - Vérification facture

3. **Mandatement** :
   - Ordre de payer
   - Paiement effectif

### 4. Suivi

**En continu** :
- Dashboard Budget Manager Pro
- Contrôle disponibilité
- Alertes dépassement

**Mensuel** :
- Tableau de bord budgétaire
- Analyse des écarts
- Projections fin d'année

### 5. Clôture

**Décembre N** :
1. Calcul des RAR (Restes à Réaliser)
2. Reports N+1
3. Bilan budgétaire

## 📊 Indicateurs budgétaires

### Taux d'engagement

```
Taux = (Montant engagé / Montant voté) × 100
```

**Interprétation** :
- < 50% : Sous-consommation
- 50-80% : Normal
- 80-95% : Vigilance
- > 95% : Alerte

### Taux de mandatement

```
Taux = (Montant mandaté / Montant engagé) × 100
```

**Interprétation** :
- < 50% : Retard paiement
- 50-80% : Normal
- > 80% : Bon suivi

### RAR (Reste à Réaliser)

```
RAR = CP voté - Montant mandaté
```

Le RAR est reporté sur l'exercice suivant.

## 🔍 Exemples pratiques DSI

### Exemple 1 : Achat de serveurs

**Classification** :
- Nature : **2313** (Matériels informatiques)
- Fonction : **01** (Services généraux)
- Type budget : **INVESTISSEMENT**

**Processus** :
1. AP existante : AP-2024-001
2. CP 2024 : 150 000 € disponibles
3. BC : BC2024-0001
   - Montant : 45 000 € HT (54 000 € TTC)
   - Fournisseur : Dell France
   - Validation → Engagement automatique
4. Réception → Facture → Mandatement

**Impact budget** :
```
CP disponible : 150 000 - 54 000 = 96 000 €
CP engagé : 54 000 €
Taux : 36%
```

### Exemple 2 : Licences logicielles

**Classification** :
- Si < 500€ ou durée < 1 an :
  - Nature : **011** (Charges générales)
  - Type : **FONCTIONNEMENT**
- Si > 500€ et durée > 1 an :
  - Nature : **20** (Immobilisations incorporelles)
  - Type : **INVESTISSEMENT**

**Exemple** : Licences Microsoft 365 (25 000 € / an)
- Nature : **011**
- Fonction : **01**
- Type : **FONCTIONNEMENT**
- BC annuel

### Exemple 3 : Maintenance

**Classification** :
- Nature : **65** (Autres charges)
- Fonction : **01**
- Type : **FONCTIONNEMENT**

**Contrat de maintenance** :
- 90 000 € HT / an
- 3 ans
- Montant total : 270 000 €

**Engagement** :
- Année 1 : 108 000 € TTC
- Années 2-3 : Reconduction

## ⚠️ Pièges à éviter

### 1. Mauvaise classification

❌ **Erreur** : Matériel < 500€ en investissement  
✅ **Correct** : Fonctionnement (011)

### 2. Oubli de l'opération

❌ **Erreur** : AP sans code opération  
✅ **Correct** : Toujours renseigner (ex: OP-2024-INF-001)

### 3. Dépassement CP

❌ **Erreur** : Engager sans vérifier le disponible  
✅ **Correct** : Budget Manager Pro bloque automatiquement

### 4. AP/CP incohérents

❌ **Erreur** : Σ CP > Montant AP  
✅ **Correct** : Σ CP ≤ Montant AP

### 5. Fonction inadaptée

❌ **Erreur** : SI école en fonction 01  
✅ **Correct** : Fonction 020 (Enseignement)

## 📋 Récapitulatif

| Concept | Durée | Section | Utilisation |
|---------|-------|---------|-------------|
| **AP** | Pluriannuelle | Investissement | Enveloppe globale projet |
| **CP** | Annuelle | Investissement | Crédit annuel de l'AP |
| **Chapitre** | - | Inv. ou Fonct. | Classification comptable |
| **Fonction** | - | Inv. ou Fonct. | Domaine d'intervention |
| **Engagement** | Ponctuel | Les deux | Réservation crédit |
| **Mandatement** | Ponctuel | Les deux | Paiement effectif |

## 🎓 Pour aller plus loin

- Instruction M57 complète (DGCL)
- Guides pratiques INET
- Formation comptabilité publique
- Échanges avec le service financier

---

**Budget Manager Pro automatise tous ces contrôles !**
