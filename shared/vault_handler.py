"""
Manejador del Baúl de Contenidos (Media Vault)
Permite indexar y recuperar fotos y videos generados previamente.
"""
import os
from pathlib import Path
from typing import List, Dict

class VaultHandler:
    def __init__(self):
        self.photos_dir = Path("content/generated_photos")
        self.videos_dir = Path("content/generated_videos")
        
        # Asegurar que existan
        self.photos_dir.mkdir(parents=True, exist_ok=True)
        self.videos_dir.mkdir(parents=True, exist_ok=True)

    def get_all_media(self) -> List[Dict]:
        """Retorna una lista de diccionarios con la info de cada archivo."""
        media_items = []
        
        # Fotos
        for f in self.photos_dir.glob("*.jpg"):
            media_items.append({
                "name": f.name,
                "path": str(f),
                "type": "photo",
                "mtime": os.path.getmtime(f)
            })
            
        # Videos
        for f in self.videos_dir.glob("*.mp4"):
            media_items.append({
                "name": f.name,
                "path": str(f),
                "type": "video",
                "mtime": os.path.getmtime(f)
            })
            
        # Ordenar por fecha (más reciente primero)
        return sorted(media_items, key=lambda x: x["mtime"], reverse=True)

if __name__ == "__main__":
    vault = VaultHandler()
    items = vault.get_all_media()
    print(f"Indexados {len(items)} archivos en el baúl.")
