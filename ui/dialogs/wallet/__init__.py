"""Package ui.dialogs.wallet - dialogs de carteira.

API publica:
    from ui.dialogs.wallet import create_wallet_dialogs
    from ui.dialogs.wallet.add_asset_dialog import AddAssetDialog
    from ui.dialogs.wallet.new_wallet import NewWalletDialog
    from ui.dialogs.wallet.add_wallet import AddWalletDialog
    from ui.dialogs.wallet.remove_wallet import RemoveWalletDialog

Arquitetura (apos Fase 5.2 + add_asset_dialog):
- add_asset_dialog.py: classe AddAssetDialog
  Buscar ativo por ticker/nome e adicionar a carteira (autocomplete)
- new_wallet.py: classe NewWalletDialog
  Criar nova carteira (TextField + dialog Criar/Cancelar)
- add_wallet.py: classe AddWalletDialog
  Adicionar/remover ativo em carteiras existentes (chips toggle +
  quick add + preco/quantidade)
- remove_wallet.py: classe RemoveWalletDialog
  Confirmar remocao de ativo de uma ou mais carteiras
- wallet_dialog.py: create_wallet_dialogs (orquestrador)
  Reune os 3 dialogs e retorna dict com openers (API retrocompativel)
"""
from ui.dialogs.wallet.new_wallet import NewWalletDialog
from ui.dialogs.wallet.add_wallet import AddWalletDialog
from ui.dialogs.wallet.remove_wallet import RemoveWalletDialog
from ui.dialogs.wallet.add_asset_dialog import AddAssetDialog
from ui.dialogs.wallet.wallet_dialog import create_wallet_dialogs

__all__ = [
    # API principal
    "create_wallet_dialogs",
    # Classes (uso avancado)
    "NewWalletDialog",
    "AddWalletDialog",
    "RemoveWalletDialog",
    "AddAssetDialog",
]
