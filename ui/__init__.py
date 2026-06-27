"""UI module - interface Flet do Terminal B3 Pro.

API publica:
    from ui import (
        # State management
        StateManager,
        # Main view
        get_dashboard_view,
        # Cards
        create_card,
        # Theme
        AppColors,
        # Components reutilizaveis
        dropdown_options, pill_button,
        # Dialogs
        create_notes_dialog, create_wallet_dialogs, create_settings_dialog,
    )
"""
from ui.state_manager import StateManager
from ui.main_page import get_dashboard_view
from ui.cards import create_card
from ui.theme import AppColors
from ui.components import dropdown_options, pill_button
from ui.dialogs.notes import create_notes_dialog
from ui.dialogs.wallet import create_wallet_dialogs
from ui.dialogs.settings_dialog import create_settings_dialog

__all__ = [
    # State management
    "StateManager",
    # Main view
    "get_dashboard_view",
    # Cards
    "create_card",
    # Theme
    "AppColors",
    # Components
    "dropdown_options",
    "pill_button",
    # Dialogs
    "create_notes_dialog",
    "create_wallet_dialogs",
    "create_settings_dialog",
]
