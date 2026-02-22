"""
Modèle Service pour l'organigramme.
"""

class Service:
    """Modèle représentant un service."""
    
    def __init__(self, id=None, code='', nom='', responsable_id=None, parent_id=None):
        self.id = id
        self.code = code
        self.nom = nom
        self.responsable_id = responsable_id
        self.parent_id = parent_id
    
    def to_dict(self):
        """Convertit le service en dictionnaire."""
        return {
            'id': self.id,
            'code': self.code,
            'nom': self.nom,
            'responsable_id': self.responsable_id,
            'parent_id': self.parent_id,
        }
    
    @classmethod
    def from_dict(cls, data):
        """Crée un Service depuis un dictionnaire."""
        return cls(
            id=data.get('id'),
            code=data.get('code', ''),
            nom=data.get('nom', ''),
            responsable_id=data.get('responsable_id'),
            parent_id=data.get('parent_id'),
        )
    
    def __str__(self):
        return f"{self.code} - {self.nom}" if self.code else self.nom
