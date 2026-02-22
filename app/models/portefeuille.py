# -*- coding: utf-8 -*-
"""
Modèle Portefeuille
"""

class Portefeuille:
    """Modèle représentant un portefeuille de projets."""
    
    def __init__(self, id=None, nom='', description='', responsable='',
                 created_at=None, updated_at=None):
        self.id = id
        self.nom = nom
        self.description = description
        self.responsable = responsable
        self.created_at = created_at
        self.updated_at = updated_at
    
    def validate(self):
        """Valide les données du portefeuille."""
        if not self.nom or not self.nom.strip():
            raise ValueError("Le nom du portefeuille est obligatoire")
        
        if len(self.nom) > 200:
            raise ValueError("Le nom du portefeuille ne peut pas dépasser 200 caractères")
    
    def to_dict(self):
        """Convertit le portefeuille en dictionnaire."""
        return {
            'id': self.id,
            'nom': self.nom,
            'description': self.description,
            'responsable': self.responsable,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }
    
    @classmethod
    def from_dict(cls, data):
        """Crée un Portefeuille depuis un dictionnaire."""
        return cls(
            id=data.get('id'),
            nom=data.get('nom', ''),
            description=data.get('description', ''),
            responsable=data.get('responsable', ''),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
        )
    
    def __str__(self):
        return self.nom
