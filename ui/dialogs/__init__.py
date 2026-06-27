"""Dialogs module - dialogos modais (notas, carteiras, configuracoes).

API publica:
    from ui.dialogs import (
        create_notes_dialog,
        create_wallet_dialogs,
        create_settings_dialog,
    )
"""
from ui.dialogs.notes import create_notes_dialog
from ui.dialogs.wallet import create_wallet_dialogs
from ui.dialogs.settings_dialog import create_settings_dialog

__all__ = [
    "create_notes_dialog",
    "create_wallet_dialogs",
    "create_settings_dialog",
]
