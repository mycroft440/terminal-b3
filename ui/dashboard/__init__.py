"""Package ui.dashboard - componentes do dashboard principal.

API publica:
    from ui.dashboard.background_worker import BackgroundScannerWorker
    from ui.dashboard.render import DashboardRenderer
    from ui.dashboard.wallet_view import WalletView
"""
from ui.dashboard.background_worker import BackgroundScannerWorker
from ui.dashboard.render import DashboardRenderer
from ui.dashboard.wallet_view import WalletView

__all__ = ["BackgroundScannerWorker", "DashboardRenderer", "WalletView"]
