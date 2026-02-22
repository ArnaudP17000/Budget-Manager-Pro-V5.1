"""
Modèle Fournisseur simplifié.
"""

class Fournisseur:
    """Modèle représentant un fournisseur."""
    
    def __init__(self, id=None, nom='', statut='ACTIF', notes=''):
        self.id = id
        self.nom = nom
        self.statut = statut  # ACTIF, INACTIF
        self.notes = notes
    
    def to_dict(self):
        """Convertit le fournisseur en dictionnaire."""
        return {
            'id': self.id,
            'nom': self.nom,
            'statut': self.statut,
            'notes': self.notes,
        }
    
    @classmethod
    def from_dict(cls, data):
        """Crée un Fournisseur depuis un dictionnaire."""
        return cls(
            id=data.get('id'),
            nom=data.get('nom', ''),
            statut=data.get('statut', 'ACTIF'),
            notes=data.get('notes', ''),
        )
    
    @property
    def is_actif(self):
        """Retourne True si le fournisseur est actif."""
        return self.statut == 'ACTIF'
    
    def __str__(self):
        return self.nom
