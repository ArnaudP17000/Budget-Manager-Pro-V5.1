"""Système de configuration et sauvegarde des widgets."""
import logging
import json
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class WidgetConfig:
    """Gère la configuration et la sauvegarde des widgets."""
    
    def __init__(self):
        """Initialise la configuration."""
        self.config_dir = Path('data/config')
        self.config_file = self.config_dir / 'dashboard_layout.json'
        self.backup_dir = self.config_dir / 'backups'
        
        # Créer les dossiers si nécessaire
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f'📁 Config dir: {self.config_dir}')
    
    def save_layout(self, layout_data):
        """
        Sauvegarde la disposition des widgets.
        
        Args:
            layout_data (dict): {
                'widgets': {
                    'widget_id': {
                        'class': 'WidgetClassName',
                        'size': 'small|medium|large',
                        'minimized': bool
                    }
                },
                'positions': {
                    'widget_id': (row, col, rowspan, colspan)
                },
                'metadata': {
                    'saved_at': timestamp,
                    'version': str
                }
            }
        """
        try:
            # Créer une sauvegarde de l'ancien fichier
            if self.config_file.exists():
                self.create_backup()
            
            # Ajouter les métadonnées
            layout_data['metadata'] = {
                'saved_at': datetime.now().isoformat(),
                'version': '1.0',
                'app': 'Budget Manager Pro V4.2'
            }
            
            # Sauvegarder
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(layout_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f'✅ Layout sauvegardé: {self.config_file}')
            return True
            
        except Exception as e:
            logger.error(f'Erreur sauvegarde layout: {e}', exc_info=True)
            return False
    
    def load_layout(self):
        """
        Charge la disposition sauvegardée.
        
        Returns:
            dict or None: Données de layout ou None si non trouvé
        """
        try:
            if not self.config_file.exists():
                logger.info('Aucun fichier de configuration trouvé')
                return None
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                layout_data = json.load(f)
            
            # Valider les données
            if not self.validate_layout(layout_data):
                logger.warning('Layout invalide, ignoré')
                return None
            
            logger.info(f"✅ Layout chargé: {len(layout_data.get('widgets', {}))} widgets")
            return layout_data
            
        except json.JSONDecodeError as e:
            logger.error(f'Erreur parsing JSON: {e}')
            return None
        except Exception as e:
            logger.error(f'Erreur chargement layout: {e}', exc_info=True)
            return None
    
    def validate_layout(self, layout_data):
        """
        Valide les données de layout.
        
        Args:
            layout_data (dict): Données à valider
            
        Returns:
            bool: True si valide
        """
        try:
            # Vérifier la structure
            if not isinstance(layout_data, dict):
                return False
            
            if 'widgets' not in layout_data or 'positions' not in layout_data:
                return False
            
            # Vérifier que les widgets et positions correspondent
            widgets = layout_data['widgets']
            positions = layout_data['positions']
            
            if set(widgets.keys()) != set(positions.keys()):
                logger.warning('Widgets et positions ne correspondent pas')
                return False
            
            # Vérifier chaque widget
            for widget_id, widget_info in widgets.items():
                if not isinstance(widget_info, dict):
                    return False
                if 'class' not in widget_info:
                    return False
            
            # Vérifier chaque position
            for widget_id, position in positions.items():
                if not isinstance(position, (list, tuple)) or len(position) != 4:
                    return False
                if not all(isinstance(x, int) for x in position):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f'Erreur validation layout: {e}')
            return False
    
    def create_backup(self):
        """Crée une sauvegarde du fichier de configuration actuel."""
        try:
            if not self.config_file.exists():
                return
            
            # Nom du backup avec timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = self.backup_dir / f'dashboard_layout_{timestamp}.json'
            
            # Copier le fichier
            import shutil
            shutil.copy2(self.config_file, backup_file)
            
            logger.info(f'✅ Backup créé: {backup_file}')
            
            # Nettoyer les vieux backups (garder les 10 derniers)
            self.cleanup_old_backups(keep=10)
            
        except Exception as e:
            logger.error(f'Erreur création backup: {e}', exc_info=True)
    
    def cleanup_old_backups(self, keep=10):
        """
        Nettoie les anciens backups.
        
        Args:
            keep (int): Nombre de backups à conserver
        """
        try:
            # Lister tous les backups
            backups = sorted(
                self.backup_dir.glob('dashboard_layout_*.json'),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            # Supprimer les anciens
            for backup in backups[keep:]:
                backup.unlink()
                logger.debug(f'🗑️ Backup supprimé: {backup.name}')
            
        except Exception as e:
            logger.error(f'Erreur nettoyage backups: {e}')
    
    def restore_backup(self, backup_file):
        """
        Restaure une sauvegarde.
        
        Args:
            backup_file (Path or str): Fichier de backup à restaurer
        """
        try:
            backup_path = Path(backup_file)
            
            if not backup_path.exists():
                logger.error(f'Backup non trouvé: {backup_path}')
                return False
            
            # Créer un backup du fichier actuel avant de restaurer
            if self.config_file.exists():
                self.create_backup()
            
            # Restaurer
            import shutil
            shutil.copy2(backup_path, self.config_file)
            
            logger.info(f'✅ Backup restauré: {backup_path.name}')
            return True
            
        except Exception as e:
            logger.error(f'Erreur restauration backup: {e}', exc_info=True)
            return False
    
    def list_backups(self):
        """
        Liste tous les backups disponibles.
        
        Returns:
            list: Liste de dicts avec infos sur les backups
        """
        try:
            backups = []
            
            for backup_file in sorted(
                self.backup_dir.glob('dashboard_layout_*.json'),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            ):
                stat = backup_file.stat()
                backups.append({
                    'file': backup_file,
                    'name': backup_file.name,
                    'size': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_mtime),
                })
            
            return backups
            
        except Exception as e:
            logger.error(f'Erreur liste backups: {e}')
            return []
    
    def get_default_layout(self):
        """
        Retourne la configuration par défaut.
        
        Returns:
            dict: Configuration par défaut
        """
        return {
            'widgets': {
                'kpi_finances': {
                    'class': 'KPIWidget',
                    'size': 'medium',
                    'minimized': False
                },
                'alertes': {
                    'class': 'AlertWidget',
                    'size': 'small',
                    'minimized': False
                },
                'top_projets': {
                    'class': 'ProjectWidget',
                    'size': 'medium',
                    'minimized': False
                },
                'meteo_budgetaire': {
                    'class': 'MeteoWidget',
                    'size': 'small',
                    'minimized': False
                }
            },
            'positions': {
                'kpi_finances': [0, 0, 1, 2],
                'alertes': [0, 2, 1, 1],
                'top_projets': [1, 0, 1, 2],
                'meteo_budgetaire': [1, 2, 1, 1]
            }
        }
    
    def reset_to_default(self):
        """Réinitialise la configuration par défaut."""
        try:
            # Sauvegarder l'actuel
            if self.config_file.exists():
                self.create_backup()
            
            # Charger la config par défaut
            default_layout = self.get_default_layout()
            
            # Sauvegarder
            self.save_layout(default_layout)
            
            logger.info('✅ Configuration réinitialisée par défaut')
            return True
            
        except Exception as e:
            logger.error(f'Erreur réinitialisation: {e}', exc_info=True)
            return False
    
    def export_config(self, export_path):
        """
        Exporte la configuration vers un fichier.
        
        Args:
            export_path (Path or str): Chemin d'export
        """
        try:
            layout_data = self.load_layout()
            
            if not layout_data:
                logger.warning('Aucune configuration à exporter')
                return False
            
            export_file = Path(export_path)
            export_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(layout_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f'✅ Configuration exportée: {export_file}')
            return True
            
        except Exception as e:
            logger.error(f'Erreur export configuration: {e}', exc_info=True)
            return False
    
    def import_config(self, import_path):
        """
        Importe une configuration depuis un fichier.
        
        Args:
            import_path (Path or str): Chemin du fichier à importer
        """
        try:
            import_file = Path(import_path)
            
            if not import_file.exists():
                logger.error(f'Fichier non trouvé: {import_file}')
                return False
            
            # Charger et valider
            with open(import_file, 'r', encoding='utf-8') as f:
                layout_data = json.load(f)
            
            if not self.validate_layout(layout_data):
                logger.error('Configuration invalide')
                return False
            
            # Sauvegarder l'actuel
            if self.config_file.exists():
                self.create_backup()
            
            # Sauvegarder la nouvelle config
            self.save_layout(layout_data)
            
            logger.info(f'✅ Configuration importée: {import_file}')
            return True
            
        except Exception as e:
            logger.error(f'Erreur import configuration: {e}', exc_info=True)
            return False
    
    def get_config_info(self):
        """
        Retourne les infos sur la configuration actuelle.
        
        Returns:
            dict: Informations
        """
        try:
            info = {
                'config_file': str(self.config_file),
                'exists': self.config_file.exists(),
                'size': 0,
                'modified': None,
                'widgets_count': 0,
                'backups_count': len(list(self.backup_dir.glob('*.json')))
            }
            
            if self.config_file.exists():
                stat = self.config_file.stat()
                info['size'] = stat.st_size
                info['modified'] = datetime.fromtimestamp(stat.st_mtime)
                
                layout_data = self.load_layout()
                if layout_data:
                    info['widgets_count'] = len(layout_data.get('widgets', {}))
                    info['metadata'] = layout_data.get('metadata', {})
            
            return info
            
        except Exception as e:
            logger.error(f'Erreur infos config: {e}')
            return {}


# Singleton
widget_config = WidgetConfig()


