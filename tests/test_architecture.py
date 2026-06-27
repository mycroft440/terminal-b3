"""
Teste de regressao arquitetural.

Valida que a estrutura basica do projeto (modulos, packages, exports
publicos) continua funcional apos refatoracao. Se algo quebrar aqui,
o refactor introduziu breaking change na API publica.

Estes testes sao PROPOSITALMENTE acoplados a estrutura atual - eles
devem ser atualizados quando a estrutura muda intencionalmente.
"""
import unittest
import sys
import os
import importlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestEstruturaModulos(unittest.TestCase):
    """Garante que os modulos criticos continuam importaveis."""

    MODULOS_ESPERADOS = [
        "main",
        "core.config",
        "core.catalog",
        "core.indicators",
        "services.cache",
        "services.scanner",
        "services.background_service",
        "providers.brapi",
        "providers.yfinance_provider",
        "ui.theme",
        "ui.cards",
        "ui.state_manager",
        "ui.main_page",
        "ui.dialogs.notes",
        "ui.dialogs.notes.note_dialog",
        "ui.dialogs.wallet",
        "ui.dialogs.wallet.wallet_dialog",
        "ui.dialogs.settings_dialog",
    ]

    def test_todos_modulos_importam(self):
        for mod in self.MODULOS_ESPERADOS:
            with self.subTest(modulo=mod):
                try:
                    importlib.import_module(mod)
                except ImportError as e:
                    self.fail(f"Falha ao importar {mod}: {e}")


class TestAPIPublicaScanner(unittest.TestCase):
    """APIs publicas do scanner que outros modulos dependem."""

    def test_gerar_chunks_ativos_existe(self):
        from services import scanner

        self.assertTrue(hasattr(scanner, "gerar_chunks_ativos"))
        self.assertTrue(callable(scanner.gerar_chunks_ativos))

    def test_gerar_b3_chunks_existe(self):
        from services import scanner

        self.assertTrue(hasattr(scanner, "gerar_b3_chunks"))

    def test_montar_catalogo_acoes_existe(self):
        from services import scanner

        # Apos refactor de unificacao, pode virar montar_catalogo(market)
        # mas o wrapper retrocompativel deve continuar existindo
        self.assertTrue(
            hasattr(scanner, "montar_catalogo_acoes")
            or hasattr(scanner, "montar_catalogo"),
            "Scanner deve expor montar_catalogo_acoes ou montar_catalogo",
        )


class TestAPIPublicaStateManager(unittest.TestCase):
    def test_state_manager_tem_metodos_essenciais(self):
        from ui.state_manager import StateManager

        metodos_esperados = [
            "load_all",
            "save_ui_state",
            "save_carteiras",
            "save_ocultos",
            "save_notes",
            "save_evaluated_cache",
            "load_evaluated_cache",
            "get_config_hash",
        ]
        for metodo in metodos_esperados:
            self.assertTrue(
                hasattr(StateManager, metodo),
                f"StateManager deve ter metodo {metodo}",
            )

    def test_state_manager_tem_state_dict(self):
        # Inicializa em diretorio temporario
        import tempfile

        with tempfile.TemporaryDirectory():
            from ui.state_manager import StateManager

            sm = StateManager()
            self.assertIsInstance(sm.state, dict)
            # Chaves essenciais
            for chave in [
                "market",
                "timeframe",
                "sector",
                "sort",
                "carteiras",
                "ocultos",
                "anotacoes",
                "mms_active",
                "mms_periodos",
                "rsi_active",
                "stoch_active",
            ]:
                self.assertIn(chave, sm.state, f"state deve ter chave '{chave}'")


class TestAPIPublicaCache(unittest.TestCase):
    def test_cache_tem_funcoes_essenciais(self):
        # Apos Fase 2.3, services expoe instancia 'cache' (diskcache.Cache)
        # em __init__.py, o que faz 'import services.cache' resolver para
        # a instancia em vez do modulo. Usamos importlib para garantir
        # que estamos pegando o modulo real.
        import importlib

        cache_module = importlib.import_module("services.cache")

        for fn in ["get_ttl", "cache_is_fresh", "cache_set_with_ts"]:
            self.assertTrue(
                hasattr(cache_module, fn),
                f"services.cache deve ter funcao {fn}",
            )

    def test_cache_instancia_eh_exposta_em_services(self):
        """Apos Fase 2.3, services expoe instancia 'cache' (diskcache.Cache)
        para uso direto via from services import cache."""
        from services import cache
        # Deve ser uma instancia de Cache (diskcache), nao modulo
        self.assertFalse(hasattr(cache, "__name__"), "cache deve ser instancia, nao modulo")
        # Deve ter metodos set/get tipicos de diskcache
        self.assertTrue(hasattr(cache, "get"), "cache deve ter metodo get")
        self.assertTrue(hasattr(cache, "set"), "cache deve ter metodo set")

    def test_get_ttl_retorna_int(self):
        from services.cache import get_ttl

        for tf in ["1d", "1s", "1m", "5m", "15m", "30m", "1h"]:
            ttl = get_ttl(tf)
            self.assertIsInstance(ttl, int)
            self.assertGreater(ttl, 0)

    def test_get_ttl_timeframe_desconhecido_tem_default(self):
        from services.cache import get_ttl

        # Timeframe invalido deve cair no default (nao crashar)
        ttl = get_ttl("xyz")
        self.assertIsInstance(ttl, int)
        self.assertGreater(ttl, 0)


class TestAPIPublicaProviders(unittest.TestCase):
    def test_yfinance_provider_tem_fetch_market_data(self):
        from providers import yfinance_provider

        self.assertTrue(callable(yfinance_provider.fetch_market_data))

    def test_brapi_tem_fetch_brapi_assets(self):
        from providers import brapi

        self.assertTrue(callable(brapi.fetch_brapi_assets))


class TestAPIPublicaUI(unittest.TestCase):
    def test_main_page_tem_get_dashboard_view(self):
        from ui import main_page

        self.assertTrue(callable(main_page.get_dashboard_view))

    def test_cards_tem_create_card(self):
        from ui import cards

        self.assertTrue(callable(cards.create_card))

    def test_notes_dialog_tem_create_notes_dialog(self):
        from ui.dialogs.notes import create_notes_dialog
        self.assertTrue(callable(create_notes_dialog))

    def test_wallet_dialog_tem_create_wallet_dialogs(self):
        from ui.dialogs.wallet import create_wallet_dialogs
        self.assertTrue(callable(create_wallet_dialogs))

    def test_settings_dialog_tem_create_settings_dialog(self):
        from ui.dialogs import settings_dialog

        # Pode ser create_settings_dialog ou similar - verifica que existe
        # algum factory publico
        factories = [
            n for n in dir(settings_dialog) if n.startswith("create_") and not n.startswith("_")
        ]
        self.assertTrue(
            len(factories) > 0,
            f"settings_dialog deve ter factory publico, encontrado: {factories}",
        )


class TestConfigHashConsistencia(unittest.TestCase):
    """Garante que get_config_hash nao tem drift entre modulos."""

    def test_state_manager_get_config_hash_eh_fonte_unica(self):
        """Apos refactor da Fase 1.3, main_page.py NAO deve ter
        implementacao propria de get_config_hash - deve delegar
        para state_manager.get_config_hash()."""
        # Le codigo de main_page.py
        with open(
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "ui",
                "main_page.py",
            ),
            "r",
            encoding="utf-8",
        ) as f:
            source = f.read()

        # Nao deve haver implementacao duplicada da logica do hash
        # (string com mms_periodos[0] + market + timeframe + ...)
        self.assertNotIn(
            "f\"{state['market']}_{state['timeframe']}",
            source,
            "main_page.py nao deve ter implementacao propria de get_config_hash "
            "- deve delegar para state_manager.get_config_hash()",
        )

    def test_state_manager_get_config_hash_funciona(self):
        """StateManager.get_config_hash continua funcional."""
        import tempfile

        with tempfile.TemporaryDirectory():
            from ui.state_manager import StateManager

            sm = StateManager()
            sm.state["market"] = "acoes"
            sm.state["timeframe"] = "1d"
            sm.state["mms_active"] = True
            sm.state["mms_periodos"] = [20]
            sm.state["rsi_active"] = True
            sm.state["stoch_active"] = False
            # Hash deterministico
            h1 = sm.get_config_hash()
            h2 = sm.get_config_hash()
            self.assertEqual(h1, h2)
            # Formato esperado
            self.assertEqual(h1, "acoes_1d_True_20_True_False")


if __name__ == "__main__":
    unittest.main(verbosity=2)
