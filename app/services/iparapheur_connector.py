"""
iparapheur_connector.py — Connecteur iParapheur pour Budget Manager Pro
Interroge l'API iParapheur pour lister les documents en attente de signature.

Supporte :
  - iParapheur v4  (SOAP/WSDL)
  - iParapheur v5  (REST JSON)

Usage direct :
    python app/services/iparapheur_connector.py

Configuration dans config/settings.py ou via variables d'environnement :
    IPARAPHEUR_URL, IPARAPHEUR_LOGIN, IPARAPHEUR_PASSWORD, IPARAPHEUR_VERSION
"""
import os
import sys
import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)


# ─── Configuration ────────────────────────────────────────────────────────────
# Modifier ces valeurs OU les mettre dans config/settings.py

IPARAPHEUR_URL      = os.environ.get('IPARAPHEUR_URL',      '')   # ex: https://parapheur.mairie.fr
IPARAPHEUR_LOGIN    = os.environ.get('IPARAPHEUR_LOGIN',    '')   # ex: dsi@mairie.fr
IPARAPHEUR_PASSWORD = os.environ.get('IPARAPHEUR_PASSWORD', '')   # mot de passe
IPARAPHEUR_VERSION  = os.environ.get('IPARAPHEUR_VERSION',  'v5') # 'v4' ou 'v5'

# Tenter de charger depuis config/settings.py
try:
    _here = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(_here))
    from config import settings as _s
    IPARAPHEUR_URL      = getattr(_s, 'IPARAPHEUR_URL',      IPARAPHEUR_URL)
    IPARAPHEUR_LOGIN    = getattr(_s, 'IPARAPHEUR_LOGIN',    IPARAPHEUR_LOGIN)
    IPARAPHEUR_PASSWORD = getattr(_s, 'IPARAPHEUR_PASSWORD', IPARAPHEUR_PASSWORD)
    IPARAPHEUR_VERSION  = getattr(_s, 'IPARAPHEUR_VERSION',  IPARAPHEUR_VERSION)
except Exception:
    pass


# ─── Connecteur v5 (REST) ─────────────────────────────────────────────────────

class IParapheurV5:
    """Connecteur REST pour iParapheur v5."""

    def __init__(self, url, login, password):
        self.base = url.rstrip('/')
        self.login = login
        self.password = password
        self._session = None

    def _get_session(self):
        import requests
        from requests.auth import HTTPBasicAuth
        if self._session is None:
            self._session = requests.Session()
            self._session.auth = HTTPBasicAuth(self.login, self.password)
            self._session.headers.update({
                'Accept':       'application/json',
                'Content-Type': 'application/json',
            })
            self._session.verify = False  # Certificats auto-signes courants en collectivite
        return self._session

    def test_connexion(self):
        """Teste la connexion. Retourne (ok, message)."""
        try:
            s = self._get_session()
            r = s.get(f"{self.base}/api/dossiers", timeout=10)
            if r.status_code in (200, 206):
                return True, f"Connexion OK (HTTP {r.status_code})"
            elif r.status_code == 401:
                return False, "Identifiants incorrects (401)"
            elif r.status_code == 403:
                return False, "Acces refuse (403) — verifiez les droits"
            else:
                return False, f"HTTP {r.status_code} : {r.text[:200]}"
        except Exception as e:
            return False, f"Connexion impossible : {e}"

    def get_documents_en_attente(self):
        """
        Retourne la liste des dossiers en attente de signature/visa.
        Format retour : liste de dicts avec id, titre, type, date_creation, etape
        """
        try:
            s = self._get_session()
            # Endpoint standard iParapheur v5
            params = {
                'statut': 'EN_ATTENTE',
                'page':   0,
                'size':   100,
            }
            r = s.get(f"{self.base}/api/dossiers", params=params, timeout=15)
            r.raise_for_status()
            data = r.json()

            # Normaliser selon la structure de la reponse
            dossiers_raw = data if isinstance(data, list) else data.get('content', data.get('dossiers', []))

            documents = []
            for d in dossiers_raw:
                documents.append({
                    'id':             d.get('id') or d.get('dossier_id', ''),
                    'titre':          d.get('titre') or d.get('nom') or d.get('libelle', ''),
                    'type':           d.get('type') or d.get('sousType', ''),
                    'statut':         d.get('statut') or d.get('etat', 'EN_ATTENTE'),
                    'etape':          d.get('etapeCourante') or d.get('etape', ''),
                    'date_creation':  (d.get('dateCreation') or d.get('date_creation', ''))[:10],
                    'date_limite':    (d.get('dateLimite') or d.get('date_limite', ''))[:10],
                    'emetteur':       d.get('emetteur') or d.get('createur', ''),
                    'circuit':        d.get('circuit') or d.get('nomCircuit', ''),
                })
            return True, documents

        except Exception as e:
            return False, str(e)

    def get_statistiques(self):
        """Retourne des stats rapides (nb en attente, urgents, etc.)."""
        ok, docs = self.get_documents_en_attente()
        if not ok:
            return False, docs
        stats = {
            'total_en_attente': len(docs),
            'urgents':          sum(1 for d in docs if d.get('date_limite') and
                                    d['date_limite'] < __import__('datetime').date.today().isoformat()),
            'par_type':         {},
        }
        for d in docs:
            t = d.get('type') or 'Autre'
            stats['par_type'][t] = stats['par_type'].get(t, 0) + 1
        return True, stats


# ─── Connecteur v4 (SOAP) ─────────────────────────────────────────────────────

class IParapheurV4:
    """Connecteur SOAP pour iParapheur v4."""

    WSDL = "/ws/iParapheur?wsdl"

    def __init__(self, url, login, password):
        self.base     = url.rstrip('/')
        self.login    = login
        self.password = password
        self._client  = None

    def _get_client(self):
        if self._client is None:
            try:
                from zeep import Client
                from zeep.transports import Transport
                import requests
                session = requests.Session()
                session.auth = (self.login, self.password)
                session.verify = False
                transport = Transport(session=session, timeout=15)
                self._client = Client(
                    f"{self.base}{self.WSDL}",
                    transport=transport
                )
            except ImportError:
                raise ImportError(
                    "zeep requis pour iParapheur v4 : pip install zeep")
        return self._client

    def test_connexion(self):
        try:
            client = self._get_client()
            # Appel de test sur l operation GetBureauEnCours
            result = client.service.GetBureauEnCours()
            return True, f"Connexion SOAP OK — Bureau : {result}"
        except Exception as e:
            return False, f"Erreur SOAP : {e}"

    def get_documents_en_attente(self):
        """Retourne les dossiers en attente via GetListeDossiers."""
        try:
            client = self._get_client()
            # Appel GetListeDossiers (standard iParapheur v4)
            result = client.service.GetListeDossiers(
                TypeTechnique='',
                SousType='',
                Statut='',
                NbResultats=100,
                PageNumber=0
            )
            dossiers_raw = result.Dossier if hasattr(result, 'Dossier') else []
            documents = []
            for d in (dossiers_raw or []):
                documents.append({
                    'id':            str(getattr(d, 'ref', '')),
                    'titre':         str(getattr(d, 'titre', '')),
                    'type':          str(getattr(d, 'typeTechnique', '')),
                    'statut':        str(getattr(d, 'status', 'EN_ATTENTE')),
                    'etape':         str(getattr(d, 'etape', '')),
                    'date_creation': str(getattr(d, 'dateCreation', ''))[:10],
                    'date_limite':   str(getattr(d, 'dateLimite', ''))[:10],
                    'emetteur':      str(getattr(d, 'emetteur', '')),
                    'circuit':       '',
                })
            return True, documents
        except Exception as e:
            return False, str(e)

    def get_statistiques(self):
        ok, docs = self.get_documents_en_attente()
        if not ok:
            return False, docs
        stats = {
            'total_en_attente': len(docs),
            'urgents':          0,
            'par_type':         {},
        }
        for d in docs:
            t = d.get('type') or 'Autre'
            stats['par_type'][t] = stats['par_type'].get(t, 0) + 1
        return True, stats


# ─── Factory ──────────────────────────────────────────────────────────────────

def get_connector(url=None, login=None, password=None, version=None):
    """Retourne le bon connecteur selon la version."""
    url      = url      or IPARAPHEUR_URL
    login    = login    or IPARAPHEUR_LOGIN
    password = password or IPARAPHEUR_PASSWORD
    version  = version  or IPARAPHEUR_VERSION

    if not url:
        raise ValueError(
            "IPARAPHEUR_URL non configure.\n"
            "Ajoutez dans config/settings.py :\n"
            "  IPARAPHEUR_URL      = 'https://parapheur.votre-collectivite.fr'\n"
            "  IPARAPHEUR_LOGIN    = 'votre@email.fr'\n"
            "  IPARAPHEUR_PASSWORD = 'motdepasse'\n"
            "  IPARAPHEUR_VERSION  = 'v5'  # ou 'v4'"
        )

    if version == 'v4':
        return IParapheurV4(url, login, password)
    return IParapheurV5(url, login, password)


# ─── Singleton pour l'appli ───────────────────────────────────────────────────

_connector_instance = None

def get_instance():
    global _connector_instance
    if _connector_instance is None:
        try:
            _connector_instance = get_connector()
        except ValueError:
            return None
    return _connector_instance


# ─── Lancement direct : diagnostic ────────────────────────────────────────────

if __name__ == '__main__':
    import urllib3
    urllib3.disable_warnings()

    print("=" * 60)
    print("  iParapheur Connector — Diagnostic")
    print("=" * 60)

    # Lire config interactive si pas configuree
    url      = IPARAPHEUR_URL
    login    = IPARAPHEUR_LOGIN
    password = IPARAPHEUR_PASSWORD
    version  = IPARAPHEUR_VERSION

    if not url:
        print("\nConfiguration non trouvee dans settings.py")
        print("Saisissez les informations de connexion :\n")
        url      = input("URL iParapheur (ex: https://parapheur.mairie.fr) : ").strip()
        login    = input("Login (email) : ").strip()
        password = input("Mot de passe : ").strip()
        version  = input("Version [v5/v4] (defaut: v5) : ").strip() or 'v5'
    else:
        print(f"\nURL      : {url}")
        print(f"Login    : {login}")
        print(f"Version  : {version}")

    if not url:
        print("\nERREUR : URL non saisie. Abandon.")
        sys.exit(1)

    print("\n[1/3] Test de connexion...")
    try:
        connector = get_connector(url, login, password, version)
        ok, msg = connector.test_connexion()
        if ok:
            print(f"  OK  {msg}")
        else:
            print(f"  ECHEC  {msg}")
            print("\nVerifiez l URL, le login et le mot de passe.")
            sys.exit(1)
    except Exception as e:
        print(f"  ERREUR : {e}")
        sys.exit(1)

    print("\n[2/3] Recuperation des documents en attente...")
    ok, result = connector.get_documents_en_attente()
    if not ok:
        print(f"  ECHEC : {result}")
        sys.exit(1)

    documents = result
    print(f"  {len(documents)} document(s) en attente\n")

    if documents:
        print(f"  {'ID':<12} {'Titre':<40} {'Type':<20} {'Date':<12} {'Limite':<12}")
        print("  " + "-" * 100)
        for d in documents:
            titre  = (d.get('titre') or '')[:38]
            type_  = (d.get('type')  or '')[:18]
            date_  = d.get('date_creation', '')
            limite = d.get('date_limite', '')
            id_    = str(d.get('id', ''))[:10]
            print(f"  {id_:<12} {titre:<40} {type_:<20} {date_:<12} {limite:<12}")

    print("\n[3/3] Statistiques...")
    ok, stats = connector.get_statistiques()
    if ok:
        print(f"  Total en attente : {stats['total_en_attente']}")
        if stats.get('urgents'):
            print(f"  URGENTS (date limite depassee) : {stats['urgents']}")
        if stats.get('par_type'):
            print("  Par type :")
            for t, n in stats['par_type'].items():
                print(f"    {t} : {n}")
    else:
        print(f"  Stats indisponibles : {stats}")

    print("\nDiagnostic termine.")
    print("\nPour integrer dans l appli, ajoutez dans config/settings.py :")
    print(f"  IPARAPHEUR_URL      = '{url}'")
    print(f"  IPARAPHEUR_LOGIN    = '{login}'")
    print(f"  IPARAPHEUR_PASSWORD = '****'")
    print(f"  IPARAPHEUR_VERSION  = '{version}'")
