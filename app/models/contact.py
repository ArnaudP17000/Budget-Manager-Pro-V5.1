"""
Modèle Contact pour l'annuaire.
"""

class Contact:
    """Modèle représentant un contact."""
    
    def __init__(self, id=None, nom='', prenom='', fonction='', type='DIRECTION',
                 telephone='', email='', service_id=None, organisation=''):
        self.id = id
        self.nom = nom
        self.prenom = prenom
        self.fonction = fonction
        self.type = type  # ELU, DIRECTION, PRESTATAIRE, AMO
        self.telephone = telephone
        self.email = email
        self.service_id = service_id
        self.organisation = organisation  # Si externe
    
    def to_dict(self):
        """Convertit le contact en dictionnaire."""
        return {
            'id': self.id,
            'nom': self.nom,
            'prenom': self.prenom,
            'fonction': self.fonction,
            'type': self.type,
            'telephone': self.telephone,
            'email': self.email,
            'service_id': self.service_id,
            'organisation': self.organisation,
        }
    
    @classmethod
    def from_dict(cls, data):
        """Crée un Contact depuis un dictionnaire."""
        return cls(
            id=data.get('id'),
            nom=data.get('nom', ''),
            prenom=data.get('prenom', ''),
            fonction=data.get('fonction', ''),
            type=data.get('type', 'DIRECTION'),
            telephone=data.get('telephone', ''),
            email=data.get('email', ''),
            service_id=data.get('service_id'),
            organisation=data.get('organisation', ''),
        )
    
    @property
    def nom_complet(self):
        """Retourne le nom complet."""
        return f"{self.prenom} {self.nom}".strip()
    
    def __str__(self):
        return self.nom_complet
