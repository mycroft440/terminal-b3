"""Package ui.dialogs.notes - Bloco de Notas com editor Markdown e galeria.

API publica:
    from ui.dialogs.notes import create_notes_dialog
    from ui.dialogs.notes.image_helpers import load_image_as_data_uri, clear_image_cache
    from ui.dialogs.notes.markdown_editor import MarkdownEditor
    from ui.dialogs.notes.image_gallery import ImageGallery

Arquitetura (apos Fase 5.1):
- image_helpers.py: load_image_as_data_uri, clear_image_cache
  Helpers para carregar imagens como data URIs base64 (Flet 0.85+)
- markdown_editor.py: classe MarkdownEditor
  Editor de texto + toolbar + toggle preview/edit + contadores
- image_gallery.py: classe ImageGallery
  Galeria de thumbnails + lightbox + file picker + placeholder
- note_dialog.py: create_notes_dialog (orquestrador)
  Reune MarkdownEditor + ImageGallery em um ft.AlertDialog

Antes (Fase 4): notes_dialog.py monolitico de 645 linhas
Agora: 4 modulos com responsabilidade unica cada
"""
from ui.dialogs.notes.image_helpers import (
    load_image_as_data_uri,
    clear_image_cache,
)
from ui.dialogs.notes.markdown_editor import MarkdownEditor
from ui.dialogs.notes.image_gallery import ImageGallery
from ui.dialogs.notes.note_dialog import create_notes_dialog

# Retrocompatibilidade: aliases com _prefix
_load_image_as_data_uri = load_image_as_data_uri
_clear_image_cache = clear_image_cache

__all__ = [
    # API principal
    "create_notes_dialog",
    # Sub-componentes (uso avancado)
    "MarkdownEditor",
    "ImageGallery",
    # Helpers
    "load_image_as_data_uri",
    "clear_image_cache",
    # Retrocompatibilidade
    "_load_image_as_data_uri",
    "_clear_image_cache",
]
